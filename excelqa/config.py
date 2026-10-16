import os

def configure(key=None, model=None, base_url=None, workers=None):
    """Ghi đè cấu hình từ tham số dòng lệnh của hệ thống chấm (không in/lưu key ra đâu)."""
    global OPENROUTER_API_KEY, MODEL, OPENROUTER_BASE_URL, WORKERS
    if key:
        OPENROUTER_API_KEY = key
    if model:
        MODEL = model
    if base_url:
        OPENROUTER_BASE_URL = base_url.rstrip("/")
    if workers:
        WORKERS = int(workers)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
MODEL = os.getenv("MODEL", "qwen/qwen3.7-flash")

WORKERS = int(os.getenv("WORKERS", "4"))
MAX_RETRIES = 2            # số lần sửa code sau lần đầu
COST_CAP = 0.07            # USD/câu: dừng retry khi vượt (giới hạn đề: 0.10)
TIME_CAP = 90              # giây/câu
GLOBAL_TIME_CAP = 30 * 60  # giây cho cả lượt chạy (giới hạn đề: 40 phút)
SANDBOX_TIMEOUT = 15       # giây/lần chạy code
MAX_SHEET_CHARS = 60000    # cắt bản xem sheet gửi LLM nếu dài hơn
SAMPLE_ROWS = 150          # bảng dài hơn: chỉ gửi mẫu đầu/cuối + danh sách khối (tiết kiệm token)
SAMPLE_HEAD, SAMPLE_TAIL = 40, 8
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "120"))
TEMPERATURE = 0.0
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2000"))
MAX_TOKENS_REASONING = int(os.getenv("MAX_TOKENS_REASONING", "8000"))   # khi bật suy luận
DISABLE_REASONING = os.getenv("DISABLE_REASONING", "1") == "1"
# Số mẫu code sinh SONG SONG cho mỗi câu rồi bỏ phiếu đa số (1 = tắt). Mẫu đầu dùng temperature 0.
VOTE = max(1, int(os.getenv("VOTE", "1")))
VOTE_TEMPERATURE = float(os.getenv("VOTE_TEMPERATURE", "0.7"))

# Giá dự phòng khi API không trả cost. KIỂM TRA LẠI trên trang model OpenRouter.
PRICE_IN_PER_M = float(os.getenv("PRICE_IN_PER_M", "0.10"))
PRICE_OUT_PER_M = float(os.getenv("PRICE_OUT_PER_M", "0.40"))