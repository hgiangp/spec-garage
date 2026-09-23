# Bàn giao: tiếp tục trên máy dữ liệu

> **Dành cho Claude (hoặc người) trên máy dữ liệu.** Đọc file này trước tiên, sau đó đến `CLAUDE.md`, [`tasks.md`](tasks.md), [`phase0-findings.md`](phase0-findings.md), [`next-steps.md`](next-steps.md).
> Cập nhật: 2026-09-23. Từ thời điểm này, việc phát triển chuyển sang máy dữ liệu.

## 1. Bối cảnh ngắn

- **Mục tiêu:** ingest spec automotive (Word → md) thành vault theo section, có Section ID ổn định, rồi improve từng section bằng skill và có expert review. So sánh before/after bằng RAG để sau.
- **Hai máy:**
  - Máy phát triển push lên GitHub (repo **public**).
  - Máy dữ liệu có `data/` (git repo local riêng) và **không push được**.
  - Code viết trên máy dữ liệu được chuyển về máy phát triển bằng `git bundle` (§6).
- **Quy tắc bắt buộc:** không đưa nội dung spec vào repo public (code, fixture, docs, commit message); fixture luôn là **giả lập**; ngôn ngữ theo `CLAUDE.md` §Ngôn ngữ; "Definition of done" theo `CLAUDE.md`.

## 2. Trạng thái

| Phần | Trạng thái |
|---|---|
| Design, `CLAUDE.md`, skills (bản nháp), `knowledge/` | ✅ |
| `sg profile` / `specs` / `init-data` / `new-id`, `ids.py` (T1, T6) | ✅ |
| P0.5: anchor trên mọi tag, slug heading kiểu pandoc, placement, `--diagnose` | ✅ (branch `phase0/p05-anchor-resolution`) |
| P0.1, P0.2 (dựng `data/`, chạy profile) | ✅ trên máy dữ liệu |
| T2 `build-vault`, T5 `export`, T4 `validate`, T3 `get`/`related` | ⏳ **việc tiếp theo** |

Branch mới nhất `phase0/p05-anchor-resolution` đã chứa toàn bộ commit. Chưa có PR nào vào `main`: tạo **một PR từ branch này vào `main`** trên máy phát triển.

## 3. Quy trình convert (đã xác nhận với chủ repo)

```
docx ─(tiền xử lý: shape/EMF/WMF → PNG, text trích từ hình đưa vào alt text)→ .shapes.docx
     ─pandoc -f docx -t markdown --extract-media=./images→ md
     ─(hậu xử lý: table phức tạp → GFM pipe table, giữ dữ liệu; một số bảng vẫn là HTML)→ data/sources/<CODE>/*.md
```

Hệ quả:
- **Link tới heading:** pandoc thay bookmark trên heading bằng slug `auto_identifiers` và viết lại các link. P0.5 sinh slug theo đúng quy tắc này (đã kiểm trên mẫu thật).
- **Anchor của caption bảng/hình:** `<span id="_Ref…" class="anchor"></span>` ngay trước text caption (placement `inline`).
- **Không có link giữa các spec.** Tham chiếu chéo spec chỉ ở dạng chữ ("refer to …"). Không xử lý ở ingest. `spec-consistency` phải nhận diện bằng chữ.
- **Ảnh:** toàn bộ PNG trong `images/`, alt text chứa text trích từ hình. `spec-diagram` dùng alt text làm nguồn chính.
- **Mục lục ở đầu file:** mỗi heading một link slug lồng số trang, ví dụ `[1.1. Overview [4](#overview)](#overview)`. Mục lục này thổi phồng số link nội bộ.
- **Ký tự đặc biệt:** gạch nối không ngắt U+2011 (`Table 1‑1`), `＝` full-width, ngoặc kép cong, escape `\>` `\_`. Search phải chuẩn hoá ký tự.
- **Bảng HTML còn sót** có số thứ tự ẩn trong `<ol start="N"><li></li></ol>`.

## 4. Câu hỏi mở cần dữ liệu (làm trước T2)

| # | Việc | Cách làm | Kết quả cần có |
|---|---|---|---|
| Q1 | Link `_Ref` lỗi: WRN 942, EWA 278 (trước P0.5) | `uv run --project tools sg profile --diagnose --out data/reports/profile-diagnose.txt` | Tỷ lệ `present` / `absent`. Link text của chúng phần lớn là `Table x‑y`, `Figure x‑y` hay số heading? |
| Q2 | `_Ref` "lúc bấm được lúc không" | Lấy 5–10 trường hợp: anchor có trong md không? nằm trong bảng HTML / pipe? mở bằng trình xem nào? | Lỗi do dữ liệu hay do trình xem. Trình xem không nhảy tới `<span id>` HTML là chuyện thường; sau T2 link sẽ được viết lại |
| Q3 | Nguyên nhân `_Ref` bị mất (nếu `absent`) | Đối chiếu với docx: bookmark nằm trong shape (đã thành PNG)? trong ô bảng (bị chuyển sang GFM)? | Nếu do converter: **sửa converter trước baseline** rồi chạy lại profile để kiểm tra hồi quy |
| Q4 | Ngưỡng tách D1 | Expert xem [`phase0-findings.md` §3](phase0-findings.md#3-ngưỡng-tách-d1) | Đề xuất 3000 |
| Q5 | **Cú pháp link trong vault** (§5) | Chủ repo quyết | Chốt trước T2 |

## 5. Quyết định cần chốt trước T2: có dùng Obsidian không?

Obsidian **không bắt buộc**. Nó chỉ là trình xem cho expert. Cú pháp link trong vault quyết định vault có gắn chặt với Obsidian hay không:

| Lựa chọn | Link tới heading | Link tới caption `_Ref` | Ưu | Nhược |
|---|---|---|---|---|
| **A. Markdown chuẩn (khuyến nghị)** | `[1.2.1 CAN data](LIN-0012.md#can-data)` | `[Table 1‑1](LIN-0014.md#_Ref131938121)`, giữ `<span id>` gốc | VS Code, GitHub và mọi trình xem đều hiểu. Obsidian vẫn mở được. Export gần như giữ nguyên | Obsidian không nhảy tới `<span id>` (chỉ mở đúng note) |
| B. Obsidian (wikilink + block ref) | `[[LIN-0012#1.2.1. CAN data\|CAN data]]` | `[[LIN-0014#^ref-131938121\|Table 1‑1]]` | Bấm được chính xác trong Obsidian, có graph/backlink | Chỉ Obsidian hiểu. Export phải chuyển ngược |

Với A:
- `CLAUDE.md` §Quy ước (Link) và `next-steps.md` T2 bước 5 phải cập nhật từ `[[…]]` sang link markdown.
- `data/vault/.obsidian/` giữ lại cũng không sao (để Obsidian vẫn dùng được), đổi `useMarkdownLinks: true`.

## 6. Cập nhật đặc tả so với `next-steps.md` (áp dụng khi làm T2–T5)

1. **Link giữa các spec:** bỏ hoàn toàn khỏi T2 (không có dữ liệu). Bước 1 của T2 chỉ cần bản đồ anchor trong từng spec.
2. **Link tới heading:** resolve qua slug (`Document.resolve`), viết lại theo cú pháp đã chốt ở §5.
3. **Link tới caption `_Ref`:** trỏ tới note chứa caption, giữ nguyên `<span id>` tại chỗ.
4. **Link không resolve:** giữ **nguyên link gốc**, gắn `#broken-ref` (hoặc comment `<!-- broken-ref -->`). **Không bao giờ đoán đích.**
5. **Mục lục (preamble, note `-0000`):** giữ nguyên văn để round-trip. Skill bỏ qua note này. Profile/validate tính riêng link mục lục.
6. **Bảng pipe và HTML:** giữ nguyên văn, không bao giờ cắt giữa bảng.
7. **Quy tắc relink:** sau tag `baseline-original` **không bao giờ chạy lại `build-vault`**. Mọi cải thiện độ chính xác sau này (khôi phục `_Ref` bị mất, thêm dạng anchor) là một bước `sg relink` **tại chỗ**, chỉ sửa link `#broken-ref`, và phải được áp dụng lên **cả baseline** (tag mới, ví dụ `baseline-relinked-1`) để không làm sai phép so sánh before/after.
8. **Việc nhỏ còn sót của P0.5** (làm khi tiện):
   - profile tách riêng link mục lục;
   - `--diagnose` phân loại link text (`Table` / `Figure` / số / khác), chỉ in dạng;
   - slug một từ (ví dụ `output`) bị xếp vào nhóm "absent other";
   - fixture giả lập theo đúng dạng pandoc: mục lục lồng số trang, `<span class="anchor">`, bảng HTML `<ol start>`, ảnh PNG có alt text dài và `{width=…}`.

## 7. Gate: độ chính xác cần tới đâu

**Nguyên tắc:** link *chưa resolve* (hiện rõ, không mất gì) được phép; link resolve *sai đích* hoặc mất nội dung thì không.

| Gate | Điều kiện | Mở ra việc |
|---|---|---|
| **A** | Không có | `spec-analyze` trên `data/sources/` cho cụm thí điểm. Bắt đầu glossary/lessons. **Làm được ngay, song song với T2** |
| **B** | Round-trip `export(build(source))` = source sau chuẩn hoá: **100 %**. Heading nhận ra: **100 %**. `sg validate`: **0 lỗi**. Link sai đích: **0 trên mẫu khoảng 30** (expert bấm thử). Mọi link lỗi đều giữ link gốc. Tỷ lệ resolve **không tính mục lục**: mục tiêu ≥ khoảng 90 %, **không chặn**. Expert xem khoảng 10 note mỗi spec | Tag `baseline-original` trong `data/` |
| **C** | Gate B, cộng với `sg get` / `related` / `validate` hoạt động | Improve (`spec-restructure`, `spec-parameterize`…) trên cụm thí điểm |

**Mốc đóng băng converter = Gate B.** Trước mốc này thì sửa converter thoải mái. Sau mốc này, mọi thay đổi converter đều buộc phải build lại và gắn lại baseline.

## 8. Thứ tự đề xuất

1. Pull `phase0/p05-anchor-resolution` (hoặc `main` sau khi merge PR). Chạy `uv run --project tools --group dev pytest tools/tests`.
2. Q1–Q3 (§4). Song song: **Gate A**.
3. Chủ repo chốt Q4, Q5.
4. T2 → T5 → T4 → T3 theo `next-steps.md` §3 cộng với §6 ở trên. Mỗi ticket có test, guide, cập nhật `tasks.md`.
5. Gate B → tag baseline.
6. Gate C → Phase 2 (S1–S6 trong `tasks.md`).

## 9. Chuyển commit từ máy dữ liệu về GitHub

Máy dữ liệu không push được. Dùng `git bundle` để giữ nguyên commit và hash:

```bash
# Máy dữ liệu (repo public, KHÔNG phải data/)
git bundle create ../sg-<branch>.bundle origin/<nhánh gốc>..<branch>
# Kiểm tra bằng mắt trước khi chuyển: git log -p origin/<nhánh gốc>..<branch>
#   → không có nội dung spec trong code, fixture, docs, commit message

# Chép file .bundle sang máy phát triển, rồi:
git fetch ../sg-<branch>.bundle <branch>:<branch>
git push -u origin <branch>
```
