"""Công cụ phát triển (không dùng khi chấm): inspect <file.xlsx> [--view] | eval <pred.csv> <gold.(csv|json)>"""
import csv, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _read(path):
    if str(path).endswith(".csv"):
        return {str(r["id"]): r["answer"] for r in csv.DictReader(open(path, encoding="utf-8-sig"))}
    d = json.load(open(path, encoding="utf-8"))
    return {str(x["id"]): x["answer"] for x in d} if isinstance(d, list) else {str(k): v for k, v in d.items()}


def cmd_inspect(path, view=False):
    import pandas as pd
    from excelqa.core.loader import load_tables
    from excelqa.core.sheet_view import sheet_text
    tables = load_tables(path)
    for i, t in enumerate(tables):
        print(f"\n=== tables[{i}] sheet={t.sheet!r} name={t.name!r} year={t.year} notes={t.notes}")
        for k, v in t.col_map.items():
            print(f"  {k} = {v}")
        with pd.option_context("display.width", 250, "display.max_columns", 40, "display.max_colwidth", 38):
            print(t.df[["_row", "section", "label", "is_total", "level", "has_children"] + t.col_names[:3]].to_string())
    if view:
        print("\n" + sheet_text(tables))


def cmd_eval(pred, gold):
    p, g = _read(pred), _read(gold)
    norm = lambda s: re.sub(r"[\s\"'()\[\],]+", " ", str(s).lower()).strip()
    strict = lenient = 0
    for i, a in g.items():
        a, got = str(a), p.get(i)
        if got == a:
            strict += 1; lenient += 1; tag = "OK  "
        elif got is not None and norm(got) == norm(a):
            lenient += 1; tag = "OK~ "
        else:
            tag = "FAIL"
        if tag != "OK  ":
            print(f"{tag} {i}: pred={got!r} gold={a!r}")
    print(f"Exact: {strict}/{len(g)}   (kể cả chuẩn hóa nhẹ: {lenient}/{len(g)})")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "inspect":
        cmd_inspect(sys.argv[2], "--view" in sys.argv)
    elif len(sys.argv) >= 4 and sys.argv[1] == "eval":
        cmd_eval(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)