"""Entrypoint (Docker ENTRYPOINT ["python", "main.py"]).

Thứ tự ưu tiên cấu hình:  tham số dòng lệnh  >  biến môi trường / file .env  >  mặc định.
- Hệ thống chấm: python main.py --xlsx-dir D --queries Q --output O --openrouter-key K
                                --openrouter-model M --openrouter-base-url U
- Chạy nhanh:    điền .env rồi gõ  python main.py
Nhật ký ra stderr; kết quả chỉ ghi vào file output. Thoát 0 sau khi đã ghi xong submission.csv.
"""
import argparse
import os
import sys
from pathlib import Path


def load_dotenv():
    """Đọc .env (KEY=VALUE) ở thư mục hiện tại hoặc thư mục dự án; không ghi đè biến môi trường đã có."""
    for base in (Path.cwd(), Path(__file__).resolve().parent):
        f = base / ".env"
        if not f.is_file():
            continue
        for line in f.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("\"'"))
        break


def parse_args(argv=None):
    load_dotenv()
    env = os.getenv
    p = argparse.ArgumentParser(description="Excel QA - trả lời câu hỏi trên bảng tính (.xlsx)")
    p.add_argument("--xlsx-dir", default=env("XLSX_DIR", "data/xlsx_files"))
    p.add_argument("--queries", default=env("QUERIES", "data/queries.json"))
    p.add_argument("--output", default=env("OUTPUT", "outputs/submission.csv"))
    p.add_argument("--openrouter-key", default=env("OPENROUTER_API_KEY", ""))
    p.add_argument("--openrouter-model", default=env("MODEL", ""))
    p.add_argument("--openrouter-base-url", default=env("OPENROUTER_BASE_URL", ""))
    p.add_argument("--workers", type=int, default=int(env("WORKERS", "0")) or None)
    p.add_argument("--log-file", default=env("LOG_FILE") or None, help="tùy chọn: ghi log từng câu (jsonl)")
    p.add_argument("--no-ui", action="store_true")
    args, _unknown = p.parse_known_args(argv)      # tham số lạ không làm chương trình sập
    return args


def main(argv=None) -> int:
    a = parse_args(argv)
    from excelqa import config as cfg
    cfg.configure(key=a.openrouter_key, model=a.openrouter_model, base_url=a.openrouter_base_url, workers=a.workers)
    print(f"[excelqa] xlsx_dir={a.xlsx_dir} queries={a.queries} output={a.output} model={cfg.MODEL} "
          f"key={'có' if cfg.OPENROUTER_API_KEY else 'THIẾU'}", file=sys.stderr)
    if not cfg.OPENROUTER_API_KEY:
        print("[excelqa] cảnh báo: thiếu API key (--openrouter-key hoặc OPENROUTER_API_KEY trong .env); "
              "các câu sẽ để trống", file=sys.stderr)
    if not Path(a.queries).is_file():
        print(f"[excelqa] lỗi: không thấy file queries: {a.queries}", file=sys.stderr)
        return 1
    from excelqa.core.pipeline import run
    from excelqa.ui import make_ui
    try:
        run(a.xlsx_dir, a.queries, a.output, workers=cfg.WORKERS, ui=make_ui(a.no_ui), log_file=a.log_file)
    except Exception as e:                          # chỉ xảy ra khi không ghi được output
        print(f"[excelqa] lỗi nghiêm trọng: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())