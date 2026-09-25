# Guide: `sg profile`, `sg specs` và parser

| | |
|---|---|
| **Task** | F3, P0.2–P0.5 ([tasks](../tasks.md)) |
| **Trạng thái** | ✅ Đã implement (`0ea4f00`; sửa ở `fcd3ce0`, `f63aa37`; P0.5 anchor/slug/diagnose ở branch `phase0/p05-anchor-resolution`) |
| **Code** | `tools/specgarage/parse.py`, `profile.py`, `config.py` |
| **Test** | `tools/tests/test_parse_profile.py`, fixture giả lập ở `tools/tests/fixtures/sources/` (DMA, DMB, DMC) |
| **Kết quả Phase 0** | [`../phase0-findings.md`](../phase0-findings.md) |

## Tính năng làm gì

**`sg specs`** đọc `data/specs.yaml` và kiểm tra file nguồn của từng spec có tồn tại không.

**`sg profile`** (Phase 0) đo cấu trúc spec để ra các quyết định trước khi build vault:
- tách note ở ngưỡng nào (D1);
- cách lấy `legacy_number` (D2);
- định dạng anchor/link mà parser phải hỗ trợ (D3).

Output **chỉ có số liệu thống kê**: số đếm, ID anchor, số heading, tên file. `--diagnose` thêm **khung markup** trong đó mọi từ đã bị thay bằng `x`. Vì vậy có thể gửi report sang máy phát triển.

**Lưu ý:** anchor dạng slug (ví dụ `acc-power-status`) được tạo từ tiêu đề heading. Kiểm tra lại trước khi gửi ra ngoài nếu tiêu đề heading được coi là nhạy cảm.

**Parser** (`parse.py`) đọc file md và dựng:
- cây heading H1–H6 (số heading, anchor, cha/con, độ dài phần riêng và cả cây con);
- anchor (tường minh và ngầm từ tiêu đề), vị trí đặt anchor;
- link (trong file / sang file khác / external), ảnh, bảng.

`build-vault` (T2) dùng lại parser này.

## Cách dùng

```bash
uv run --project tools sg specs
uv run --project tools sg profile --out data/reports/profile.txt
uv run --project tools sg profile --diagnose --out data/reports/profile-diagnose.txt
uv run --project tools sg profile --json --out data/reports/profile.json
uv run --project tools sg profile data/sources/WRN --thresholds 1500,3000,6000
```

| Tuỳ chọn | Mặc định | Tác dụng |
|---|---|---|
| `paths…` | `data/sources/` | File `.md` hoặc thư mục (quét đệ quy) |
| `--thresholds` | `2000,3000,5000,8000` | Các ngưỡng token để mô phỏng tách note |
| `--diagnose` | | Giải thích anchor chưa resolve (xem [bên dưới](#chế-độ---diagnose)). Chậm hơn vài giây với spec lớn |
| `--json` | | Xuất JSON, đầy đủ hơn (có `own_text_by_level`) |
| `--out` | stdout | Ghi ra file |

### Định dạng được nhận ra

| Loại | Dạng |
|---|---|
| Heading | ATX `#`–`######` có khoảng trắng sau `#`. Bỏ qua heading trong code fence |
| Anchor tường minh | `{#_Toc123}`, `[]{#_Ref456 .anchor}` (pandoc); thuộc tính `id=` / `name=` trên **mọi tag HTML**: `<a id>`, `<span id>`, `<p id>`, `<td id>`… |
| Anchor ngầm (slug) | Tạo từ tiêu đề heading theo 3 kiểu:<br>• pandoc: `### 1.2 Abnormal Checksum Detection` → `abnormal-checksum-detection`, trùng thì thêm `-1`, `-2`<br>• GitHub: `12-abnormal-checksum-detection`<br>• GitHub bỏ số: `abnormal-checksum-detection`<br>Anchor tường minh luôn được ưu tiên |
| Link | `[t](#_Ref1)`, `[t](Other.docx#_Ref2)`, `[t](file:///C:/…/Other.docx#_Ref2)`, `<a href=…>`, reference definition `[x]: …` (không tính footnote `[^1]:`) |
| URL có ngoặc | `7820ZXXXXG000_E_(Warning)_260220.docx`, ngoặc cân bằng trong URL |
| Ảnh | `![alt](path)`, `<img src=…>`, `![[…]]` |
| Bảng | pipe, grid, `<table>` |
| Encoding | UTF-8, có hoặc không có BOM |

### Anchor thuộc về section nào (placement)

| Placement | Khi nào | Thuộc về |
|---|---|---|
| `heading` | Trên cùng dòng với heading | Heading đó |
| `before_heading` | Dòng chỉ có anchor, dòng có nội dung kế tiếp là heading | **Heading kế tiếp** (Word bookmark trên heading thường được xuất kiểu này) |
| `after_heading` | Dòng chỉ có anchor, ngay sau heading | Heading đó |
| `table` | Trong `<table>…</table>` hoặc dòng bảng pipe | Section chứa bảng |
| `standalone` | Dòng chỉ có anchor, giữa nội dung | Section chứa nó |
| `inline` | Cùng dòng với nội dung | Section chứa nó |

## Đọc kết quả

Output mẫu (fixture giả lập DMC):
```
=== …/9999ZXXXXC000_E_(Demo Anchors)_260101.md
  lines 30  ~tokens 216
  headings 4  H1:2  H2:2  H3:0  H4:0  H5:0  H6:0
    numbered 4  with anchor 3  duplicate titles 0  level jumps 0  setext? 0
  heading numbers: unnumbered 0  duplicate numbers 0  level-minus-depth {'0': 4}
  …
  anchors defined 6  implicit heading slugs 8
    syntax {'html:a': 5, 'html:p': 1}
    placement {'before_heading': 3, 'after_heading': 1, 'inline': 1, 'table': 1}
  links internal 8 (resolved by slug 3, unresolved 3 links / 3 distinct anchors)  cross-file 0 {} …
    unresolved sample: _Ref500030, _Ref599999, abnormal-checksum-detect
  other doc numbers mentioned in text: {'7821ZXXXXF000': 2}
  split simulation (threshold → notes, p50 / p90 / max tokens, over, tiny<50):
        20 →     5      30 /     84 /      84  over 4  tiny 3
             over: 1 (84), 1.2 (59), preamble (30), 1.1 (28)
  diagnose unresolved anchors: present but unrecognised 1  absent slug-like 1  absent other 1
    present  _Ref500030 @line 26: <w:bookmarkStart w:name="{ANCHOR}"/>x….
    slug     abnormal-checksum-detect  closest heading slug: abnormal-checksum-detection
    absent   _Ref599999
```

| Chỉ số | Nếu thấy | Thì |
|---|---|---|
| `anchors defined` = 0 nhưng `links internal` > 0 | Parser không nhận ra định dạng anchor | Chạy `--diagnose` |
| `unresolved … links` > khoảng 5 % số link | Anchor mất, sai định dạng, hoặc slug không khớp | Chạy `--diagnose` |
| `placement` | Phần lớn là `before_heading` | Bình thường: bookmark Word đặt trước heading, đã được gán đúng |
| `resolved by slug` | > 0 | Converter tạo link tới heading bằng slug của tiêu đề. T2 sẽ đổi các link này sang `[[ID]]` |
| `numbered` thấp | Word auto-numbering bị mất khi convert | T2 phải **tính `legacy_number` từ vị trí trong cây** |
| `duplicate numbers` > 0 | Cùng số heading xuất hiện nhiều lần (đánh số lại theo chương, hoặc phụ lục) | `legacy_number` không duy nhất. Dùng kèm `heading_path` |
| `level-minus-depth` | Ví dụ `{'0': 1500}`: H3 có số `x.y.z` | Khác 0 nghĩa là cấp heading lệch với độ sâu của số |
| `duplicate titles` cao | Nhiều heading trùng tên | Bình thường. Đây là lý do đặt tên note theo ID (D3) |
| `level jumps` > 0 | Heading nhảy cấp (H2 → H4) | Báo expert. Parser vẫn xử lý được |
| `setext?` cao | Converter dùng heading kiểu gạch chân | Cần bổ sung parser |
| `missing files` > 0 | Ảnh không nằm đúng chỗ so với file md | Đặt lại folder ảnh cạnh file md như lúc convert |
| `other doc numbers mentioned in text` | Spec nhắc số tài liệu khác trong nội dung | Đây là tham chiếu cross-spec dạng chữ, dùng cho `spec-consistency` |
| `cross-file … unknown_file` | Link tới spec ngoài bộ `data/specs.yaml` | Quyết định thêm vào registry hay coi là tham chiếu ngoài |
| `over:` | Note vẫn lớn hơn ngưỡng, liệt kê theo **số heading** | Thường là section lá có bảng lớn. Expert xem có cần tách theo nội dung không |

Link sang file khác được khớp theo **tên file (stem)**, rồi theo **số tài liệu** (phần trước `_` đầu tiên).

### Chế độ `--diagnose`

Mỗi anchor chưa resolve được phân vào một trong ba loại:

| Loại | Nghĩa | Việc cần làm |
|---|---|---|
| `present` (present but unrecognised) | Chuỗi anchor **có** trong file nhưng ở dạng parser chưa hiểu | Xem khung markup, ví dụ `<w:bookmarkStart w:name="{ANCHOR}"/>`. Tạo fixture giả lập cùng dạng rồi mở rộng parser |
| `slug` (absent slug-like) | Link dạng slug không khớp slug nào của heading | So với `closest heading slug`: lệch do quy tắc slug (bổ sung kiểu slug) hay do heading đã đổi tên (link cũ) |
| `absent` (absent other) | Chuỗi anchor **không có ở đâu** trong file | Bookmark bị mất khi convert, hoặc link trỏ tới bookmark đã bị xoá trong Word. Đối chiếu với quy trình verify của converter |

Khung markup giữ lại tên tag và tên thuộc tính, thay mọi giá trị thuộc tính bằng `…` (trừ anchor, hiện là `{ANCHOR}`), và thay mọi từ bằng `x`.

## Chọn ngưỡng tách (D1)

Cách mô phỏng: đi từ trên xuống cây heading, dừng ở heading có cả cây con ≤ ngưỡng. Heading lớn hơn ngưỡng thì phần riêng của nó thành một note, và các con tiếp tục được tách.

- **`over`:** note vẫn lớn hơn ngưỡng (section lá không tách nhỏ hơn được), liệt kê theo số heading.
- **`tiny`:** note < 50 token, thường là heading cha chỉ có tiêu đề.

**Chọn ngưỡng nhỏ nhất mà `over` gần 0 và `tiny` không quá nhiều.** Kết quả áp dụng cho 3 spec hiện tại: [`phase0-findings.md`](../phase0-findings.md).

## Giới hạn đã biết

- Token là ước lượng `ký tự / 4`.
- Heading setext không được coi là heading, chỉ được đếm ở `setext?`.
- Không xử lý: comment HTML nhiều dòng, indented code block, link trong inline code.
- Nhận diện grid table là heuristic.
- Slug ngầm chỉ theo 3 kiểu nêu trên. Converter dùng kiểu khác thì `--diagnose` sẽ hiện ở loại `slug`.
- `DOC_NO_RE` nhận số tài liệu theo dạng `7820ZXXXXG000` (4 số, `Z`, 4 ký tự, 1 chữ, 3 số). Họ số khác cần sửa regex.

**Khi sửa parser:** luôn thêm **fixture giả lập** tái hiện định dạng đó vào `tools/tests/fixtures/` trước. Không copy nội dung spec thật vào repo public.

## Test

```bash
uv run --project tools --group dev pytest tools/tests/test_parse_profile.py
```

Có test cho:
- cây heading, code fence, link và ảnh, phân loại link;
- resolve cross-file, mô phỏng tách, CLI;
- các trường hợp biên: `#######`, `#tag`, fence lồng nhau, footnote, `file://`, `IGN_ON`, BOM;
- placement anchor (trước / sau heading, bảng, inline), `id` trên tag bất kỳ;
- slug pandoc / GitHub và đánh số trùng `-1`;
- `--diagnose`: phân loại đủ 3 loại, và khung markup không lộ chữ;
- danh sách `over` chỉ dùng số heading.
