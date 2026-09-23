# Spec Garage

Repo để ingest và improve spec automotive (Word → Markdown + ảnh).
- Thiết kế và các quyết định (D1–D13): `docs/spec-pipeline-design.md`.
- Việc cần làm tiếp và đặc tả Phase 1: `docs/next-steps.md`.
- Task list và trạng thái: `docs/tasks.md`. Hướng dẫn từng tính năng: `docs/guides/`.

**Giai đoạn hiện tại:** Phase 0 (profile dữ liệu) → Phase 1 (vault) → Phase 2 (skills improve). RAG/chatbot để sau.

## Chính sách dữ liệu và hai máy

- **Repo public (GitHub):** chỉ chứa code, skill, tri thức chung, tài liệu. **Không bao giờ chứa nội dung spec.**
- **`data/`:** toàn bộ dữ liệu rút ra từ spec. Repo public luôn ignore thư mục này. Trên máy có dữ liệu, `data/` là **một git repo local riêng**.
- **Máy phát triển:** viết code, push lên GitHub.
- **Máy dữ liệu:** chỉ `git pull` repo public, không push. Làm việc với spec trong `data/`.
- Claude Code được phép đọc và sửa spec trong `data/`. **Không** đưa nội dung spec vào dịch vụ bên ngoài khác (web search, WebFetch, API bên thứ ba, artifact công khai).
- Không commit nội dung domain (trích spec, thuật ngữ riêng, lessons) vào repo public. Những thứ đó thuộc `data/knowledge/`.

## Cấu trúc

| Đường dẫn | Repo | Vai trò |
|---|---|---|
| `specs.yaml` | public | Registry: mã spec ↔ file nguồn |
| `knowledge/` | public | Tri thức **chung**: style guide, quality checklist, templates section |
| `.claude/skills/` | public | Skill improve (chỉ chứa quy trình) |
| `tools/` | public | CLI `sg`. `tools/specgarage/data_template/` là khung cho `data/` |
| `data/sources/<CODE>/` | data | Spec gốc Word→md + ảnh. **Chỉ đọc** |
| `data/vault/<CODE>/` | data | Obsidian vault, mỗi note là một section. Nguồn sự thật sau Phase 1. Mọi improve sửa ở đây |
| `data/vault/<CODE>/_manifest.yaml` | data | Cây section, thứ tự, `next_id`, `retired`. Chỉ sửa qua `sg` |
| `data/knowledge/` | data | Tri thức **domain**: `glossary.md`, `lessons.md` |
| `data/reports/`, `data/evals/` | data | Output của profile/validate/skill; eval case |

## Quy ước (D2, D3)

- **Section ID:** `<CODE>-<NNNN>`, ví dụ `WRN-0342`.
  - Gán cho mọi heading H1–H6. Preamble (nội dung trước heading đầu tiên) là `<CODE>-0000`.
  - ID mới chỉ lấy qua `sg new-id <CODE>`.
  - Không bao giờ đổi hoặc dùng lại ID. ID không mang ý nghĩa: số heading nằm ở `legacy_number`.
- **Tên file note:** chỉ là ID, ví dụ `data/vault/WRN/WRN-0342.md`. Tiêu đề nằm trong `title` và `aliases`.
- **Heading con trong note:** ngay dưới heading có dòng `<!-- id: WRN-0345 | legacy: 3.2.4.1 | anchors: _Ref512349999 -->`.
- **Link:** `[[WRN-0342|Tiêu đề]]`, hoặc `[[WRN-0342#Heading con|…]]`. Hyperlink Word (`#_Ref…`, `#_Toc…`) được resolve qua trường `anchors`.
- **Frontmatter:** `id, spec, title, aliases, legacy_number, heading_path, level, anchors, refs_out, status, derived_from`.
  - `status` nhận một trong: `original | proposed | reviewed | approved`.
  - `refs_out` do script sinh, không sửa tay.
- **Tách / gộp / xoá section:**
  - Tách: phần mới nhận ID mới kèm `derived_from`.
  - Gộp: section bị gộp vào ghi `merged_into` trong `retired` của manifest.
  - Xoá: đưa ID vào `retired` kèm lý do.

## Guardrail khi improve (D9)

1. **Không bịa giá trị.** Thiếu thông tin thì ghi `> [!todo] ASSUMPTION: …` để expert điền.
2. **Không đổi ngữ nghĩa** (giá trị, điều kiện, thứ tự hành vi) nếu chưa được expert xác nhận. Mỗi lần improve là một branch trong repo `data/` để review bằng `git diff`.
3. **Giữ nguyên ID, anchors, legacy_number.** Không xoá comment `<!-- id: … -->`.
4. Chạy `sg validate` sau mỗi lần sửa (khi đã implement).
5. Trước khi sửa, đọc:
   - `knowledge/style-guide.md`
   - `data/knowledge/glossary.md`
   - `data/knowledge/lessons.md` (lessons được ưu tiên hơn style guide khi mâu thuẫn)

## Lệnh

Chạy từ gốc repo:

```bash
uv run --project tools sg init-data [--migrate-legacy]              # máy dữ liệu: tạo data/ (git repo local)
uv run --project tools sg specs                                     # kiểm tra registry và file nguồn
uv run --project tools sg profile --out data/reports/profile.txt    # Phase 0
uv run --project tools sg new-id WRN [-n 3]                         # cấp ID mới
uv run --project tools --group dev pytest tools/tests               # test tools
```

Các lệnh `build-vault`, `get`, `related`, `validate`, `export` đã có chỗ trong CLI nhưng chưa implement (Phase 1).

## Definition of done (mọi commit/PR tính năng)

Commit chỉ có code thì **chưa xong**. Mỗi task phải kèm:
1. **`docs/tasks.md`:** cập nhật trạng thái, branch/commit, ghi chú.
2. **`docs/guides/<tính-năng>.md`** (tạo mới hoặc cập nhật):
   - tính năng làm gì;
   - cách dùng (lệnh, ví dụ, output);
   - quy tắc cho agent và người dùng;
   - giới hạn đã biết;
   - cách test.
3. **Test** cho tính năng, dùng fixture giả lập, và toàn bộ test phải pass.
4. **`CLAUDE.md`** nếu thêm hoặc đổi lệnh, quy ước.
5. **Commit message** giải thích *vì sao* và mọi điểm lệch khỏi đặc tả trong `docs/next-steps.md`.

## Git

**Repo public:**
- `main` luôn là bản đã duyệt.
- Mỗi ticket là một branch `phase1/<ticket>-<mô-tả>` và một PR.

**Repo `data/` (local):**
- `main` luôn là bản đã được expert duyệt.
- Mỗi lần improve là một branch `improve/<ID>-<mô-tả>`.
- Tag `baseline-original` được gắn ngay sau lần build vault đầu tiên được duyệt. Đây là bản "before", không được viết lại.
