"""Đọc queries.json, tìm file xlsx, ghi submission.csv."""
from __future__ import annotations
import csv, json, os, re
from pathlib import Path


def load_queries(path) -> list[dict]:
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)
    out = []
    for q in data:
        fn = q.get("file_name") or q.get("file name") or q.get("filename") or q.get("file")
        out.append({"id": str(q.get("id", "")), "file_name": fn,
            "query": q.get("query") or q.get("question") or ""})
    return out


def find_xlsx(data_dir, name) -> Path | None:
    """Tìm file theo tên: khớp chính xác, không phân biệt hoa/thường, hoặc tìm đệ quy."""
    base = Path(data_dir)
    if not name:
        return None
    p = base / name
    if p.exists():
        return p
    low = Path(name).name.lower()
    for root, _, files in os.walk(base):
        for fn in files:
            if fn.lower() == low:
                return Path(root) / fn
    return None


def write_submission(path, ids, answers: dict) -> None:
    """UTF-8 không BOM, header id,answer, đúng thứ tự ids, mỗi id một dòng."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["id", "answer"])
        for i in ids:
             w.writerow([i, " ".join(str(answers.get(i, "")).split())])

def ordered_ids(ids):
    """Submission theo id tăng dần. Id toàn số -> sắp xếp số học; ngược lại giữ thứ tự gốc."""
    if all(re.fullmatch(r"-?\d+", str(i)) for i in ids):
        return sorted(ids, key=lambda x: int(x))
    return list(ids)