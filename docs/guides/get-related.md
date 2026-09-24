# Guide: `sg get` và `sg related`

| | |
|---|---|
| **Task** | T3 ([tasks](../tasks.md)) |
| **Trạng thái** | ✅ Đã implement (branch `phase1/t3-get-related`) |
| **Code** | `tools/specgarage/section.py`, `tools/specgarage/vault.py` (chỉ mục section, dùng chung với `validate`) |
| **Test** | `tools/tests/test_section.py` (dùng fixture `DMD` của T2) |

## Tính năng làm gì

Hai lệnh các skill dùng để đọc spec **theo section**, không phải mở cả file hay tự grep:

- **`sg get <ID>`:** in nội dung một section. Kèm theo:
  - **file và khoảng dòng** trong vault, để agent sửa đúng chỗ;
  - **breadcrumb**, chuỗi heading cha để biết ngữ cảnh;
  - số token ước lượng.
- **`sg related <ID>`:** liệt kê các section mà section này **link tới** (out) và **được link từ** (in). Lệnh này chỉ in ID, tiêu đề và kích thước, không in nội dung. Agent tự `sg get` những section cần đọc.

**Section** là mọi heading có ID:
- heading gốc của một note (ID = ID của note);
- heading con nằm trong note (ID lấy từ dòng `<!-- id: … -->` ngay dưới heading đó).

Preamble (`-0000`) cũng là một section, nhưng không có heading.

## Cách dùng

```bash
uv run --project tools sg get WRN-0342                  # note: kèm frontmatter
uv run --project tools sg get WRN-0342 --no-frontmatter
uv run --project tools sg get WRN-0345                  # heading con: chỉ phần của nó (kể cả heading con của nó)
uv run --project tools sg get WRN-0345 --json

uv run --project tools sg related WRN-0342
uv run --project tools sg related WRN-0342 --depth 2
uv run --project tools sg related WRN-0342 --include-preamble --json
```

Output `get`:

```
DMD-0003 (in DMD-0001)  data/vault/DMD/DMD-0001.md:52-55  ~31 tokens
1. Demo Function > 1.1. Overview > 1.1.1. Sub Behaviour

### 1.1.1. Sub Behaviour
<!-- id: DMD-0003 | legacy: 1.1.1 | anchors: _Ref100020 -->

The demo lamp shall stay on for 200 ms.
```

Dòng đầu gồm: ID, note chứa nó, **`file:dòng-đầu-dòng-cuối`** (số dòng tính cả frontmatter, khớp khi mở file) và số token. Dòng thứ hai là breadcrumb.

Output `related`:

```
DMD-0001  1. Demo Function  ~249 tokens
links to (1):
  DMD-0006  Appendix  ~11 tokens  via #appendix
linked from (1):
  DMD-0000  Preamble  ~109 tokens  via #demo-function, #overview
```

`via` là anchor của link, ví dụ `#_Ref123`, `#some-slug`, hoặc `DMD-0001.md#…` sau T2b. Mỗi dòng là một section. Section nào nằm trong một note khác ID của chính nó thì có thêm `(in <note>)`.

| Tuỳ chọn | Lệnh | Tác dụng |
|---|---|---|
| `--no-frontmatter` | get | Với note: chỉ in phần thân |
| `--json` | get | `{id, note, path, lines, title, breadcrumb, tokens, text}` |
| `--depth N` | related | Đi theo link N bước (mặc định 1). Kết quả có cột `depth` |
| `--include-preamble` | related | Tính cả link từ mục lục (preamble). Mặc định bỏ, vì mục lục link tới mọi heading |
| `--json` | related | `{id, note, title, tokens, out: [...], in: [...]}` |

## Quy tắc tính link

- **Resolve qua `_anchors.yaml`**, nên chạy được trên vault chưa relink, nơi link vẫn là `#_Ref…` hay `#slug`. Link `[…](<ID>.md#frag)` do `sg relink` viết ra sau này cũng được hiểu.
- **Link nằm trong section nào** thì lấy section **nhỏ nhất** chứa dòng đó.
- **Không tính link nội bộ của chính section đang hỏi.** Hỏi cả note `WRN-0342` thì link từ phần này sang heading con của chính nó bị bỏ, vì `sg get WRN-0342` đã có nội dung đó. Hỏi một heading con thì link sang phần khác của cùng note **vẫn** được tính.
- **Link tự trỏ** (ví dụ "see Table 1‑1" trỏ vào caption trong chính section) bị bỏ.

## Quy tắc cho agent

- **Đọc section:** dùng `sg get <ID>`, không đọc cả file note hay file source.
- **Lấy ngữ cảnh:** `sg related <ID>`, rồi chỉ `sg get` những mục thật sự cần, để tiết kiệm context. Các section lớn có sẵn số token để cân nhắc.
- **Sửa:** dùng khoảng dòng trong output của `get` để sửa đúng chỗ trong file note, rồi chạy `sg validate`.

## Giới hạn đã biết

- **Chỉ trong một spec.** Không có link giữa các spec (tham chiếu chéo spec chỉ ở dạng chữ, xem `handoff.md` §3). `spec-consistency` phải tự tìm theo chữ.
- **Tiêu đề** in ra là tiêu đề heading gốc, kể cả số (ví dụ `1.1. Overview`), không phải `title` trong frontmatter.
- **Mỗi lần gọi, cả vault của spec được đọc lại** (WRN khoảng 250 note). Với một lần gọi thì chấp nhận được. Nếu skill gọi hàng trăm lần liên tiếp thì nên dùng `--json` và gom yêu cầu lại.
- **Heading con thiếu dòng `<!-- id -->`** thì không có section riêng: nó bị tính vào section cha. `sg validate` (V05) sẽ báo.

## Cách test

```bash
uv run --project tools --group dev pytest tools/tests/test_section.py
```

Các trường hợp được test:
- chỉ mục section: mọi heading có ID, cha/con, breadcrumb;
- `get` cho note và cho heading con, **khoảng dòng khớp với file**;
- `related`: link trong section, loại link nội bộ, preamble là tuỳ chọn, `--depth`, link kiểu `<ID>.md#frag` sau relink;
- CLI và `--json`.
