"""Trả lời MỘT câu hỏi: LLM sinh code -> sandbox -> kiểm tra -> retry -> bỏ phiếu -> dự phòng."""
from __future__ import annotations
import re, time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from .. import config as cfg
from ..llm import prompts
from ..llm.client import CostTracker
from . import postprocess as pp
from .sandbox import run_code

CODE_RE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.S)
OPEN_FENCE_RE = re.compile(r"```(?:python|py)?\s*\n(.*)$", re.S)     # khối code chưa đóng (bị cắt)


def extract_code(text: str) -> str:
    text = text or ""
    m = CODE_RE.findall(text)
    if m:
        return m[-1].strip()
    m = OPEN_FENCE_RE.search(text)
    return (m.group(1) if m else text).strip()


def _chain(llm, base_messages, tables, kind, query, tracker, temperature, deadline):
    """Một chuỗi: sinh code -> chạy -> nếu lỗi thì gửi lỗi lại cho mô hình sửa (tối đa MAX_RETRIES lần)."""
    messages = list(base_messages)
    res = {"answer": None, "code": "", "error": "", "retries": 0}
    for attempt in range(cfg.MAX_RETRIES + 1):
        if deadline and time.time() > deadline:
            res["error"] = "global deadline"
            break
        r = llm.chat(messages, temperature=temperature)
        tracker.add(r)
        code = extract_code(r.text)
        ok, raw, err = run_code(code, tables)
        if ok:
            ans, why = pp.normalize(raw, kind, query)
        else:
            ans, why = None, err
        if r.finish_reason == "length" and ans is None:
            why = "your reply was cut off (too long); write shorter code. " + (why or "")
        res["code"] = code
        if ans is not None:
            res["answer"] = ans
            return res
        res["error"], res["retries"] = why, attempt + 1
        if tracker.over_budget() or attempt == cfg.MAX_RETRIES:
            break
        messages = messages + [{"role": "assistant", "content": r.text or "(empty)"},
                               {"role": "user", "content": prompts.RETRY_TMPL.format(problem=why, kind=kind)
                                + _sections_hint(tables)}]
    return res


def _sections_hint(tables) -> str:
    """Gợi ý ngắn khi retry: các khối (section) thật sự có trong bảng."""
    parts = []
    for i, t in enumerate(tables):
        secs = [x[:60] for x in dict.fromkeys(t.df["section"]) if x][:25]
        if secs:
            parts.append(f"tables[{i}] sections: " + " | ".join(secs))
    return ("\n" + "\n".join(parts)) if parts else ""


def _vote_key(ans: str) -> str:
    return " ".join(str(ans).lower().split())


def answer_question(q: dict, tables, sheet_text: str, llm, deadline: float | None = None) -> dict:
    kind = pp.detect_kind(q["query"])
    tracker = CostTracker()
    info = {"id": q["id"], "kind": kind, "answer": "", "code": "", "retries": 0, "error": "", "mode": "code"}
    messages = [{"role": "system", "content": prompts.SYSTEM_CODE},
                {"role": "user", "content": prompts.USER_TMPL.format(sheet=sheet_text, query=q["query"], kind=kind)}]
    try:
        n = cfg.VOTE
        temps = [cfg.TEMPERATURE] + [cfg.VOTE_TEMPERATURE] * (n - 1)   # mẫu đầu tất định, các mẫu sau đa dạng
        run = lambda t: _chain(llm, messages, tables, kind, q["query"], tracker, t, deadline)
        if n == 1:
            results = [run(temps[0])]
        else:
            with ThreadPoolExecutor(max_workers=n) as ex:
                results = list(ex.map(run, temps))
        info["retries"] = sum(r["retries"] for r in results)
        good = [r for r in results if r["answer"] is not None]
        if good:
            votes = Counter(_vote_key(r["answer"]) for r in good)
            best = votes.most_common(1)[0][0]            # hoà phiếu -> ưu tiên mẫu sớm hơn (mẫu temperature 0)
            pick = next(r for r in good if _vote_key(r["answer"]) == best)
            info.update(answer=pick["answer"], code=pick["code"])
            if n > 1:
                info["votes"] = dict(votes)
            return _finish(info, tracker)
        info["code"], info["error"] = results[0]["code"], results[0]["error"]
        # dự phòng: trả lời trực tiếp (không code) nếu còn ngân sách; chỉ nhận dòng 'ANSWER:'
        if not tracker.over_budget() and not (deadline and time.time() > deadline):
            info["mode"] = "direct"
            res = llm.chat([{"role": "system", "content": prompts.SYSTEM_DIRECT},
                            {"role": "user", "content": f"{sheet_text}\n\nQUESTION: {q['query']}"}])
            tracker.add(res)
            info["answer"] = pp.parse_direct(res.text, kind, q["query"])
    except Exception as e:  # không để một câu làm sập cả lượt chạy
        info["error"] = f"{type(e).__name__}: {e}"
    return _finish(info, tracker)


def _finish(info, tracker):
    info.update(prompt_tokens=tracker.prompt, completion_tokens=tracker.completion,
                cost_usd=round(tracker.cost, 6), seconds=round(tracker.elapsed, 2), llm_calls=tracker.calls)
    return info