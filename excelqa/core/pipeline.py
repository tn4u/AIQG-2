"""Điều phối: đọc queries -> nạp file (1 lần) -> trả lời song song -> ghi CSV + log."""
from __future__ import annotations
import json, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .. import config as cfg
from ..llm.client import LLMClient
from ..ui import NullUI
from . import agent
from .io_utils import find_xlsx, load_queries, ordered_ids, write_submission
from .loader import load_tables
from .sheet_view import sheet_text


def get_peak_ram_mb() -> float:
    try:
        import resource, sys
        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return round(usage / (1024 * 1024), 1) if sys.platform == "darwin" else round(usage / 1024, 1)
    except Exception:
        return 0.0


def run(data_dir, queries_path, output_path, workers: int = cfg.WORKERS, ui=None,
        log_file=None, llm=None) -> dict:
    ui = ui or NullUI()
    queries = load_queries(queries_path)
    ids = list(dict.fromkeys(q["id"] for q in queries))      # loại id trùng
    cache = {}
    for fn in sorted({q["file_name"] for q in queries if q["file_name"]}):
        p = find_xlsx(data_dir, fn)
        try:
            tabs = load_tables(p, fn) if p else []
            cache[fn] = (tabs, sheet_text(tabs)) if tabs else ([], f"cannot load {fn}")
        except Exception as e:
            cache[fn] = ([], f"{type(e).__name__}: {e}")
            ui.message(f"Không đọc được {fn}: {e}")

    llm = llm or LLMClient()
    deadline = time.time() + cfg.GLOBAL_TIME_CAP
    answers, log_lock = {}, threading.Lock()
    log_f = None
    if log_file:
        try:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            log_f = open(log_file, "w", encoding="utf-8")
        except OSError:
            log_f = None

    def work(q):
        try:
            tabs, text = cache.get(q["file_name"], ([], "missing file"))
            if not tabs:
                info = {"id": q["id"], "kind": "-", "answer": "", "error": text, "seconds": 0}
            else:
                info = agent.answer_question(q, tabs, text, llm, deadline)
        except Exception as e:
            info = {"id": q["id"], "kind": "-", "answer": "", "error": f"{type(e).__name__}: {e}", "seconds": 0}
        info["file"], info["query"] = q["file_name"], q["query"]
        with log_lock:
            answers[q["id"]] = info["answer"]
            if log_f:
                log_f.write(json.dumps(info, ensure_ascii=False, default=str) + "\n"); log_f.flush()
            ui.update(info)
        return info

    ui.start(len(queries))
    t0 = time.time()
    infos = []
    try:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
            infos = list(ex.map(work, queries))
    finally:
        if log_f:
            log_f.close()
        write_submission(output_path, ordered_ids(ids), answers)   # luôn ghi đủ id

    n = max(1, len(infos))
    tok_list = [i.get("prompt_tokens", 0) + i.get("completion_tokens", 0) for i in infos]
    costs = [i.get("cost_usd", 0.0) for i in infos]
    summary = {"questions": len(infos), "answered": sum(1 for i in infos if i.get("answer") != ""),
               "total_sec": round(time.time() - t0, 1),
               "avg_sec": round(sum(i.get("seconds", 0) for i in infos) / n, 2),
               "total_tokens": sum(tok_list),
               "avg_tokens": round(sum(tok_list) / n),
               "total_cost_usd": round(sum(costs), 4),
               "max_cost_usd": round(max(costs, default=0.0), 4),
               "peak_ram_mb": get_peak_ram_mb()}
    ui.finish(summary)
    return summary