# Guide: `sg build-vault`

| | |
|---|---|
| **Task** | T2 ([tasks](../tasks.md#t2--kế-hoạch-chi-tiết)) |
| **Trạng thái** | ✅ Đã implement |
| **Code** | `tools/specgarage/build_vault.py`, `tools/specgarage/notes.py` |
| **Test** | `tools/tests/test_build_vault.py`, fixture `tools/tests/fixtures/sources/DMD/` |

## Tính năng làm gì

Tách mỗi file spec trong `data/sources/` thành nhiều note trong `data/vault/<CODE>/`, mỗi note là một section, có **Section ID ổn định**.

Điểm quan trọng nhất: **nội dung note là văn bản gốc, nguyên văn.** Chỉ hai thứ khác đi:

1. **đường dẫn ảnh**, vì file ảnh thật sự chuyển sang `attachments/`;
2. thêm dòng `<!-- id: … -->` dưới mỗi heading con (heading không phải heading gốc của note).

**Không** viết lại link, **không** đổi cú pháp anchor. Link `[Table 1‑1](#_Ref100010)` trong vault vẫn y như trong source. Việc đổi link sang dạng trỏ tới note là `sg relink` (T2b), chạy sau, khi vault đã được kiểm chứng. Tách như vậy vì viết lại link là thao tác rủi ro nhất (resolve sai đích thì mất thông tin một cách âm thầm), còn build là thứ sinh ra baseline.

Hệ quả có thể kiểm chứng được: **nối các note lại theo `_manifest.yaml` thì ra đúng file gốc.** Đã kiểm trên cả ba spec thật (WRN 19,613 dòng không rỗng, EWA 6,275, LIN 5,383 — giống hệt).

## Cách dùng

```bash
uv run --project tools sg build-vault --dry-run    # xem trước, không ghi gì
uv run --project tools sg build-vault              # build cả ba spec
uv run --project tools sg build-vault WRN --force  # build lại một spec
```

Output:

```
WRN: 247 notes, 1593 headings, 4022 anchors, 269 images, largest note ~16,499 tokens
EWA: 127 notes, 394 headings, 1122 anchors, 88 images, largest note ~5,660 tokens
LIN: 71 notes, 219 headings, 517 anchors, 9 images, largest note ~7,688 tokens
vault written to …/data/vault
```

| Tuỳ chọn | Tác dụng |
|---|---|
| `--max-tokens N` | Ngưỡng tách, mặc định **3000** (D1) |
| `--dry-run` | Chỉ in thống kê, không ghi file |
| `--force` | Build lại thư mục vault đã tồn tại (xoá rồi ghi lại) |
| `--i-know-baseline-exists` | Build kể cả khi tag `baseline-original` đã tồn tại. **Gần như không bao giờ dùng** |

## Sinh ra những gì

```
data/vault/
├─ WRN/
│  ├─ WRN-0000.md … WRN-1590.md   note, tên file chỉ là ID
│  ├─ _manifest.yaml              cây note, next_id, id_width, source_sha256, max_tokens
│  ├─ _anchors.yaml               anchor → ID, và heading ID → note ID
│  └─ _toc.md                     mục lục, link markdown
└─ attachments/WRN/               ảnh được copy sang đây
```

**Một note:**

```markdown
---
id: WRN-0342
spec: WRN
title: Buzzer Parameters
aliases: ['3.2.4 Buzzer Parameters']
legacy_number: '3.2.4'
heading_path: ['3 Function Description', '3.2 Buzzer Control', '3.2.4 Buzzer Parameters']
level: 3
anchors: [_Ref512345678]
refs_out: [WRN-0120]
status: original
derived_from: []
---
### 3.2.4 Buzzer Parameters

Nội dung nguyên văn, link cũng nguyên văn: [Table 1‑1](#_Ref512349999).

#### 3.2.4.1 Timing constraints
<!-- id: WRN-0343 | legacy: 3.2.4.1 | anchors: _Ref512349999 -->
```

**`_anchors.yaml`** là thứ thay cho việc viết lại link:

```yaml
spec: WRN
anchors:            # anchor (tường minh hoặc slug heading) → ID của heading sở hữu nó
  _Ref512345678: WRN-0345
  buzzer-parameters: WRN-0342
notes:              # heading ID → note chứa nó (chỉ ghi khi hai cái khác nhau)
  WRN-0345: WRN-0342
```

## Quy tắc

**Cách chia note.** Duyệt cây heading từ trên xuống, dừng khi cả cây con nằm dưới ngưỡng. Heading quá lớn trở thành một note chỉ chứa phần văn bản của chính nó, các con thành note riêng. Thuật toán nằm trong `notes.plan_notes` và **dùng chung với `sg profile`** — nếu hai bên lệch nhau thì số liệu Phase 0 không nói gì về vault thật.

**ID.** Mọi heading H1–H6 đều được cấp ID theo thứ tự tài liệu (`0001`, `0002`, …), không chỉ heading trở thành note, để link trỏ vào một H5 vẫn có đích. Preamble (nội dung trước heading đầu tiên) là `-0000`. `next_id` trong manifest = số heading + 1.

**Note phủ kín file.** Mỗi dòng thuộc đúng một note. Đây là điều kiện để `sg export` chỉ là phép nối.

**Không cắt giữa bảng HTML.** Nếu một ranh giới note rơi vào giữa `<table>…</table>`, nó được đẩy xuống sau khi bảng đóng.

**Anchor ngay trên heading** (Word bookmark của heading) được kéo vào note của heading đó, không để lại ở cuối note trước.

**An toàn:**
- Từ chối ghi đè vault đã tồn tại nếu không có `--force`.
- Từ chối **tuyệt đối** nếu tag `baseline-original` đã tồn tại trong repo `data/`. Sau khi có baseline, không bao giờ build lại — cải thiện link là `sg relink` tại chỗ.
- `source_sha256` trong manifest cho biết vault được build từ đúng bản nguồn nào.

## Giới hạn đã biết

- **Preamble là mục lục và rất to.** WRN ~16.5k token, EWA ~5.7k. Nó luôn vượt ngưỡng. Đây là chủ ý: giữ nguyên văn để round-trip, skill bỏ qua note `-0000`.
- **Hai section nội dung vượt ngưỡng**: WRN heading `2` (~9.6k token) và LIN `3.1.6.2` (~7.7k). Không tách được nữa vì chúng không có heading con. Expert quyết ở Phase 2.
- **Token là ước lượng** (ký tự / 4). Đủ để chọn ranh giới, không dùng để tính context.
- **Heading nằm trong bảng HTML** sẽ làm build dừng với `SplitError`, vì không thể bắt đầu một note ở giữa bảng. Không xảy ra với ba spec hiện tại.
- **Ảnh trùng tên** ở hai thư mục khác nhau sẽ bị báo `WARNING` và chỉ copy file đầu tiên.
- `refs_out` được sinh từ `_anchors.yaml`, **không** từ link đã viết lại (vì link chưa được viết lại).

## Cách test

```bash
uv run --project tools --group dev pytest tools/tests/test_build_vault.py
```

Fixture `DMD` mô phỏng đúng những dạng converter thật xuất ra: mục lục lồng số trang, anchor caption trong `<span>`, bảng HTML có `<ol start>` ẩn, ảnh có alt text **xuống dòng** và `{width=…}`, hai heading trùng tiêu đề (pandoc thành slug `overview-1`), một heading không có số.

Test quan trọng nhất: `test_note_text_is_the_source_text` — nối các note lại phải ra đúng văn bản gốc. Đây là thứ giữ cho build trung thực.