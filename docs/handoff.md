# Trạng thái và điểm bắt đầu

> **Đọc file này trước tiên**, sau đó đến `CLAUDE.md`, [`tasks.md`](tasks.md), [`next-steps.md`](next-steps.md).
> Cập nhật: 2026-09-23 (sau khi chuyển hai repo lên GitLab nội bộ và chốt Q1–Q5).

## 1. Bối cảnh ngắn

- **Mục tiêu:** ingest spec automotive (Word → md) thành vault theo section, có Section ID ổn định, rồi improve từng section bằng skill và có expert review. So sánh before/after bằng RAG để sau.
- **Hai repo, cùng trên GitLab nội bộ, không trộn lịch sử:**
  - `spec-garage` — code, skill, tri thức chung, tài liệu.
  - `data/` — spec gốc, vault, tri thức domain, report, eval. Bị repo code ignore.
- **Quy tắc bắt buộc:** nội dung spec không bao giờ nằm trong repo code (kể cả fixture, docs, commit message); fixture luôn **giả lập**; không đưa spec ra dịch vụ bên ngoài; ngôn ngữ theo `CLAUDE.md` §Ngôn ngữ; "Definition of done" theo `CLAUDE.md`.

> Lịch sử: trước 2026-09-23 repo code nằm public trên GitHub, máy dữ liệu chỉ được pull và code chuyển đi bằng `git bundle`. Mô hình đó **không còn dùng nữa**.

## 2. Trạng thái

| Phần | Trạng thái |
|---|---|
| Design, `CLAUDE.md`, skills (bản nháp), `knowledge/` | ✅ |
| `sg profile` / `specs` / `init-data` / `new-id`, `ids.py` (T1, T6) | ✅ |
| Phase 0 trọn vẹn: dựng `data/`, profile 3 spec, P0.5 anchor resolution | ✅ |
| Q1–Q5 (anchor, ngưỡng tách, cú pháp link, phạm vi T2) | ✅ đã chốt, xem §4 |
| T2 `build-vault` (T2-lite) | ✅ branch `phase1/t2-vault-decisions`, [guide](guides/build-vault.md). 445 note, nối lại ra đúng bản gốc |
| T5 `export` + `--check` | ✅ branch `phase1/t5-export`, [guide](guides/export.md). **Round-trip OK trên cả 3 spec thật** (2026-09-24) |
| T4 `validate` | ✅ branch `phase1/t4-validate`, [guide](guides/validate.md) |
| T3 `get`/`related` | ⏳ **việc tiếp theo: T3**. Song song: chạy `sg validate` trên 3 spec thật (V1) |
| T2b `relink` | ⏳ sau Gate B |

`data/`: branch `main`, đã push lên GitLab. Chưa có tag `baseline-original`.

## 3. Quy trình convert (đã xác nhận với chủ repo)

```
docx ─(tiền xử lý: shape/EMF/WMF → PNG, text trích từ hình đưa vào alt text)→ .shapes.docx
     ─pandoc -f docx -t markdown --extract-media=./images→ md
     ─(hậu xử lý: table phức tạp → GFM pipe table, giữ dữ liệu; một số bảng vẫn là HTML)→ data/sources/<CODE>/*.md
```

Hệ quả:
- **Link tới heading:** pandoc thay bookmark trên heading bằng slug `auto_identifiers` và viết lại các link. P0.5 sinh slug theo đúng quy tắc này, kể cả hậu tố `-1`, `-2` cho slug trùng.
- **Anchor của caption bảng/hình:** `<span id="_Ref…" class="anchor"></span>` ngay trước text caption, cộng với `<h6 id>` và `<figure id>`.
- **Không có link giữa các spec.** Tham chiếu chéo spec chỉ ở dạng chữ ("refer to …"). Không xử lý ở ingest. `spec-consistency` phải nhận diện bằng chữ.
- **Ảnh:** toàn bộ PNG trong `images/`, alt text chứa text trích từ hình. `spec-diagram` dùng alt text làm nguồn chính.
- **Mục lục ở đầu file:** mỗi heading một link slug lồng số trang. Mục lục này thổi phồng số link nội bộ, và là lý do preamble của WRN nặng ~16.5k token.
- **Ký tự đặc biệt:** gạch nối không ngắt U+2011 (`Table 1‑1`), `＝` full-width, ngoặc kép cong, escape `\>` `\_`. Search phải chuẩn hoá ký tự.
- **Bảng HTML còn sót** có số thứ tự ẩn trong `<ol start="N"><li></li></ol>`.

## 4. Các câu hỏi đã chốt

| # | Câu hỏi | Kết luận |
|---|---|---|
| Q1–Q3 | `_Ref` không resolve được (trước P0.5: WRN 942, EWA 278, LIN 156) | **Đã giải quyết bằng P0.5.** Profile chạy lại: **0 link unresolved trên cả ba spec** (WRN 2224 link, EWA 1042, LIN 456). Không phải sửa converter. Lưu ý: con số này chỉ chứng minh anchor **tồn tại**, chưa chứng minh **đúng đích** — việc đó thuộc Gate B |
| Q4 | Ngưỡng tách D1 | **3000** cho cả ba spec → 445 note, p90 ≈ 2.2k token |
| Q5 | Cú pháp link trong vault | **Markdown chuẩn** `[text](WRN-0342.md#…)`, không dùng wikilink |
| Q6 | Có cần Obsidian không? | **Không.** Vault chỉ là thư mục markdown có quy ước. Obsidian là trình xem tuỳ chọn cho expert, không nằm trên đường tới hạn |
| Q7 | Phạm vi T2 | **T2-lite:** build tách note + ID + frontmatter + ảnh, **giữ nguyên link**, sinh `_anchors.yaml`. Viết lại link là ticket riêng T2b `sg relink`, chạy sau Gate B |

## 5. Đặc tả T2–T5 (điểm khác so với bản đầu của `next-steps.md`)

1. **Link giữa các spec:** bỏ hoàn toàn (không có dữ liệu). Bản đồ anchor chỉ cần trong từng spec.
2. **Build không viết lại link và không đổi anchor.** Link và anchor giữ nguyên văn; build chỉ chèn `<!-- id: … -->` dưới heading con và đổi đường dẫn ảnh. Build sinh `_anchors.yaml` (`anchors: anchor → heading ID`, `notes: heading ID → note ID`). Xem `next-steps.md` §3 T2 và T2b.
3. **Link không resolve** (ở bước relink): giữ **nguyên link gốc**, gắn `#broken-ref`. **Không bao giờ đoán đích.**
4. **Mục lục (preamble, note `-0000`):** giữ nguyên văn để round-trip. Skill bỏ qua note này.
5. **Bảng pipe và HTML:** giữ nguyên văn, không bao giờ cắt giữa bảng.
6. **Quy tắc relink:** sau tag `baseline-original` **không bao giờ chạy lại `build-vault`**. Mọi cải thiện độ chính xác link là một bước `sg relink` **tại chỗ**, và phải được áp lên **cả baseline** (tag mới, ví dụ `baseline-relinked-1`) để không làm sai phép so sánh before/after.
7. **Việc nhỏ còn sót của P0.5** (làm khi tiện): profile tách riêng link mục lục; `--diagnose` phân loại link text; fixture giả lập theo đúng dạng pandoc (mục lục lồng số trang, `<span class="anchor">`, bảng HTML `<ol start>`, ảnh PNG có alt text dài và `{width=…}`).

## 6. Gate: độ chính xác cần tới đâu

**Nguyên tắc:** link *chưa resolve* (hiện rõ, không mất gì) được phép; link resolve *sai đích* hoặc mất nội dung thì không.

| Gate | Điều kiện | Mở ra việc |
|---|---|---|
| **A** | Không có | `spec-analyze` trên `data/sources/` cho cụm thí điểm. Bắt đầu glossary/lessons. **Làm được ngay, song song với T2** |
| **B** | Round-trip `export(build(source))` = source sau chuẩn hoá: **100 %**. Heading nhận ra: **100 %**. `sg validate`: **0 lỗi**. Expert xem khoảng 10 note mỗi spec: ranh giới note hợp lý, bảng còn nguyên, ảnh hiển thị | Tag `baseline-original` trong `data/` |
| **C** | Gate B, cộng với `sg get` / `related` / `validate` hoạt động | Improve (`spec-restructure`, `spec-parameterize`…) trên cụm thí điểm |
| **D** | `sg relink --dry-run` cho thấy tỷ lệ resolve ≥ ~90 % (không tính mục lục) và expert bấm thử ~30 link: **0 link sai đích** | Chạy `sg relink` thật, gắn tag `baseline-relinked-1` |

**Mốc đóng băng converter = Gate B.** Trước mốc này thì sửa converter thoải mái. Sau mốc này, mọi thay đổi converter đều buộc phải build lại và gắn lại baseline.

## 7. Thứ tự việc

1. ✅ Dọn dẹp, chốt quyết định vào docs.
2. ✅ **T2 `build-vault`** (T2-lite).
3. ✅ **T5 `export` + round-trip** (`sg export --check`).
4. ✅ **T4 `validate`**. Trên dữ liệu thật: build + `export --check` OK cả ba spec; còn chạy `sg validate` (V1).
   Tiếp: **T3 `get`/`related`**. Song song: **Gate A** (`spec-analyze` trên `data/sources/`).
5. Gate B → tag `baseline-original`.
6. Gate C → Phase 2 (S1–S6 trong `tasks.md`).
7. T2b `relink` → Gate D → tag `baseline-relinked-1`.
 