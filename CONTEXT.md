# HANDOFF: Excel QA (cuộc thi "Hỏi đáp trên bảng tính Excel") - đặc tả đầy đủ để lập trình

> Vai trò của bạn (AI coding assistant): triển khai dự án Python dưới đây theo đúng đặc tả. Làm theo từng GIAI ĐOẠN ở mục 12, hết mỗi giai đoạn dừng lại để tôi chạy kiểm tra. Không tự thêm tính năng ngoài đặc tả. Không hardcode theo tên file/câu hỏi mẫu, vì code sẽ chạy lại trên dữ liệu mới.

## 1. Bài toán

Xây chương trình CLI tự động trả lời câu hỏi ngôn ngữ tự nhiên dựa trên dữ liệu trong các file Excel (.xlsx). Dữ liệu có thể có: nhiều bảng trên một sheet, tiêu đề phân cấp nhiều tầng, ô gộp, cấu trúc không đồng nhất. Giải pháp phải xác định đúng thông tin liên quan và trả đáp án chính xác.

### Input
- Thư mục chứa các file `.xlsx`.
- `queries.json`: list các object `{"id": "p4_q001", "file_name": "p4_t01.xlsx", "query": "..."}`. Mỗi câu hỏi liên quan đúng 1 file. Lưu ý: ví dụ trong đề viết `"file name"` (có dấu cách) còn mô tả viết `file_name`, nên phải chấp nhận cả hai key.
- `sample_submission.csv` (chỉ để tham khảo định dạng). Header file mẫu có BOM ẩn trước chữ `id`.

### Output
- `submission.csv`, UTF-8 KHÔNG BOM, header đúng `id,answer`, mỗi `id` trong queries.json đúng một dòng, đúng thứ tự queries.json, dùng module `csv` chuẩn (tự quote khi đáp án chứa dấu phẩy, ví dụ `"34282, 118705"`).
- Cột `answer` chỉ chứa đáp án cuối, không giải thích.
- Chấm bằng EXACT MATCH, nên đúng từng ký tự.

### Ràng buộc cứng (vi phạm một trong số này = không được chấm)
| Hạng mục | Giới hạn |
|---|---|
| LLM | Phải hỗ trợ `qwen/qwen3.7-flash` qua OpenRouter (https://openrouter.ai/qwen/qwen3.7-flash). Key chỉ đọc từ biến môi trường, KHÔNG có trong mã nguồn |
| Chi phí LLM | <= 0.10 USD / câu hỏi, tính cả retry |
| Thời gian | <= 40 phút cho 20 câu (từ lúc chạy đến lúc có submission.csv, gồm xử lý dữ liệu + gọi API) |
| Máy chấm | 6 vCPU, 12 GB RAM |
| Bộ nhớ | Tổng RAM giải pháp dùng <= 1 GB |
| Zip nộp | <= 100 MB |
| Khả năng chạy lại | Chạy được với dữ liệu mới, không phụ thuộc đường dẫn bộ mẫu; không chạy được/không tạo file hợp lệ = không chấm |

### Thứ tự xếp hạng
1. Số câu đúng (Exact Match) - nhiều hơn xếp trước.
2. Thời gian chạy trung bình mỗi câu - thấp hơn xếp trước.
3. Số token LLM trung bình mỗi câu - ít hơn xếp trước.

=> Ưu tiên tuyệt đối là ĐÚNG; sau đó nhanh; sau đó ít token. Ngân sách 0.10 USD/câu và 2 phút/câu là rất rộng, nên dùng retry/bỏ phiếu khi cần, nhưng tránh lãng phí.

### Sản phẩm phải nộp
Một file `.zip` gồm: mã nguồn, `requirements.txt`, `.env.example`, `README.md` (hướng dẫn cài đặt, cấu hình, chạy bằng dòng lệnh). Không gồm `.env`, `.venv`, `data/`, `outputs/`.

### Lịch
- 13/10 19:00: bộ công khai lần 1. 16/10 09:00: bộ công khai lần 2.
- Hạn nộp zip: 17/10 12:00. 18/10 08:00-17:00: vấn đáp xác minh (phải giải thích nguyên lý, thành phần chính, và sửa được mã nguồn theo yêu cầu). Không đạt vấn đáp = bị loại khỏi bảng chính thức.
=> Code phải dễ đọc, chia module rõ, có docstring và comment ngắn.

## 2. Yêu cầu về giao diện CLI (do người dùng muốn)

Giao diện đẹp được phép NHƯNG không được phá chế độ chạy tự động:
1. Lệnh chạy chính hoàn toàn non-interactive: không `input()`, không hỏi xác nhận.
2. Logic nằm ở `excelqa/core` và `excelqa/llm`; CLI/UI chỉ là lớp bọc.
3. Giao diện in ra stderr; kết quả ghi ra file. Không bao giờ lẫn UI vào `submission.csv`.
4. Tự chuyển sang log thuần khi: có cờ `--no-ui`, hoặc stderr không phải TTY (bị pipe/CI), hoặc biến môi trường `NO_COLOR`/`CI` được đặt.
5. Chỉ dùng Typer + Rich (nhẹ). Không dùng Textual.
6. Chế độ tương tác (`wizard`) là lệnh riêng, tuyệt đối không là mặc định.

Các lệnh:
| Lệnh | Mục đích |
|---|---|
| `python main.py run --data-dir D --queries Q --output O [--workers 4] [--no-ui] [--log-file L]` | Lệnh chính (BTC dùng lệnh này) |
| `python main.py inspect FILE.xlsx [--sheet-view]` | In bảng đã chuẩn hóa (DataFrame + bản sheet gọn gửi LLM) để kiểm tra loader |
| `python main.py eval --pred P --gold G` | So sánh submission với đáp án chuẩn, in số đúng/sai và diff |
| `python main.py wizard` | Hỏi từng bước (thư mục, key, model) rồi gọi `run` |

Tham số có giá trị mặc định hợp lý; `--data-dir` và `--queries` bắt buộc cho `run`; mã thoát khác 0 chỉ khi không ghi được submission.csv (câu lỗi riêng lẻ KHÔNG làm chương trình thoát; ghi giá trị dự phòng).

## 3. Cấu trúc thư mục

```
excel-qa/
├── README.md
├── requirements.txt
├── .env.example            # OPENROUTER_API_KEY=  /  MODEL=qwen/qwen3.7-flash
├── .gitignore              # .env, .venv, data/, outputs/, __pycache__
├── main.py                 # điểm vào, gọi excelqa.cli.app()
├── excelqa/
│   ├── __init__.py
│   ├── cli.py              # Typer: run / inspect / eval / wizard
│   ├── ui.py               # Rich progress/bảng, tự tắt khi không TTY
│   ├── config.py           # đọc env, hằng số, ngưỡng chi phí/thời gian
│   ├── core/
│   │   ├── pipeline.py     # điều phối A→B→C→D
│   │   ├── loader.py       # giải ô gộp, làm phẳng header, gắn khối
│   │   ├── sheet_view.py   # sinh bản sheet gọn cho prompt
│   │   ├── agent.py        # sinh code, chạy, retry, dự phòng
│   │   ├── sandbox.py      # chạy code có timeout, namespace hạn chế
│   │   ├── postprocess.py  # chuẩn hóa đáp án theo loại
│   │   └── io_utils.py     # đọc queries.json, ghi CSV
│   └── llm/
│       ├── client.py       # OpenRouter, đếm token/chi phí, retry
│       └── prompts.py      # toàn bộ prompt
├── tests/
│   ├── gold_answers.json
│   ├── test_loader.py
│   └── test_postprocess.py
├── scripts/
│   ├── evaluate.py
│   └── make_zip.py         # đóng gói, loại .env/.venv/data/outputs, kiểm tra < 100 MB, quét key
├── data/                   # KHÔNG nộp: xlsx_files/, queries.json, sample_submission.csv
└── outputs/                # KHÔNG nộp: submission.csv, run_log.jsonl
```

`requirements.txt` (ghim phiên bản khi hoàn tất): `openpyxl pandas numpy httpx typer rich python-dotenv`. Python 3.11/3.12.

## 4. Dữ liệu thật (bộ công khai lần 1)

Cả 10 file đều 1 sheet, nhỏ (tối đa 134 hàng x 13 cột) => KHÔNG cần chọn sheet/RAG; gửi nguyên sheet (đã chuẩn hóa) cho LLM trong prompt. Nhưng bộ ẩn có thể lớn hơn/khác dạng, nên loader phải tổng quát và có cơ chế cắt gọn nếu sheet quá lớn (xem mục 6.3).

| File | Nội dung | Điểm khó |
|---|---|---|
| p4_t01 | `People` A1:G22. 20 người: No, Name(First/Middle/Last), Date of(Birth/Admission), Score | Header 2 hàng gộp ô (B1:D1 `Name`, E1:F1 `Date of`, A1:A2, G1:G2). Dữ liệu từ hàng 3. Ngày là datetime |
| p4_t02 | `Monsumtable` A1:L18. Xuất nhập khẩu nông sản (tỷ USD), 2 khối: Fiscal years (hàng 1-7) và Calendar years (hàng 9-15) | Header gộp B1:E1 `Fiscal years 2/`, F1:G1 `Fiscal year-to-date`, H1 `September`; hàng 2 là năm 2020..2024 (năm 2023 xuất hiện 2 lần: cả năm và year-to-date); hàng 3 `Billion dollars` gộp; ô H9 là công thức `=H1`; nhãn có footnote `Trade balance 3/`; hàng "Agricultural exports" xuất hiện ở cả 2 khối |
| p4_t03 | `Sheet0` A1:K42. CPI theo hạng mục chi tiêu | KHÔNG có ô gộp; header 2 hàng với tên nhóm lặp ở nhiều cột (`Unadjusted indexes` x3, `Unadjusted percent change` x2, `Seasonally adjusted percent change` x3); hàng 2 là kỳ (`Oct.\n2023`...); cột A `Indent Level` (0-4) là cây phân cấp; hàng 3 rỗng; có hàng trống (14, 23); I38, J38 rỗng; nhãn có footnote `(1)` |
| p4_t04 | `cpsaat07` A1:I68. Tình trạng việc làm 25+ theo học vấn, 2023, đơn vị nghìn | Tiêu đề/ghi chú ở A1,A2; header A4:I6 gộp 3 hàng; các khối TOTAL / Men / Women / White / Black or African American / Asian / Hispanic or Latino ethnicity (hàng chỉ có nhãn ở cột A); mỗi khối 7 hàng chỉ số lặp lại (`Civilian noninstitutional population`, `Civilian labor force`, `Participation rate`, `Employed`, `Employment-population ratio`, `Unemployed`, `Unemployment rate`); cột: Less than HS, HS graduates, Some college or associate degree (Total / Some college, no degree / Associate degree), Bachelor's+ (Total / Bachelor's only / Advanced). Footnote ở hàng 65-68 (gộp) |
| p4_t05 | `cpsaat14` A1:M96. Người đi làm phi nông nghiệp theo ngành x tuổi/giới/chủng tộc | 12 cột ngành, KHÔNG có cột tổng ngành; nhãn tuổi (`20 to 24 years`) lặp trong từng khối giới; khối là hàng `Total, 16 years and over`, `Men, 16 years and over`, `Women, 16 years and over`, ... (nhãn đã chứa tên khối); `TOTAL` ở A7; header A4:M5 |
| p4_t06 | `cpsaat15` A1:M38. Loại hình lao động (wage&salary, self-employed, unpaid family) x tuổi/giới | Header 3 tầng (B2:E2 `Agriculture and related industries`, F2:M2 `Nonagricultural industries`, G3:K3 `Wage and salary workers`, H4:J4 `Private industries`...); cột `Total` xuất hiện ở nhiều cấp; hàng nhóm tuổi cha/con (`16 to 19 years` > `16 to 17`, `18 to 19`); khối bắt đầu ở `Total, 16 years and over` (7), `Men, 16 years and over` (18), `Women, 16 years and over` (29) |
| p4_t07 | `cpsaat17` A1:M134. Người đi làm theo ngành x nghề nghiệp | Header 2 tầng, 13 cột (Total employed; Management..., Service..., Sales and office..., Natural resources..., Production...); nhãn ngành có `\n` giữa chừng (`Mining, quarrying, and\noil and gas extraction`); tên ngành lặp trong các khối TOTAL / Men / Women / chủng tộc; ngành lồng nhau (`Manufacturing` > `Durable goods`, `Nondurable goods`; `Wholesale and retail trade` > `Wholesale trade`, `Retail trade`; `Other services` > `Other services, except private households`, `Private households`) |
| p4_t08 | `cpsaat19` A1:G20. Giờ làm việc 2023 | Hai nhóm cột: `Persons at work` (All industries / Agriculture and related / Nonagricultural) và `Percent distribution` (3 cột tương tự); hàng cha/con (`1 to 34 hours` > `1 to 4`, `5 to 14`, `15 to 29`, `30 to 34`; `35 hours and over` > `35 to 39`, `40 hours`, `41 hours and over` > `41 to 48`, `49 to 59`, `60 hours and over`); 2 hàng `Average hours` ở cuối, ô % là `–` |
| p4_t09 | `cpsaat21` A1:I28. Giờ làm theo ngành/loại lao động, phi nông nghiệp, 2023 | Header 3 tầng (`Worked 1 to 34 hours` > Total / For economic reasons / For noneconomic reasons > Usually work full time / Usually work part time; `Worked 35 hours or more`; `Average hours` > Total at work / Persons who usually work full time); chỉ có nhóm wage & salary (hàng 8-24), self-employed (26), unpaid family (28); ngành lồng nhau như t07; `–` ở I28 |
| p4_t10 | `cpsaat22` A1:I67. Người làm phi nông nghiệp theo tuổi, giới, chủng tộc, hôn nhân, full/part time | Cùng header như t09; khối `AGE AND SEX` (9), `RACE AND HISPANIC OR LATINO ETHNICITY` (40), `MARITAL STATUS` (54); trong AGE AND SEX có `Total, 16 years and over`, `Men, 16 years and over`, `Women, 16 years and over` kèm các nhóm tuổi con; trong RACE hàng `Men`/`Women` lặp dưới từng chủng tộc; trong MARITAL STATUS có `Men, 16 years and over` / `Women, 16 years and over` rồi `Married, spouse present(1)`, `Widowed, divorced, or separated(2)`, `Never married`; footnote hàng 64-67 |

### Ba bài toán cấu trúc chung (loader phải giải quyết tổng quát)
1. Header nhiều tầng + ô gộp -> làm phẳng thành tên cột đầy đủ, ví dụ `Worked 1 to 34 hours | For noneconomic reasons | Usually work full time`.
2. Nhãn hàng KHÔNG duy nhất (lặp qua các khối) -> mỗi hàng phải có thuộc tính `section` (đường dẫn khối), ví dụ `Women > Civilian labor force`.
3. Hàng cha/con và hàng tổng -> đánh dấu `is_total` / `level` để cộng/xếp hạng không đếm trùng.

## 5. Bộ 20 câu hỏi mẫu + đáp án chuẩn nội bộ (đã tự tính từ dữ liệu; dùng để tạo `tests/gold_answers.json`)

Các đáp án đánh dấu (?) có nhập nhằng; hãy dùng quy ước ghi ở mục 5.1 và đặt vào prompt. Mọi đáp án khác đã kiểm tra từ dữ liệu.

| id | file | câu hỏi (rút gọn) | đáp án chuẩn |
|---|---|---|---|
| p4_q001 | t01 | Second-youngest on admission date, last name | `Ngo` |
| p4_q002 | t01 | Score of second-oldest person | `64` (?) |
| p4_q003 | t01 | Highest score among ten youngest people | `99` |
| p4_q004 | t02 | Agri export FYTD 2024 > FYTD 2023? Yes/No | `No` (174.43 < 178.18) |
| p4_q005 | t03 | Category with highest absolute change in "Unadjusted percent change" Sep 2024 -> Oct 2024 | `Airline fares` (6.4) |
| p4_q006 | t04 | Abs diff civilian noninstitutional population vs civilian labor force, women, "Some college, no degree" | `7668` (16796 - 9128) |
| p4_q007 | t04 | Avg unemployment rate across all education levels, women, 2 decimals | `3.14` (?) (trung bình 8 cột: 6.4,3.8,3,3.3,2.6,2,2.2,1.8) |
| p4_q008 | t05 | How many more employed aged 20-24 than 16-19 across all industries | `9017` (14564 - 5547, khối Total, cộng 12 cột ngành) |
| p4_q009 | t05 | Employed 20-24 in Construction + Manufacturing | `2218` (1055 + 1163, khối Total) |
| p4_q010 | t05 | Industry with highest employed aged 16-19 | `Leisure and hospitality` (2344, khối Total) |
| p4_q011 | t05 | Age 20+: Financial Activities > Transportation and Utilities? | `Yes` (10952 > 9794, khối Total) |
| p4_q012 | t06 | Total unpaid family workers across all age groups, agriculture | `35` (?) (khớp `Total, 16 years and over`=35 và tổng các nhóm tuổi lá) |
| p4_q013 | t07 | Rank Agriculture, Manufacturing, Construction by 'Transportation and Material Moving' | `Manufacturing, Construction, Agriculture` (1217, 335, 105; khối TOTAL) |
| p4_q014 | t07 | Protective service + Service occupations except protective, Manufacturing | `265` (45 + 220, khối TOTAL) |
| p4_q015 | t08 | Persons at work, all industries, 5-14 hours, and in agriculture | `5475` (?) hoặc `134` (?) - xem 5.1 |
| p4_q016 | t08 | Hour category with highest percentage of agricultural workers | `35 hours and over` (?) (34.8; nếu chỉ xét hàng lá thì `40 hours` 33.8) |
| p4_q017 | t09 | Abs diff total in Manufacturing vs Construction in 2023 | `4826` (14880 - 10054, cột `Total at work`) |
| p4_q018 | t10 | People worked 1 to 34 hours and 35+ hours | `34282, 118705` (hàng `Total, 16 years and over`) |
| p4_q019 | t10 | Average hours, widowed/divorced/separated men and women, 16+ | `40.60, 37.60` (cột Average hours > Total at work, khối MARITAL STATUS) |
| p4_q020 | t10 | Number of workers in "Total, 16 years and over" | `152987` |

### 5.1 Quy ước giải (đưa vào prompt)
- Câu hỏi không nêu khối nào -> mặc định khối TOTAL (khối đầu tiên của bảng).
- "second-youngest on their admission date" = tuổi tại ngày nhập học (admission - birth). "oldest/youngest" không nhắc ngày nhập học = xếp theo ngày sinh. Đề phòng đồng hạng.
- "across all <categories>" / "all industries" khi bảng không có cột tổng = cộng các cột/hàng LÁ của khối đó, KHÔNG đếm trùng hàng cha và hàng con. Khi bảng đã có hàng/cột tổng rõ ràng thì ưu tiên đối chiếu với tổng đó.
- "absolute difference/change" = trị tuyệt đối.
- Xếp hạng/tìm max-min theo hạng mục: loại hàng tổng (`Total...`, `All items`, `All industries`). Khi nhập nhằng cha/con thì chọn cách hiểu thông thường nhất (max trực tiếp trên cột).
- p4_q015: "number ... in all industries who work 5-14 hours and in agriculture" - nhập nhằng; đề nghị mặc định `5475` (all industries); ghi chú trong log để người dùng xem lại. Người dùng sẽ quyết định cuối cùng.
- Đơn vị: "[Numbers in thousands]" - trả đúng số trong ô (KHÔNG nhân 1000), trừ khi câu hỏi yêu cầu.
- Tên hạng mục/ngành/nhóm giờ: trả đúng chuỗi trong ô nhãn, bỏ footnote `(1)`, thay `\n` bằng khoảng trắng đơn.
- Ô `–`, `(NA)`, rỗng = NaN (không phải 0).

## 6. Kiến trúc pipeline

```
main.py → cli.py
   A. io_utils: đọc queries.json (chấp nhận `file_name` và `file name`), nhóm câu theo file
   B. (mỗi file, cache trong bộ nhớ) loader.py → danh sách Table; sheet_view.py → text cho LLM
   C. (mỗi câu, ThreadPool, mặc định 4 luồng) agent.py:
        C1 phân loại dạng đáp án (int / float2 / yesno / text / list) từ chính câu hỏi
        C2 prompt = bản sheet gọn + câu hỏi + quy tắc → LLM sinh code pandas
        C3 sandbox chạy code → kết quả
        C4 kiểm tra dạng/NaN/lỗi → retry kèm traceback (tối đa 2 lần)
        C5 postprocess.py chuẩn hóa chuỗi
   D. io_utils: ghi submission.csv đủ id (câu thất bại ghi giá trị dự phòng) + run_log.jsonl
```

### 6.1 loader.py (code thuần, KHÔNG dùng LLM; quan trọng nhất)

Mô hình dữ liệu:
```python
@dataclass
class Table:
    file: str
    sheet: str
    title: str            # A1/A2 và dòng tiêu đề bảng (nếu có), gồm đơn vị "[Numbers in thousands]"
    year: str | None      # nếu có hàng năm gộp ngang trên header (vd 2023)
    col_names: list[str]  # tên cột phẳng, duy nhất
    df: pd.DataFrame      # cột đầu: _row (số hàng Excel), section, label, is_total, level, rồi các cột dữ liệu
    footnotes: list[str]
```

Thuật toán (mô tả để cài đặt tổng quát):
1. Dùng `openpyxl.load_workbook(path, data_only=True)` (lấy giá trị đã cache của công thức; nếu giá trị None mà ô là công thức thì thử lại bằng load thường rồi đánh dấu). Với mỗi `merged_cells.ranges`: điền giá trị ô trên-trái vào mọi ô trong vùng (trong bản sao 2D `grid`, không sửa file).
2. Xác định `cols_used` (cột có dữ liệu) và vùng dữ liệu: "hàng dữ liệu đầu tiên" = hàng đầu tiên có >= 1 ô số (int/float, không phải bool/ngày làm nhãn) trong các cột sau cột nhãn, VÀ sau đó còn nhiều hàng như vậy. Với t01 hàng 3 (có ngày/số). Chú ý: hàng năm `2023`, `2020..2024` là SỐ nhưng thuộc header -> nhận biết bằng: các ô số là số nguyên 1900-2100, nằm ở hàng phía trên một hàng chữ/đơn vị; hoặc cả hàng chỉ có số năm. Hãy xử lý hàng "chỉ gồm năm" như hàng header.
3. Header = các hàng từ hàng bắt đầu vùng bảng (sau tiêu đề A1/A2 và hàng trống) tới ngay trước hàng dữ liệu đầu tiên. Tên cột = ghép các giá trị từ tầng trên xuống, bỏ giá trị lặp liên tiếp, bỏ rỗng, thay `\n` bằng khoảng trắng và gộp khoảng trắng, nối bằng ` | `. Tên trùng thì thêm hậu tố ` #2`. Cột đầu (nhãn) đặt tên `label` (hoặc theo header ô trên-trái nếu có, nhưng giữ khóa nội bộ `label`). Cột như `Indent Level` (t03) giữ nguyên làm cột `level_raw`.
4. Duyệt các hàng dữ liệu:
   - Hàng rỗng hoàn toàn: bỏ qua.
   - Hàng chỉ có nhãn (không ô số nào) và hợp lệ không phải footnote (không bắt đầu `(1)`, `Footnotes`, `NOTE`, `Source`, không là ô gộp ngang toàn bộ chiều rộng ở cuối bảng): coi là TIÊU ĐỀ KHỐI -> cập nhật `section` hiện tại. Hàng khối có thể lồng (`AGE AND SEX` rồi `Men, 16 years and over`): giữ `section_path` dạng ngăn xếp: khối cấp 1 (toàn chữ HOA hoặc không thụt lề) và khối cấp 2 (hàng `Men, 16 years and over`, `Women, 16 years and over` có số liệu nhưng đồng thời là tiêu đề khối của các hàng con thụt lề bên dưới).
   - Hàng có số liệu: một dòng của bảng. Nếu nhãn dạng `<Nhóm>, 16 years and over` / `Total, 16 years and over` / bắt đầu bằng `Total`/`All items`: `is_total = True` và cũng khởi tạo khối con (ví dụ `Men, 16 years and over` làm `section` cho các hàng nhóm tuổi tiếp theo cho tới khi gặp hàng khối kế tiếp).
   - `level`: ưu tiên cột `Indent Level` nếu có; nếu không thì lấy `cell.alignment.indent` của ô nhãn nếu >0; nếu không thì 0. Ngoài ra đánh dấu `has_children` bằng heuristic: hàng i là cha của các hàng i+1.. liền sau nếu giá trị cột số đầu tiên của hàng i xấp xỉ bằng tổng các hàng liền sau có level lớn hơn (dung sai làm tròn +/-2). Heuristic chỉ là gợi ý (`parent_label`), không bắt buộc đúng.
5. Ép kiểu: số dạng chuỗi có dấu phẩy -> số; `–`, `-`, `(NA)`, `NA`, `n.a.`, rỗng -> NaN; datetime giữ nguyên (chuyển thành `pd.Timestamp`). Nhãn: bỏ footnote cuối ` (1)`, ` (1)(3)`, ` 2/`, ` 3/`, bỏ `\n`.
6. Xử lý nhiều bảng trên một sheet (t02 có 2 khối năm với header riêng): nếu giữa vùng dữ liệu xuất hiện lại một hàng header mới (hàng chỉ toàn chữ/năm tiếp theo sau hàng có số, ngay trước một cụm hàng số mới) thì tách thành Table thứ hai (tên: `title` + chữ ở ô trái-trên của header, ví dụ `Calendar years`). Với t02: Table 1 = Fiscal (hàng 1-7), Table 2 = Calendar (hàng 9-15). Nếu cài đặt tách bảng phức tạp, chấp nhận phương án đơn giản hơn: giữ MỘT Table nhưng thêm vào `section` giá trị `Fiscal years` / `Calendar years` (lấy từ ô gộp ở B1 / B9) và cột `year` theo từng hàng header. Quan trọng là KHÔNG mất thông tin và không nhập nhằng.

Bất biến cần giữ (viết test):
- Mọi hàng số liệu thuộc đúng một `section`.
- Không có hai cột trùng tên.
- `inspect` cho thấy với t04: tên cột như `Some college or associate degree | Some college, no degree`; hàng `Women > Civilian labor force`.
- t01: cột `Name | First`, `Name | Middle`, `Name | Last`, `Date of | Birth`, `Date of | Admission`, `Score`.

### 6.2 Câu hỏi cần "kiểu dữ liệu" nào thì loader phải bảo toàn
Ngày phải giữ datetime (tính tuổi). Số nguyên phải giữ số nguyên (không biến `5475` thành `5475.0` khi đưa vào prompt). Số thập phân giữ nguyên (`40.6`).

### 6.3 sheet_view.py
Sinh text gọn cho LLM theo từng Table:
```
FILE: p4_t10.xlsx | SHEET: cpsaat22 | UNIT: Numbers in thousands | YEAR: 2023
TITLE: 22. Persons at work in nonagricultural industries by ...
COLUMNS:
  c1 = Total at work
  c2 = Worked 1 to 34 hours | Total
  ...
ROWS (row_id | section | label | [total?] | c1 | c2 | ...):
  r10 | AGE AND SEX | Total, 16 years and over | T | 152987 | 34282 | ...
  r11 | AGE AND SEX > Total, 16 years and over | 16 to 19 years | | 5338 | ...
```
Quy tắc: dùng mã cột ngắn (`c1..cN`) trong bảng dữ liệu + bảng ánh xạ tên đầy đủ để tiết kiệm token; số in đúng định dạng; NaN in `NA`; ngày in `YYYY-MM-DD`. Nếu tổng ký tự > ngưỡng cấu hình (mặc định 60.000 ký tự), cắt: giữ header/cột đầy đủ, rút gọn các khối ít liên quan bằng cách chỉ giữ nhãn khối + ... (hoặc chạy bước chọn khối bằng 1 lần gọi LLM nhỏ). Với bộ công khai không cần cắt.
Đồng thời `df` thật được nạp vào sandbox dưới tên `tables` (list) và `df` (Table đầu tiên) để code LLM truy cập chính xác.

### 6.4 agent.py - sinh code (Program-of-Thought)
- LLM KHÔNG tự tính. LLM trả về MỘT khối code Python (trong ```python```) gán kết quả vào biến `answer`, kèm `# assumptions:` ngắn ở đầu.
- Quy ước truy cập dữ liệu để LLM dùng: `t = tables[i]`; `t.df` có các cột `_row, section, label, is_total, level` + các cột dữ liệu có tên đúng như trong COLUMNS (hoặc mã `c1..`; chọn MỘT cách và nhất quán: khuyến nghị dùng tên đầy đủ trong code qua dict `COL = {"c1": "Total at work", ...}` được cung cấp sẵn).
- Prompt hệ thống gồm: vai trò; quy ước mục 5.1; mô tả `tables`/`df`; các cạm bẫy (khối, hàng tổng, hàng cha/con, `abs`, đơn vị); yêu cầu chỉ xuất code; không in, không import ngoài danh sách cho phép.
- Few-shot: 2-3 ví dụ ngắn (một câu cộng theo khối, một câu xếp hạng, một câu tính tuổi). Không đưa đáp án của 20 câu mẫu vào prompt dưới dạng hardcode.
- Tham số LLM: temperature thấp (0-0.2). Tìm cách tắt/giảm "thinking/reasoning" nếu model hỗ trợ (kiểm tra tài liệu OpenRouter của model; tham số có thể là `reasoning` trong body) để giảm token & thời gian; có hằng cấu hình để bật lại nếu độ chính xác giảm.
- Retry (tối đa 2 lần): khi code lỗi, `answer` thiếu/NaN/rỗng, hoặc sai dạng (ví dụ yes/no ra số). Gửi lại traceback ngắn + chỉ dẫn sửa. Có ngân sách theo câu: dừng khi chi phí tích lũy > 0.07 USD hoặc thời gian > 90 giây.
- Dự phòng: nếu hết retry, gọi LLM trả lời trực tiếp từ bản sheet (không code), rồi postprocess; nếu vẫn lỗi, ghi chuỗi rỗng và log lý do (KHÔNG làm sập chương trình).
- Tùy chọn (cờ cấu hình `VOTE=1`, mặc định tắt): sinh 3 mẫu code, chạy cả 3, bỏ phiếu theo kết quả đã chuẩn hóa; chỉ dùng khi bật.

### 6.5 sandbox.py
- `exec` code trong namespace hạn chế: `pd, np, math, datetime, re, tables, df, COL` và `abs, min, max, sum, len, sorted, round, int, float, str, range, enumerate, zip, any, all, list, dict, set, tuple` (builtins whitelist); chặn `import` tùy ý, `open`, `os`, `sys`, `__import__`, `eval`, `exec`, mạng.
- Timeout cứng (mặc định 15 giây): chạy trong thread/process con có giới hạn thời gian (khuyến nghị `multiprocessing` hoặc `concurrent.futures` + kill); không để treo toàn bộ pipeline.
- Trả về `(ok, answer_raw, error_text)`. Giải phóng DataFrame sau mỗi câu; tổng RAM < 1 GB.
- Lưu ý bảo mật: đây là chạy code do LLM sinh; không cho đọc/ghi hệ thống file.

### 6.6 postprocess.py - chuẩn hóa đáp án (rất quan trọng cho Exact Match)
Dạng đáp án (`answer_kind`) suy ra từ câu hỏi bằng quy tắc regex trước, LLM chỉ làm phương án phụ:
| kind | dấu hiệu trong câu hỏi | quy tắc |
|---|---|---|
| `yesno` | `Yes or No`, `Yes/No` | đúng `Yes`/`No` |
| `int` | `integer`, `only the integer`, `without commas` | `int(round(x))`, không dấu phẩy, không `.0`, không đơn vị |
| `float2` | `rounded to two decimal places`, `exactly two decimal places` | `f"{x:.2f}"` |
| `list` | `separated by a comma and one space`, `in the order`, `descending order` | các phần tử nối bằng `", "` (đúng thứ tự yêu cầu); từng phần tử áp quy tắc int/float2/text riêng nếu câu hỏi nói rõ (vd q019 mỗi số 2 chữ số thập phân; q018 hai số nguyên không dấu phân cách nghìn) |
| `text` | `only the last name`, `category name`, `industry name`, `hour category`, v.v. | giữ đúng chuỗi trong ô, strip, bỏ footnote, thay `\n` bằng khoảng trắng |
Làm tròn: dùng `Decimal` ROUND_HALF_UP khi cần, tránh lỗi `round()` của float. Số nguyên có kiểu numpy -> chuyển sang `int` Python. Bool -> `Yes`/`No`. Nếu kết quả là Series/DataFrame/NaN -> coi là lỗi để retry.

### 6.7 llm/client.py
- Gọi OpenRouter chat completions (`https://openrouter.ai/api/v1/chat/completions`), header `Authorization: Bearer $OPENROUTER_API_KEY`; model từ env `MODEL` (mặc định `qwen/qwen3.7-flash`). Dùng `httpx` có timeout (60s), retry có backoff cho lỗi 429/5xx/timeout (tối đa 3 lần), đếm CẢ các lần retry vào chi phí.
- Đọc `usage` (prompt_tokens, completion_tokens, total) từ phản hồi; nếu API trả `cost` thì dùng, nếu không dùng giá cấu hình `PRICE_IN_PER_M` / `PRICE_OUT_PER_M` trong `config.py` (đặt giá trị mặc định rồi ghi chú là phải kiểm tra lại trên trang model).
- Trả về `LLMResult(text, prompt_tokens, completion_tokens, cost_usd, latency_s)`; một `CostTracker` theo câu hỏi, an toàn đa luồng.
- Không log/in ra key. Nếu thiếu key: thông báo rõ ràng và thoát có mã lỗi, nhưng vẫn ghi submission.csv rỗng đúng định dạng nếu đã đọc được queries.json.

### 6.8 pipeline.py / io_utils.py
- `run(data_dir, queries_path, output_path, workers, ui)`: tải queries; nhóm theo file; loader cho mỗi file MỘT lần (cache); chạy các câu bằng `ThreadPoolExecutor(max_workers=workers)`; giữ đúng thứ tự id khi ghi; sau mỗi câu cập nhật UI và ghi 1 dòng vào `run_log.jsonl` (id, file, query, code, raw, answer, kind, tokens, cost, thời gian, số lần retry, lỗi).
- Nếu file xlsx không tồn tại/hỏng: ghi dự phòng, log, tiếp tục.
- In tổng kết cuối: số câu, tổng/trung bình thời gian, token, chi phí (ra stderr).
- Ghi CSV: `csv.writer`, `newline=""`, `encoding="utf-8"`, `lineterminator="\n"`, header `id,answer`.

## 7. Giao diện (ui.py)
- Rich: banner ngắn, `Progress` với spinner + thanh tiến độ + bộ đếm `done/total`, bảng tóm tắt cuối (id, đáp án, kind, token, giây, trạng thái), màu cho OK/lỗi.
- `UI` là lớp có interface `start(total) / update(id, status, ...) / finish(summary)`; `NullUI` (log thuần ra stderr) được chọn tự động theo mục 2. Toàn bộ pipeline chỉ phụ thuộc interface này.
- `wizard`: dùng `typer.prompt`/`rich.prompt` hỏi data-dir, queries, output, workers; kiểm tra key; xác nhận; rồi gọi cùng hàm `run`.
- `inspect`: bảng Rich của DataFrame chuẩn hóa + (tùy chọn) bản sheet gọn.
- `eval`: đọc submission + gold (`{id: answer}` JSON), in đúng/sai, tỷ lệ, diff từng câu sai.

## 8. config.py (hằng số và biến môi trường)
`OPENROUTER_API_KEY`, `MODEL` (mặc định `qwen/qwen3.7-flash`), `OPENROUTER_BASE_URL`, `WORKERS=4`, `MAX_RETRIES=2`, `PER_QUESTION_COST_CAP=0.07`, `PER_QUESTION_TIME_CAP=90`, `SANDBOX_TIMEOUT=15`, `MAX_SHEET_CHARS=60000`, `PRICE_IN_PER_M`, `PRICE_OUT_PER_M`, `VOTE=0`. Đọc `.env` bằng python-dotenv nếu có, nhưng biến môi trường thật ưu tiên.

## 9. Tiêu chí nghiệm thu theo giai đoạn
- GĐ1 loader+inspect: với 10 file, in được bảng sạch; test xác nhận các bất biến mục 6.1 và các tên cột/hàng ví dụ.
- GĐ2 pipeline tối thiểu: `run` tạo `submission.csv` đủ 20 dòng đúng định dạng trên bộ mẫu; không crash khi một câu lỗi.
- GĐ3 đúng đắn: `eval` với `gold_answers.json` (mục 5) đạt >= 18/20; các câu (?) được ghi chú.
- GĐ4 giới hạn: tổng thời gian toàn bộ 20 câu <<< 40 phút (mục tiêu < 5 phút), chi phí/câu << 0.10 USD (in ra), RAM < 1 GB (kiểm tra bằng `tracemalloc`/`psutil` khi phát triển).
- GĐ5 chạy lại được: chạy từ thư mục khác, venv mới, đường dẫn tuyệt đối khác; không có đường dẫn hardcode; không có key trong mã (quét `sk-`, `OPENROUTER_API_KEY=` có giá trị).
- GĐ6 đóng gói: `scripts/make_zip.py` tạo zip < 100 MB, loại `.env`, `.venv`, `data/`, `outputs/`, `__pycache__`.

## 10. README.md (nộp) - nội dung bắt buộc
1. Yêu cầu: Python 3.11+.
2. Cài đặt: `python -m venv .venv`, kích hoạt, `pip install -r requirements.txt`.
3. Cấu hình: `cp .env.example .env`, điền `OPENROUTER_API_KEY`; hoặc `export OPENROUTER_API_KEY=...`; model mặc định `qwen/qwen3.7-flash`.
4. Chạy: `python main.py run --data-dir <thư mục xlsx> --queries <queries.json> --output <submission.csv>` (kèm `--no-ui` cho môi trường tự động).
5. Kiến trúc ngắn (5-8 dòng): loader → sheet view → LLM sinh pandas → sandbox → postprocess → CSV.
6. Ghi chú: không lưu key trong mã; mọi tham số trong `config.py`.

## 11. Ghi chú cho vấn đáp 18/10
Mã phải dễ giải thích: mỗi module một trách nhiệm, docstring đầu file mô tả "làm gì/vì sao". Có thể bị yêu cầu: đổi quy tắc chuẩn hóa đáp án (postprocess), đổi quy ước hàng tổng, đổi số lần retry/ngưỡng chi phí, thêm kiểu đáp án mới. Thiết kế phải cho phép sửa các điểm này ở một chỗ duy nhất.

## 12. Thứ tự làm (dừng sau mỗi giai đoạn)
1. Khung dự án + config + io_utils + cli/ui tối thiểu (`inspect` chạy được với loader giả).
2. loader.py + sheet_view.py + test_loader (GĐ1).
3. llm/client.py + prompts.py + agent.py + sandbox.py + postprocess.py + pipeline (GĐ2).
4. `eval` + `gold_answers.json` + log (GĐ3).
5. Tối ưu token/thời gian, retry/ngân sách, dự phòng (GĐ4).
6. UI hoàn chỉnh, wizard, README, make_zip (GĐ5-6).

Khi bắt đầu, hãy xác nhận đã hiểu bằng 5 dòng tóm tắt rồi làm GĐ1. Nếu có điểm trong đặc tả mâu thuẫn hoặc thiếu, nêu giả định bạn chọn thay vì hỏi nhiều câu.