# Guide: `sg profile`, `sg specs` và parser

| | |
|---|---|
| **Task** | F3, P0.2–P0.5 ([tasks](../tasks.md)) |
| **Trạng thái** | ✅ Đã implement (`0ea4f00`, sửa ở `fcd3ce0`, `f63aa37`) |
| **Code** | `tools/specgarage/parse.py`, `profile.py`, `config.py` |
| **Test** | `tools/tests/test_parse_profile.py`, fixture giả lập ở `tools/tests/fixtures/sources/` |

## Tính năng làm gì

**`sg specs`** đọc `specs.yaml` và kiểm tra file nguồn của từng spec có tồn tại không.

**`sg profile`** (Phase 0) đo cấu trúc spec để ra các quyết định trước khi build vault:
- tách note ở ngưỡng nào (D1);
- cách lấy `legacy_number` (D2);
- định dạng anchor/link mà parser phải hỗ trợ (D3).

Output **chỉ có số liệu thống kê**, cùng với ID anchor và tên file của các link không resolve được, **không có nội dung spec**. Vì vậy có thể gửi `profile.txt` sang máy phát triển để thảo luận.

**Parser** (`parse.py`) đọc file md và dựng:
- cây heading H1–H6 (số heading, anchor, cha/con, độ dài phần riêng và cả cây con);
- anchor, link (trong file / sang file khác / external), ảnh, bảng.

Parser này là nền tảng mà `build-vault` (T2) sẽ dùng lại.

## Cách dùng

```bash
uv run --project tools sg specs
uv run --project tools sg profile --out data/reports/profile.txt
uv run --project tools sg profile --json --out data/reports/profile.json
uv run --project tools sg profile data/sources/WRN --thresholds 1500,3000,6000
```

| Tuỳ chọn | Mặc định | Tác dụng |
|---|---|---|
| `paths…` | `data/sources/` | File `.md` hoặc thư mục (quét đệ quy) |
| `--thresholds` | `2000,3000,5000,8000` | Các ngưỡng token để mô phỏng tách note |
| `--json` | | Xuất JSON (đầy đủ hơn, có `own_text_by_level`) |
| `--out` | stdout | Ghi ra file |

### Định dạng được nhận ra

| Loại | Dạng |
|---|---|
| Heading | ATX `#`–`######` có khoảng trắng sau `#`. Bỏ qua heading nằm trong code fence |
| Anchor | `{#_Toc123}`, `[]{#_Ref456 .anchor}` (pandoc); `<a id=…>`, `<a name=…>`, `<span id=…>` |
| Link | `[t](#_Ref1)`, `[t](Other.docx#_Ref2)`, `[t](file:///C:/…/Other.docx#_Ref2)`, `<a href=…>`, reference definition `[x]: …` (không tính footnote `[^1]:`) |
| URL có ngoặc | `7820ZXXXXG000_E_(Warning)_260220.docx`, ngoặc cân bằng trong URL |
| Ảnh | `![alt](path)`, `<img src=…>`, `![[…]]` |
| Bảng | pipe, grid, `<table>` |
| Encoding | UTF-8, có hoặc không có BOM |

## Đọc kết quả

Output mẫu (một spec):
```
=== data/sources/WRN/7820ZXXXXG000_E_(Warning)_260220.md
  lines 8,120  ~tokens 190,400
  headings 612  H1:9  H2:74  H3:260  H4:201  H5:62  H6:6
    numbered 0  with anchor 598  duplicate titles 41  level jumps 3  setext? 0
  subtree tokens by level (n / p50 / p90 / max):
    H1:     9 /  18,300 /  40,100 /   52,000
    …
  tables pipe 180  grid 12  html 0
  images 95  missing files 0
  anchors defined 1,240  syntax {'attribute': 1240, 'html': 0}
  links internal 830 (unresolved 4)  cross-file 57 {'resolved': 40, 'unknown_file': 17}  external 2  other 0
  split simulation (threshold → notes, p50 / p90 / max tokens, over, tiny<50):
     3,000 →   410     280 / 1,900 /  6,200  over 5  tiny 120
```
(Số liệu minh hoạ, không phải của spec thật.)

| Chỉ số | Nếu thấy | Thì |
|---|---|---|
| `anchors defined` = 0 nhưng `links internal` > 0 | Parser không nhận ra định dạng anchor | Tìm cách một `_Ref…` được định nghĩa trong md. Tạo fixture **giả lập** cùng định dạng, rồi mở rộng `ATTR_ID_RE` / `HTML_ID_RE` (P0.5) |
| `unresolved` > khoảng 5 % số link trong file | Anchor mất hoặc sai định dạng | Như trên. Xem mẫu ở `internal_unresolved_sample` trong JSON |
| `numbered` thấp so với tổng số heading | Word auto-numbering bị mất khi convert | T2 phải **tính `legacy_number` từ vị trí trong cây** |
| `duplicate titles` cao | Nhiều heading trùng tên ("Overview"…) | Bình thường. Đây là lý do đặt tên note theo ID (D3) |
| `level jumps` > 0 | Heading nhảy cấp (H2 → H4) | Báo expert. Parser vẫn xử lý được |
| `setext?` cao | Converter dùng heading kiểu gạch chân | Cần bổ sung parser (P0.5) |
| `missing files` > 0 | Ảnh không nằm đúng chỗ so với file md | Đặt lại folder ảnh cạnh file md như lúc convert |
| `cross-file … unknown_file` | Có spec tham chiếu tới spec ngoài bộ trong `specs.yaml` | Xem danh sách cuối report. Quyết định thêm vào registry hay coi là tham chiếu ngoài |

Link sang file khác được khớp theo **tên file (stem)**, rồi theo **số tài liệu** (phần trước `_` đầu tiên). Nhờ vậy link tới bản spec cũ hơn (khác ngày trong tên file) vẫn resolve được.

## Chọn ngưỡng tách (D1)

Cách mô phỏng: đi từ trên xuống cây heading, dừng ở heading có cả cây con ≤ ngưỡng. Heading lớn hơn ngưỡng thì phần riêng của nó thành một note, và các con tiếp tục được tách.

- **`over`:** số note vẫn lớn hơn ngưỡng. Đây là section lá, không tách nhỏ hơn được.
- **`tiny`:** số note < 50 token, thường là heading cha chỉ có tiêu đề.

**Chọn ngưỡng nhỏ nhất mà `over` gần 0 và `tiny` không quá nhiều.** Khởi điểm hợp lý là **3000**. Ghi quyết định vào D1 trong design doc. Nếu cần ngưỡng khác nhau cho từng spec thì thêm `max_tokens:` vào `specs.yaml`.

## Giới hạn đã biết

- Token là ước lượng `ký tự / 4`.
- Heading setext không được coi là heading, chỉ được đếm ở `setext?`.
- Anchor trong body được gán về section chứa nó, nhưng không nằm trong danh sách anchor của heading.
- Không xử lý: comment HTML nhiều dòng, indented code block, link trong inline code.
- Nhận diện grid table là heuristic.

**Khi sửa parser:** luôn thêm **fixture giả lập** tái hiện định dạng đó vào `tools/tests/fixtures/` trước. Không copy nội dung spec thật vào repo public.

## Test

```bash
uv run --project tools --group dev pytest tools/tests/test_parse_profile.py
```

Có test cho: cây heading, code fence, link và ảnh, phân loại link, resolve cross-file, mô phỏng tách, CLI, các trường hợp biên (`#######`, `#tag`, fence lồng nhau, footnote, `file://`, `IGN_ON`, BOM).
