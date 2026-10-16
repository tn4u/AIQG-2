"""Sinh bản mô tả gọn của các Table để đưa vào prompt (mã cột ngắn c1..cN)."""
from __future__ import annotations
import re
import numpy as np
import pandas as pd

from .. import config as cfg


def fmt(v) -> str:
    if v is None or v is pd.NaT or (isinstance(v, float) and np.isnan(v)):
        return "NA"
    if isinstance(v, pd.Timestamp):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    if isinstance(v, (float, np.floating)):
        return str(int(v)) if float(v).is_integer() else repr(float(v))
    return str(v)


def _kind(s: pd.Series) -> str:
    if pd.api.types.is_datetime64_any_dtype(s):
        return "date"
    if pd.api.types.is_numeric_dtype(s):
        return "number"
    nn = s.dropna()
    if re.search(r"\b(code|naics)\b", str(s.name), re.I):
        return "text (code)"
    if len(nn) and pd.to_numeric(nn, errors="coerce").notna().mean() >= 0.5:
        return "text, mostly numeric: use pd.to_numeric(..., errors='coerce')"
    return "text"


def table_text(t, idx: int, max_chars: int) -> str:
    head = [f"### tables[{idx}]  name={t.name!r}  file={t.file}  sheet={t.sheet!r}"]
    if t.title:
        head.append(f"TITLE: {t.title}")
    if t.year:
        head.append(f"YEAR (applies to all columns): {t.year}")
    if t.notes:
        head.append("UNIT/NOTES: " + "; ".join(t.notes))
    head.append(f"LABEL COLUMN header: {t.label_col!r} (values are in df['label'])")
    head.append("VALUE COLUMNS (df columns are named exactly c1..cN):")
    head += [f"  {k} = {v}  [{_kind(t.df[v])}]" for k, v in t.col_map.items()]
    n = len(t.df)
    secs_all = [x for x in dict.fromkeys(t.df["section"]) if x]
    if len(secs_all) >= 2 and n <= cfg.SAMPLE_ROWS:
        head.append("BLOCKS in order (the FIRST is the default when the question names no block): "
                    + " | ".join(secs_all[:25]))
    sample = n > cfg.SAMPLE_ROWS
    if sample:
        head.append(f"TABLE HAS {n} ROWS. Only the first {cfg.SAMPLE_HEAD} and last {cfg.SAMPLE_TAIL} rows are shown; "
                    "the real DataFrame has all rows - search/filter it with code.")
        secs = []
        for name, g in t.df.groupby("section", sort=False):
            secs.append(f"  {name or '-'}: rows {g['_row'].min()}-{g['_row'].max()} ({len(g)} rows)")
        head.append("SECTIONS:\n" + "\n".join(secs[:30]))
    head.append("ROWS: row_id | section | label | flags | " + " | ".join(t.col_map))
    head.append("flags: T=total/aggregate row, P=parent row (has sub-rows below), L<n>=indent level")
    idxs = list(range(n)) if not sample else list(range(cfg.SAMPLE_HEAD)) + list(range(n - cfg.SAMPLE_TAIL, n))
    lines, size = [], sum(len(x) for x in head)
    for i in idxs:
        r = t.df.iloc[i]
        if sample and i == n - cfg.SAMPLE_TAIL:
            lines.append("[... rows omitted ...]")
        flags = ("T" if r["is_total"] else "") + ("P" if r["has_children"] else "") + (f"L{r['level']}" if r["level"] else "")
        vals = " | ".join(fmt(r[c]) for c in t.col_names)
        line = f"r{r['_row']} | {r['section'] or '-'} | {r['label']} | {flags or '-'} | {vals}"
        size += len(line) + 1
        if size > max_chars:
            lines.append("[VIEW TRUNCATED: remaining rows exist in the real DataFrame; query them with code]")
            break
        lines.append(line)
    foot = [f"FOOTNOTE: {f}" for f in t.footnotes[:4]]
    return "\n".join(head + lines + foot)


def sheet_text(tables, max_chars: int = cfg.MAX_SHEET_CHARS) -> str:
    per = max(5000, max_chars // max(1, len(tables)))
    return "\n\n".join(table_text(t, i, per) for i, t in enumerate(tables))