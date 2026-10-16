#!/usr/bin/env bash
# Chạy + chấm cả 3 bộ dữ liệu. Dùng: TAG=v2 VOTE=3 bash scripts/bench.sh
set -u
TAG=${TAG:-run}
cd "$(dirname "$0")/.."
run() {  # $1=dir  $2=gold
  out="outputs/bench-$TAG-$(basename "$1").csv"
  python main.py --no-ui --xlsx-dir "$1/xlsx_files" --queries "$1/queries.json" --output "$out" \
    --log-file "outputs/bench-$TAG-$(basename "$1").jsonl" 2>&1 | tail -1
  python scripts/dev.py eval "$out" "$1/$2"
}
run public-data-1 sample_submission.csv
run public-data-2 answers.json
run public-data-3 answer_key.csv
