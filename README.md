# Hướng Dẫn Cài Đặt và Chạy (CT-QA)

Giải pháp tự động hỏi đáp trên các tệp Excel phức tạp (`.xlsx`) sử dụng mô hình **Qwen3.7 Flash** (`qwen/qwen3.7-flash`) qua OpenRouter theo đúng quy định của Ban Tổ Chức.

---

## 1. Cài đặt môi trường

Yêu cầu: **Python 3.10+** (khuyên dùng Python 3.11).

```bash
# Tạo và kích hoạt môi trường ảo (tùy chọn)
python3 -m venv .venv
source .venv/bin/activate      # Trên Windows: .venv\Scripts\activate

# Cài đặt các thư viện cần thiết (< 2 phút, không cần cài đặt nặng)
pip install -r requirements.txt
```

---

## 2. Cách chạy chương trình

### Cách 1: Nhanh nhất — Dùng file `.env` (Khuyên dùng khi chấm nhanh)
Ban Giám khảo chỉ cần tạo hoặc chỉnh sửa file `.env` ở thư mục gốc:

```env
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxx
MODEL=qwen/qwen3.7-flash
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
XLSX_DIR=data/xlsx_files
QUERIES=data/queries.json
OUTPUT=outputs/submission.csv
```

Sau đó chỉ cần gõ đúng một lệnh:
```bash
python main.py
```

---

### Cách 2: Chạy bằng tham số dòng lệnh (Khớp hoàn toàn script chấm của BTC)
Hệ thống chấm có thể truyền trực tiếp các đường dẫn và API key qua cờ dòng lệnh:

```bash
python main.py \
  --xlsx-dir /path/to/xlsx_files \
  --queries /path/to/queries.json \
  --output /path/to/submission.csv \
  --openrouter-key <OPENROUTER_API_KEY> \
  --openrouter-model qwen/qwen3.7-flash \
  --openrouter-base-url https://openrouter.ai/api/v1
```

* Thứ tự ưu tiên cấu hình: **Tham số dòng lệnh > Biến môi trường / file `.env` > Giá trị mặc định**.
* Sau khi xử lý xong, file kết quả `submission.csv` sẽ được tạo đúng định dạng (`id,answer`), không kèm câu giải thích hay đơn vị dư thừa.

---

## 3. Chạy bằng Docker (linux/amd64)

```bash
# Build image
docker build --platform linux/amd64 -t ctqa .

# Chạy container
docker run --rm \
  -v /path/to/input:/input \
  -v /path/to/output:/output \
  ctqa \
  --xlsx-dir /input/xlsx_files \
  --queries /input/queries.json \
  --output /output/submission.csv \
  --openrouter-key <OPENROUTER_API_KEY>
```

---

## 4. Cấu trúc thư mục

```
main.py                 # Điểm khởi chạy chính (hỗ trợ cả CLI args và .env)
Dockerfile, requirements.txt, .env.example
excelqa/
  config.py             # Cấu hình tài nguyên (timeout, cost cap, workers, vote)
  ui.py                 # Giao diện tiến trình và bảng tổng hợp đối chiếu chỉ số BTC
  core/
    loader.py           # Tiền xử lý Excel: unmerge ô, giải phẳng header, phân tầng
    sheet_view.py       # Tối ưu hóa schema & dữ liệu mẫu nạp vào prompt cho LLM
    agent.py            # Sinh mã pandas (Program-of-Thought), retry và voting
    sandbox.py          # Môi trường thực thi code cách ly, an toàn, có timeout
    postprocess.py      # Chuẩn hóa đáp án thành giá trị nguyên thủy (Exact Match)
    pipeline.py         # Điều phối đa luồng, quản lý bộ nhớ và xuất file CSV
    io_utils.py         # Đọc queries và ghi submission chuẩn UTF-8
  llm/
    client.py           # Kết nối OpenRouter, kiểm soát retry, token và chi phí
    prompts.py          # System prompt & các quy tắc suy luận bảng biểu
```