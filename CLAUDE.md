# Spec Garage

Repo để ingest và improve spec automotive (Word → Markdown + ảnh). Thiết kế và các quyết định (D1–D13): `docs/spec-pipeline-design.md`.

**Giai đoạn hiện tại:** Phase 0 (profile dữ liệu) → Phase 1 (vault) → Phase 2 (skills improve). RAG/chatbot để sau.

## Chính sách dữ liệu

- Spec là tài liệu mật. Claude Code được phép đọc và sửa spec trong repo này.
- **Không** đưa nội dung spec vào dịch vụ bên ngoài khác (web search, WebFetch, API bên thứ ba, artifact công khai).

## Cấu trúc

| Thư mục | Vai trò | Quy tắc |
|---|---|---|
| `sources/<CODE>/` | Spec gốc Word→md + ảnh | **Chỉ đọc.** Không sửa tay |
| `vault/<CODE>/` | Obsidian vault, mỗi note là một section. Nguồn sự thật sau Phase 1 | Mọi improve sửa ở đây |
| `vault/<CODE>/_manifest.yaml` | Cây section, thứ tự, `next_id`, `retired` | Chỉ sửa qua `sg` hoặc khi đổi cấu trúc có chủ đích |
| `knowledge/` | Tri thức domain dùng chung cho mọi skill | Expert duyệt trước khi thêm rule |
| `.claude/skills/` | Skill improve (chỉ chứa quy trình) | Nội dung domain đưa vào `knowledge/` |
| `tools/` | CLI `sg` | Mọi thao tác máy móc đi qua đây |
| `evals/`, `reports/` | Eval skill / câu hỏi vàng; output của analyze và validate | |
| `specs.yaml` | Registry: mã spec ↔ file nguồn | |

## Quy ước (D2, D3)

- **Section ID:** `<CODE>-<NNNN>`, ví dụ `WRN-0342`.
  - Gán cho mọi heading H1–H6.
  - ID mới luôn bằng `next_id` trong manifest.
  - Không bao giờ đổi hoặc dùng lại ID. ID không mang ý nghĩa: số heading nằm ở `legacy_number`.
- **Tên file note:** chỉ là ID, ví dụ `vault/WRN/WRN-0342.md`. Tiêu đề nằm trong `title` và `aliases`.
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
2. **Không đổi ngữ nghĩa** (giá trị, điều kiện, thứ tự hành vi) nếu chưa được expert xác nhận. Mọi thay đổi đi qua PR.
3. **Giữ nguyên ID, anchors, legacy_number.** Không xoá comment `<!-- id: … -->`.
4. Chạy `sg validate` sau mỗi lần sửa (khi đã implement).
5. Đọc `knowledge/style-guide.md`, `knowledge/glossary.md` và `knowledge/lessons.md` trước khi sửa.

## Lệnh

Chạy từ gốc repo:

```bash
uv run --project tools sg specs                    # kiểm tra registry và file nguồn
uv run --project tools sg profile --out reports/profile.txt   # Phase 0
uv run --project tools --group dev pytest tools/tests          # test tools
```

Các lệnh `build-vault`, `get`, `related`, `validate`, `export` đã có chỗ trong CLI nhưng chưa implement (Phase 1).

## Git

- `main` luôn là bản đã duyệt.
- Mỗi lần improve là một branch `improve/<ID>-<mô-tả>` và một PR.
- Tag `baseline-original` được gắn ngay sau lần build vault đầu tiên. Đây là bản "before", không được viết lại.
