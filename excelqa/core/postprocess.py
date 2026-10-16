"""Chuẩn hóa tối thiểu đáp án do mô hình tạo ra (không đoán dạng đáp án từ từ ngữ câu hỏi)."""
from __future__ import annotations
import math, re
from decimal import Decimal, ROUND_HALF_UP

import numpy as np
import pandas as pd

from .loader import clean_text, strip_footnote

PLACEHOLDERS = {"n/a", "na", "none", "nan", "nat", "null", "unknown", "-", "--"}


def detect_kind(query: str) -> str:
    return "auto"          # mô hình tự định dạng theo câu hỏi


def fmt_num(x, nd: int = 0) -> str:
    """Số -> chuỗi làm tròn half-up đúng nd chữ số thập phân (nd=0: số nguyên)."""
    d = Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP)
    return f"{d:f}"


def _fmt_item(x) -> str | None:
    if isinstance(x, (pd.Series, pd.Index, np.ndarray)):
        x = list(x)
        x = x[0] if len(x) == 1 else None
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    if isinstance(x, (bool, np.bool_)):
        return "Yes" if bool(x) else "No"
    if isinstance(x, (int, float, np.integer, np.floating)):
        f = float(x)
        return str(int(f)) if f.is_integer() else repr(round(f, 10))
    s = strip_footnote(clean_text(x))
    return s or None


def normalize(raw, kind: str = "auto", query: str = "") -> tuple[str | None, str]:
    """Trả (đáp án chuỗi | None nếu không hợp lệ, lý do lỗi để gửi lại cho mô hình)."""
    if raw is None:
        return None, "answer is None"
    if isinstance(raw, pd.DataFrame):
        return None, "answer must be a string/number/list, not a DataFrame"
    if isinstance(raw, (pd.Series, pd.Index, np.ndarray)):
        raw = list(raw)
    if isinstance(raw, (list, tuple)):
        parts = [_fmt_item(e) for e in raw]
        if not parts or any(p is None for p in parts):
            return None, "list answer has empty/NaN items"
        out = ", ".join(_align_items(parts, query))
    else:
        out = _fmt_item(raw)
        if out is None:
            return None, "answer is empty/NaN or not a single value"
        if isinstance(raw, str):
            out = ", ".join(_align_items(out.split(", "), query))
    if any(p.strip().lower() in PLACEHOLDERS for p in out.split(",")):
        return None, "answer contains a placeholder (N/A/None/nan): your row/section filter probably selected nothing"
    return out, ""


def _align_items(parts: list[str], query: str) -> list[str]:
    """Chỉ đổi sang tên ngắn theo câu hỏi khi MỌI mục sau khi đổi đều xuất hiện trong câu hỏi."""
    ql = query.lower()
    aligned = [_align_to_query(p, query) for p in parts]
    if aligned != parts and all(a.lower() in ql for a in aligned):
        return aligned
    return parts


def _align_to_query(e: str, query: str) -> str:
    """Nếu câu hỏi tự gọi mục này bằng tên ngắn hơn (vd 'Agriculture'), dùng đúng tên theo câu hỏi."""
    ql = query.lower()
    if e.lower() in ql:
        return e
    words = e.split()
    for k in range(len(words) - 1, 0, -1):
        pre = " ".join(words[:k])
        if re.search(r"(?<![\w])" + re.escape(pre.lower()) + r"(?![\w])", ql):
            return pre
    return e


def parse_direct(text: str, kind: str = "auto", query: str = "") -> str:
    """Chế độ dự phòng (không code): chỉ lấy dòng 'ANSWER: ...' cuối cùng; không có -> chuỗi rỗng."""
    tags = re.findall(r"^[\s*#>]*(?:final\s+)?answer\s*\**\s*[:\-]\s*(.+?)\s*$", text or "", flags=re.I | re.M)
    if not tags:
        return ""
    s = tags[-1].strip().strip("`*\"' ").rstrip(".").strip()
    return "" if s.lower() in PLACEHOLDERS else s