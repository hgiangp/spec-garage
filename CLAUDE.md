# Spec Garage

Repo để ingest và improve spec automotive (Word → Markdown + ảnh).
- **Bắt đầu phiên làm việc mới: đọc `docs/handoff.md` trước.**
- Thiết kế và các quyết định (D1–D13): `docs/spec-pipeline-design.md`.
- Việc cần làm tiếp và đặc tả Phase 1: `docs/next-steps.md`.
- Task list và trạng thái: `docs/tasks.md`. Hướng dẫn từng tính năng: `docs/guides/`.

**Giai đoạn hiện tại:** Phase 0 (profile dữ liệu) → Phase 1 (vault) → Phase 2 (skills improve). RAG/chatbot để sau.

## Chính sách dữ liệu và hai repo

Cả hai repo đều nằm trên **GitLab nội bộ của công ty**. Không có remote nào ra ngoài.

| | Repo code (`spec-garage`) | Repo dữ liệu (`data/`) |
|---|---|---|
| Chứa | code, skill, tri thức chung, tài liệu | spec gốc, vault, tri thức domain, report, eval |
| Remote | `…/giangpth13/spec-garage.git` | `…/giangpth13/data.git` |
| Nội dung spec | **không bao giờ** | đây là chỗ của nó |

- **`data/` bị repo code ignore** (`.gitignore`) và là **một git repo riêng**. Hai repo không bao giờ trộn lịch sử với nhau.
- Lý do giữ tách đôi (dù cả hai đều nội bộ): vòng đời review khác nhau, `data/` có ~370 file ảnh nhị phân, và baseline/tag của dữ liệu phải độc lập với lịch sử code.
- Fixture test trong `tools/tests/fixtures/` **luôn là spec giả lập**, không bao giờ copy từ spec thật.
- Không commit nội dung domain (trích spec, thuật ngữ riêng, lessons) vào repo code. Những thứ đó thuộc `data/knowledge/`.
- Claude Code được phép đọc và sửa spec trong `data/`. **Không** đưa nội dung spec vào dịch vụ bên ngoài (web search, WebFetch, API bên thứ ba, artifact công khai).

## Ngôn ngữ

| Tiếng Việt (tạm thời) | Tiếng Anh (bắt buộc) |
|---|---|
| Tài liệu trong `docs/`, guide, `CLAUDE.md`, README | Code, comment, docstring, tên biến |
| | Skill: `SKILL.md`, `references/` và mọi file đi kèm (skill cũ còn tiếng Việt sẽ chuyển dần) |
| Trao đổi với người dùng | CLI help, log, message, thông báo lỗi |
| | Commit message |
| | Nội dung spec và mọi thứ ghi vào vault (requirement, bảng, `ASSUMPTION`, `question`, mô tả ảnh) |
| | Report do agent sinh (`data/reports/`), glossary, lessons |
| | Eval case, bộ câu hỏi vàng |

Spec hiện tại là tiếng Anh. Mọi output mà agent ghi vào `data/` đều bằng tiếng Anh.

## Cấu trúc

| Đường dẫn | Repo | Vai trò |
|---|---|---|
| `specs.yaml` | code | Registry: mã spec ↔ file nguồn |
| `knowledge/` | code | Tri thức **chung**: style guide, quality checklist, templates section |
| `.claude/skills/` | code | Skill improve (chỉ chứa quy trình) |
| `tools/` | code | CLI `sg`. `tools/specgarage/data_template/` là khung cho `data/` |
| `data/sources/<CODE>/` | data | Spec gốc Word→md + ảnh. **Chỉ đọc** |
| `data/vault/<CODE>/` | data | Vault: thư mục markdown, mỗi note là một section. Nguồn sự thật sau Phase 1. Mọi improve sửa ở đây. Obsidian chỉ là **một trình xem tuỳ chọn**, không phải thành phần của pipeline |
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
- **Link (Q5, đã chốt: markdown chuẩn):** `[Tiêu đề](WRN-0342.md)`, hoặc `[…](WRN-0342.md#heading-con-slug)`. Không dùng wikilink `[[…]]`: VS Code, GitLab và mọi renderer đều hiểu link markdown, và export gần như không phải chuyển đổi.
  - **`sg build-vault` KHÔNG viết lại link** (quyết định T2-lite). Link trong note giữ **nguyên văn như trong source** (`#slug`, `#_Ref…`), kèm `_anchors.yaml` ánh xạ `anchor → ID` do build sinh ra.
  - Việc đổi link sang dạng trỏ tới note là bước riêng **`sg relink`**, chạy sau khi vault đã được kiểm chứng. Lý do: tách rủi ro "link resolve sai đích" ra khỏi bước build, và giữ round-trip của `sg export` gần như hiển nhiên.
  - Link không resolve được: **giữ nguyên link gốc**, gắn `#broken-ref`. **Không bao giờ đoán đích.**
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
4. Chạy `sg validate` sau mỗi lần sửa: phải 0 error.
5. Trước khi sửa, đọc:
   - `knowledge/style-guide.md`
   - `data/knowledge/glossary.md`
   - `data/knowledge/lessons.md` (lessons được ưu tiên hơn style guide khi mâu thuẫn)

## Lệnh

Chạy từ gốc repo:

```bash
uv run --project tools sg init-data [--migrate-legacy]              # tạo data/ (git repo riêng)
uv run --project tools sg specs                                     # kiểm tra registry và file nguồn
uv run --project tools sg profile --out data/reports/profile.txt    # Phase 0
uv run --project tools sg profile --diagnose                         # giải thích anchor chưa resolve (không lộ chữ)
uv run --project tools sg new-id WRN [-n 3]                         # cấp ID mới
uv run --project tools sg build-vault [CODE…] [--dry-run|--force]   # T2: sources → vault (445 note)
uv run --project tools sg export [CODE…] --check                    # T5: vault → build/export/, so round-trip với source
uv run --project tools sg validate [CODE…] [--fix-refs]             # T4: kiểm V01–V10, exit 1 nếu có error
uv run --project tools sg get WRN-0342 [--no-frontmatter|--json]    # T3: nội dung section + file:dòng + breadcrumb
uv run --project tools sg related WRN-0342 [--depth N|--json]       # T3: section link tới / được link từ
uv run --project tools sg find "<term>" [--spec NAME] [--kind heading|table|text] [--json]  # thuật ngữ nằm ở section nào (tham chiếu chéo spec chỉ là chữ)
uv run --project tools sg specs --lookup "LIN COMM"                 # tên (code/title/alias) → spec; exit 1 nếu chưa đăng ký
uv run --project tools --group dev pytest tools/tests               # test tools
```

Lệnh `relink` (T2b) đã có chỗ trong CLI nhưng chưa implement, làm sau Gate B. 
**Ngưỡng tách note (D1, đã chốt): 3000 token** cho cả ba spec → 445 note, p90 ≈ 2.2k token.

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

**Repo code:**
- `main` luôn là bản đã duyệt.
- Mỗi ticket là một branch `phase1/<ticket>-<mô-tả>`, merge vào `main` sau khi review.

**Repo `data/`:**
- `main` luôn là bản đã được expert duyệt.
- Mỗi lần improve là một branch `improve/<ID>-<mô-tả>`.
- Tag `baseline-original` được gắn ngay sau lần build vault đầu tiên được duyệt. Đây là bản "before", không được viết lại. Sau tag này **không bao giờ chạy lại `build-vault`**; mọi cải thiện link là `sg relink` tại chỗ và phải áp lên cả baseline (tag mới, ví dụ `baseline-relinked-1`).
