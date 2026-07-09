## inclusion: always

# Quy Tắc Làm Việc Của Leader Team

## 1. Cú pháp điều khiển

### /ask (mặc định)

- Chỉ phân tích và trả lời câu hỏi.
- Không lập kế hoạch thực thi.
- Không đề xuất thay đổi code trừ khi được yêu cầu.

### /plan

- Phân tích yêu cầu.
- Lập kế hoạch thực hiện chi tiết.
- Chưa được sửa code.
- Chưa chạy lệnh.
- Mục tiêu là xác định hướng xử lý trước khi thực thi.

### /go (Sử dụng 3 sub-agents trong tình huống phù hợp)

- Phân tích yêu cầu.
- Lập kế hoạch thực hiện.
- Thực thi sửa code.
- Sau khi sửa phải:
  - Review lại code liên quan.
  - Chạy check.
  - Chạy app nếu cần.
  - Test lại toàn bộ luồng bị ảnh hưởng.
  - Gọi API bằng shell nếu có backend.
  - Test UI nếu có frontend.

- Không được kết thúc khi chưa xác nhận trạng thái hoạt động.

### /test (sử dụng trong folder test để tạo các file không tạo ở ngoài)

- Chỉ dùng để kiểm thử.
- Không sửa chức năng mới.
- Xác nhận:
  - Bug đã hết chưa.
  - Có phát sinh bug khác không.
  - Có ảnh hưởng tính năng cũ không.

Nếu không có prefix:
=> Mặc định là /ask.

---

# 2. Quy trình tiếp nhận yêu cầu

Khi nhận yêu cầu:

## Bước 1: Hiểu yêu cầu

Tóm tắt:

- Mục tiêu
- Vấn đề
- Kết quả mong muốn

Sau đó lọc:

### Keywords chính

Ví dụ:

- login
- oauth
- websocket
- tauri
- tray
- update
- cache

---

## Bước 2: Tra cứu lịch sử dự án

Tìm kiếm theo keywords:

```bash
git log --oneline --all --grep="<keyword>"

git log -p --grep="<keyword>"
```

Mục tiêu:

- Tìm commit liên quan.
- Xem cách xử lý cũ.
- Tránh tái tạo bug đã từng fix.

Sau khi đọc commit phải:

- Tóm tắt nguyên nhân.
- Tóm tắt giải pháp cũ.
- Tóm tắt rủi ro cần tránh.

Khi xem commit bằng:

```bash
git show <commit>
```

Đọc xong phải thoát ngay:

```bash
q
```

Không để treo terminal.

---

# 3. Xử lý tài liệu tham chiếu

## Trường hợp A: Local Path

Ví dụ:

```text
.agents/rules/project-map.md
/docs
/reference-project
```

Yêu cầu:

- Đọc toàn bộ nội dung liên quan.
- Hiểu cấu trúc.
- Đối chiếu với source hiện tại.
- Tìm giải pháp có thể tái sử dụng.
- Không copy mù quáng.

Đánh giá:

- Học được gì.
- Không nên áp dụng gì.
- Giải pháp nào phù hợp nhất hiện tại.

---

## Trường hợp B: Link Online

Ví dụ:

```text
Github
Medium
StackOverflow
Official Docs
```

Yêu cầu:

- Đọc nhanh đúng trọng tâm.
- Chỉ lấy thông tin liên quan.
- Đóng tab ngay sau khi đọc.
- Không lan man ngoài phạm vi task.

Ưu tiên:

1. Official Docs
2. Github Source
3. StackOverflow
4. Medium
5. Các nguồn khác

---

# 4. Đọc cấu trúc dự án

Nếu tồn tại:

```text
.agents/rules/project-map.md
```

Phải đọc trước khi lập kế hoạch.

Mục tiêu:

- Hiểu dependency.
- Hiểu module liên quan.
- Xác định vùng ảnh hưởng.

Sau khi sửa code:

Phải kiểm tra keyword vừa sửa còn xuất hiện ở đâu trong `.agents/rules/project-map.md` để tránh bỏ sót luồng liên quan.

---

# 5. Phân loại hệ điều hành

Mọi task phải xác định rõ:

## Windows

- Windows 10
- Windows 11

## macOS Intel

- x86_64

## macOS Apple Silicon

- arm64

Nếu có khác biệt:

Phải ghi rõ:

```text
Ảnh hưởng Windows:
...

Ảnh hưởng Mac Intel:
...

Ảnh hưởng Apple Silicon:
...
```

Không được giả định các nền tảng hoạt động giống nhau.

---

# 6. Quy tắc lập Flow

Flow phải:

- Ngắn gọn.
- Theo thứ tự từ trên xuống dưới.
- Có mục tiêu rõ ràng.

Ví dụ:

### Task 1

Xác định nguyên nhân bug.

### Task 2

Xác định vùng code bị ảnh hưởng.

### Task 3

Thiết kế hướng sửa.

### Task 4

Thực hiện sửa code.

### Task 5

Review code.

### Task 6

Check build.

### Task 7

Test.

### Task 8

Tổng kết.

---

# 7. Quy tắc Tauri

## Rust

Không chạy check trong giai đoạn lập kế hoạch.

Chỉ chạy sau khi đã sửa xong:

```bash
cargo check
```

Nếu cần:

```bash
cargo test
```

---

## Bun

Luôn sử dụng:

```bash
bun install
bun run dev
bun run build
```

Không tự ý chuyển sang:

```bash
npm
```

hoặc

```bash
yarn
```

trừ khi dự án đang sử dụng chúng.

---

# 8. Quy tắc chống code thừa

Không được:

- Duplicate code.
- Copy-paste logic.
- Tạo utility trùng chức năng.
- Hardcode khi đã có config.
- Tạo workaround tạm thời nếu có thể sửa đúng gốc.

Ưu tiên:

1. Tái sử dụng.
2. Refactor hợp lý.
3. Giảm technical debt.

---

# 9. Quy tắc vị trí file Test

**Mọi file test** (Python script, JSON config, shell script test, v.v.) PHẢI được tạo/lưu trong folder:

```text
/Users/opalx14/GitHub/pmc-labs/test/
```

KHÔNG tạo test file ở:

- `/scripts/` (đã có scripts build, clean, etc.)
- `/src/` (production code)
- `/src-tauri/` (production code)
- root project (`/test_*.py`)

Khi cần tạo test mới:

1. Tạo file trong `/test/` folder
2. Nếu test cần config path (cookies, images, profiles): dùng `/test/test_paths.json` làm source of truth
3. Reference trong rule này

Mục đích:

- Tách biệt test khỏi production code
- Dễ tìm khi cần regression test
- Không pollute scripts/ với file tạm

## 9.1. Quy tắc tái sử dụng test file có sẵn

**TRƯỚC KHI tạo test mới**, PHẢI:

1. Đọc `/test/TEST_MAP.md` để biết test nào đã có sẵn
2. Nếu test đã tồn tại và phù hợp → **DÙNG LẠI**, KHÔNG tạo mới
3. Nếu test tương tự đã có nhưng khác scenario → MỞ RỘNG file cũ (thêm test case mới), KHÔNG tạo file mới trùng mục đích
4. CHỈ tạo file mới khi:
   - Chưa có test nào cover feature đó
   - Hoặc test cũ đã quá lớn (>300 dòng) và cần tách module

**CẤM**: tạo test mới mà có file cũ đã cover cùng mục đích → tạo duplicate → vi phạm rule 8 (chống code thừa).

## 9.2. Test Map

Mọi test file PHẢI được khai báo trong `/test/TEST_MAP.md` với format:

```text
- test_<feature>.py — <mục đích>, <khi nào dùng>, <expected behavior>
```

Khi tạo test mới: cập nhật TEST_MAP.md cùng lúc.
Khi xoá test: xoá entry trong TEST_MAP.md cùng lúc.

## 9.3. Test Files hiện có (snapshot nhanh)

Danh sách test đang có trong `/test/` — đọc nhanh để biết file nào test luôn cho nhanh. Chi tiết đầy đủ ở `/test/TEST_MAP.md`.

### Gemini / veo_engine

- **`test_webapi.py`** — Regression test Gemini webapi (HTTP client, deprecated path) cho text-only.
  - Khi nào dùng: Sau khi re-login `veo3gv03`, muốn verify webapi còn hoạt động.
  - 4 test cases: init client (~2s) → simple prompt "PONG" (~3-7s) → big VN prompt (~3-7s) → production storyboard JSON parse 3 scenes (~7s).
  - Cookie expired → vẫn work anonymous mode cho text, KHÔNG timeout.

- **`test_webapi_image.py`** — Regression test webapi với image upload.
  - Khi nào dùng: Sau khi login lại veo3gv03, verify image upload qua webapi có work không.
  - 1 test case: gửi `prompt + image` qua `client.generate_content(files=[...])`.
  - Cookie expired → **TIMEOUT 60s** (bug đã biết); Cookie fresh → ~5-10s.

### Config

- **`test_paths.json`** — Source of truth paths (cookies, profiles, test images).
  - Khi nào dùng: Bất kỳ test nào cần đọc cookie path / image path / profile email.
  - Structure: `profiles.<name>.cookie_file`, `test_images.<name>`, `test_settings.default_timeout_seconds`, `test_settings.warn_about`.

### veo_engine auth

- **`test_session_check.py`** — Unit test cho `_has_real_session()` trong login.py (phân biệt cookies login thật vs logout).
  - Khi nào dùng: Mỗi khi sửa logic check session, verify 8 case: real session / tracking-only / expired / wrong domain / empty / chỉ PSIDTS / veo3gv03 thật / giả lập logout (xoá \_\_Secure-1PSID).
  - Expected: 8/8 PASS.
  - Quick run: `python3 test/test_session_check.py`.

- **`test_verify_veo3gv03_session.py`** — Playwright e2e test navigate gemini.google.com với cookies, check redirect + send prompt "Reply PONG".
  - Khi nào dùng: Sau khi update Gemini UI selector hoặc refresh cookies, verify end-to-end session work.
  - ⚠️ Selector response element cần update (dùng `.response-container-content` thay vì `.model-response`).

- **`test_debug_veo3gv03.py`** — Debug version với screenshot + dump DOM textbox selectors.
  - Khi nào dùng: Khi test_verify timeout, cần biết selector nào work + screenshot trạng thái page.

---

# 10. Báo cáo sau mỗi task

Sau mỗi task phải ghi:

### Đã làm

- ...

### Kết quả

- ...

### Ảnh hưởng

- ...

### Còn tồn đọng

- ...

---

# 11. Báo cáo cuối cùng

## Yêu cầu ban đầu

...

## Nguyên nhân

...

## Giải pháp

...

## Đã kiểm tra

- Code review
- Build
- Test

## Kết quả

✅ Hoàn thành

hoặc

⚠️ Chưa hoàn thành:

- Lý do
- Kế hoạch tiếp theo

---

# Nguyên tắc quan trọng nhất

Không đoán.

Không kết luận khi chưa đọc code.

Không sửa khi chưa xác định nguyên nhân.

Không kết thúc khi chưa kiểm tra kết quả thực tế.
