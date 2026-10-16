"""Gọi OpenRouter (chat completions), đếm token/chi phí, retry có backoff."""
from __future__ import annotations
import os, threading, time
from dataclasses import dataclass

import httpx

from .. import config as cfg


@dataclass
class LLMResult:
    text: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    latency_s: float
    finish_reason: str = ""          # "length" = bị cắt do max_tokens


class CostTracker:
    """Cộng dồn chi phí/token/thời gian của MỘT câu hỏi (gồm cả retry). An toàn đa luồng."""
    def __init__(self):
        self.prompt = self.completion = 0
        self.cost = 0.0
        self.calls = 0
        self.t0 = time.time()
        self._lock = threading.Lock()

    def add(self, r: LLMResult):
        with self._lock:
            self.prompt += r.prompt_tokens
            self.completion += r.completion_tokens
            self.cost += r.cost_usd
            self.calls += 1

    @property
    def tokens(self) -> int:
        return self.prompt + self.completion

    @property
    def elapsed(self) -> float:
        return time.time() - self.t0

    def over_budget(self) -> bool:
        return self.cost >= cfg.COST_CAP or self.elapsed >= cfg.TIME_CAP


class LLMClient:
    def __init__(self, api_key: str | None = None, model: str | None = None,
                 base_url: str | None = None, timeout: float | None = None):
        self.api_key = api_key or cfg.OPENROUTER_API_KEY or os.getenv("OPENROUTER_API_KEY", "")
        self.model = model or cfg.MODEL or os.getenv("MODEL", "qwen/qwen3.7-flash")
        self.base_url = (base_url or cfg.OPENROUTER_BASE_URL or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")).rstrip("/")
        self.http = httpx.Client(timeout=timeout if timeout is not None else cfg.LLM_TIMEOUT)

    def close(self):
        if hasattr(self, "http") and self.http is not None:
            self.http.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def chat(self, messages: list[dict], temperature: float | None = None,
             max_tokens: int | None = None, reasoning: bool | None = None) -> LLMResult:
        """reasoning=None -> theo cấu hình (cfg.DISABLE_REASONING)."""
        use_reasoning = (not cfg.DISABLE_REASONING) if reasoning is None else reasoning
        api_key = self.api_key or cfg.OPENROUTER_API_KEY or os.getenv("OPENROUTER_API_KEY", "")
        if not api_key:
            raise RuntimeError("Thiếu OPENROUTER_API_KEY (đặt biến môi trường hoặc file .env)")
        model = self.model or cfg.MODEL or os.getenv("MODEL", "qwen/qwen3.7-flash")
        base_url = (self.base_url or cfg.OPENROUTER_BASE_URL or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")).rstrip("/")
        body = {"model": model, "messages": messages,
                "temperature": cfg.TEMPERATURE if temperature is None else temperature,
                "max_tokens": max_tokens or (cfg.MAX_TOKENS_REASONING if use_reasoning else cfg.MAX_TOKENS),
                "usage": {"include": True}}            # xin OpenRouter trả chi phí
        if not use_reasoning:
            body["reasoning"] = {"enabled": False}     # giảm token/thời gian
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        last = None
        for attempt in range(4):
            t0 = time.time()
            try:
                resp = self.http.post(f"{self.base_url}/chat/completions", json=body, headers=headers)
                if resp.status_code == 400 and ("reasoning" in body or "usage" in body):
                    body.pop("reasoning", None); body.pop("usage", None)   # tham số lạ -> bỏ rồi thử lại
                    continue
                if resp.status_code in (429, 500, 502, 503, 504):
                    last = RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
                    time.sleep(1.5 * (2 ** attempt))
                    continue
                resp.raise_for_status()
                data = resp.json()
                choice = data["choices"][0]
                text = choice["message"].get("content") or ""   # KHÔNG dùng phần 'reasoning' làm đáp án
                finish = choice.get("finish_reason") or ""
                u = data.get("usage") or {}
                pt, ct = int(u.get("prompt_tokens", 0)), int(u.get("completion_tokens", 0))
                cost = u.get("cost")
                if cost is None:
                    cost = pt / 1e6 * cfg.PRICE_IN_PER_M + ct / 1e6 * cfg.PRICE_OUT_PER_M
                return LLMResult(text, pt, ct, float(cost), time.time() - t0, finish)
            except (httpx.TimeoutException, httpx.TransportError) as e:
                last = e
                time.sleep(1.5 * (2 ** attempt))
        if last is not None:
            raise last
        raise RuntimeError("OpenRouter call failed after retries")