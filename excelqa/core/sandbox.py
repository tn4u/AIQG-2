"""Chạy code do LLM sinh trong namespace hạn chế, có timeout.

Lưu ý: đây là lớp bảo vệ mức cơ bản (AST + builtins whitelist), đủ cho code pandas ngắn.
"""
from __future__ import annotations
import ast, collections, datetime, functools, itertools, math, re, statistics, threading, traceback, copy

import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

from .. import config as cfg
from .postprocess import fmt_num

BANNED_ATTRS = {"read_csv", "read_excel", "read_pickle", "read_json", "to_csv", "to_excel", "to_pickle",
                "to_sql", "to_json", "eval", "system", "popen", "load", "loads", "dump", "save"}
SAFE_BUILTINS = {n: __builtins__[n] if isinstance(__builtins__, dict) else getattr(__builtins__, n)
                 for n in ["abs", "min", "max", "sum", "len", "sorted", "round", "int", "float", "str", "bool",
                           "range", "enumerate", "zip", "any", "all", "list", "dict", "set", "tuple",
                           "isinstance", "reversed", "map", "filter", "Exception", "ValueError",
                           "KeyError", "IndexError", "TypeError", "True", "False", "None", "next",
                           "iter", "pow", "divmod", "repr", "format", "hasattr", "frozenset", "slice"]}
# Module an toàn mà code sinh ra hay import: thay vì từ chối, chuyển `import`/`from ... import` thành phép gán.
SAFE_MODULES = {"pandas": pd, "numpy": np, "math": math, "datetime": datetime, "re": re,
                "statistics": statistics, "collections": collections, "itertools": itertools,
                "functools": functools}


class _ImportRewriter(ast.NodeTransformer):
    def visit_Import(self, node):
        out = []
        for a in node.names:
            top = a.name.split(".")[0]
            if top not in SAFE_MODULES:
                return node                                   # để check_code báo lỗi
            if a.asname:                                      # import numpy as np -> np = numpy
                out.append(ast.parse(f"{a.asname} = {a.name}").body[0])
        return out or None

    def visit_ImportFrom(self, node):
        mod = node.module or ""
        if node.level or mod.split(".")[0] not in SAFE_MODULES or any(a.name == "*" for a in node.names):
            return node
        return [ast.parse(f"{a.asname or a.name} = {mod}.{a.name}").body[0] for a in node.names]


def rewrite_imports(code: str) -> str:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code                                           # check_code sẽ báo lỗi cú pháp
    if not any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(tree)):
        return code
    return ast.unparse(ast.fix_missing_locations(_ImportRewriter().visit(tree)))


def check_code(code: str) -> str | None:
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"SyntaxError: {e}"
    for n in ast.walk(tree):
        if isinstance(n, ast.While):
            return "while loops are not allowed; use a for-loop or pandas operations"
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            return ("import is not allowed for this module (available: pd, np, math, datetime, re, "
                    "statistics, collections, itertools, functools)")
        if isinstance(n, ast.Attribute) and (n.attr.startswith("__") or n.attr in BANNED_ATTRS):
            return f"attribute '{n.attr}' is not allowed"
        if isinstance(n, ast.Name) and n.id in {"open", "exec", "eval", "compile", "__import__", "globals", "locals", "getattr", "setattr", "input"}:
            return f"name '{n.id}' is not allowed"
    return None

def children(d, label, section=None):
    """Các hàng nằm ngay dưới hàng `label` (level+1), dừng khi gặp hàng có level <= level của nó."""
    m = d[d["label"] == label]
    if section is not None:
        m = m[m["section"].str.contains(section, regex=False)]
    if m.empty:
        return d.iloc[0:0]
    i = d.index.get_loc(m.index[0])
    lv = d["level"].tolist()
    out = []
    for j in range(i + 1, len(d)):
        if lv[j] <= lv[i]:
            break
        if lv[j] == lv[i] + 1:
            out.append(j)
    return d.iloc[out]

def run_code(code: str, tables, timeout: float = cfg.SANDBOX_TIMEOUT):
    """Trả về (ok, answer, error_text). Mỗi lần chạy dùng bản sao DataFrame."""
    code = rewrite_imports(code)
    err = check_code(code)
    if err:
        return False, None, err

    helpers = ["_row", "section", "label", "is_total", "level", "has_children"]
    tabs = []
    for t in tables:
        t2 = copy.copy(t)
        inv = {v: k for k, v in t.col_map.items()}              # tên đầy đủ -> c1..cN
        d = t.df.rename(columns=inv)
        t2.df = d[helpers + list(t.col_map)].copy()               # chỉ còn helper + c1..cN
        t2.vcols = list(t.col_map)
        tabs.append(t2)

    dfs = {t.sheet: t.df for t in tabs}
    SAFE_BUILTINS["print"] = lambda *a, **k: None
    env = {"__builtins__": SAFE_BUILTINS, **SAFE_MODULES, "pd": pd, "np": np,
           "tables": tabs, "dfs": dfs, "df": tabs[0].df if tabs else None,
           "VCOLS": tabs[0].vcols if tabs else [], "children": children,
           "fmt": fmt_num, "fmt_num": fmt_num, "answer": None, "final_answer": None}
    box = {}

    def target():
        try:
            exec(compile(code, "<llm_code>", "exec"), env)
            box["ok"] = True
        except Exception:
            box["ok"] = False
            box["err"] = traceback.format_exc(limit=3)[-800:]

    th = threading.Thread(target=target, daemon=True)
    th.start()
    th.join(timeout)
    if th.is_alive():
        return False, None, f"timeout after {timeout}s"
    if not box.get("ok"):
        return False, None, box.get("err", "unknown error")
    raw = env.get("final_answer") if env.get("final_answer") is not None else env.get("answer")
    return True, raw, ""