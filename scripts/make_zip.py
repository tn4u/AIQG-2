"""Đóng gói: python scripts/make_zip.py team001  ->  team001.zip (Dockerfile ở gốc). Quét key, kiểm tra < 100 MB."""
import re, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
team = sys.argv[1] if len(sys.argv) > 1 else "team001"
KEEP = ["Dockerfile", ".dockerignore", ".env.example", "requirements.txt", "README.md", "main.py"]
KEY_RE = re.compile(r"sk-or-[A-Za-z0-9_\-]{10,}|sk-[A-Za-z0-9_\-]{30,}")
files = [ROOT / f for f in KEEP if (ROOT / f).exists()]
files += [p for p in (ROOT / "excelqa").rglob("*") if p.is_file() and "__pycache__" not in p.parts]
files += [p for p in (ROOT / "scripts").glob("*.py")]
for p in files:
    if KEY_RE.search(p.read_text(encoding="utf-8", errors="ignore")):
        sys.exit(f"CẢNH BÁO: có thể lộ API key trong {p}")
out = ROOT / f"{team}.zip"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for p in files:
        z.write(p, p.relative_to(ROOT).as_posix())
mb = out.stat().st_size / 1e6
print(f"{out.name}: {mb:.2f} MB, {len(files)} files; Dockerfile ở gốc: {'Dockerfile' in [f.name for f in files]}")
sys.exit("zip vượt 100 MB!" if mb > 100 else 0)