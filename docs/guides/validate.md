# Guide: `sg validate`

| | |
|---|---|
| **Task** | T4 ([tasks](../tasks.md)) |
| **Trạng thái** | ✅ Đã implement (branch `phase1/t4-validate`) |
| **Code** | `tools/specgarage/validate.py` |
| **Test** | `tools/tests/test_validate.py` (dùng fixture `DMD` của T2) |

## Tính năng làm gì

Kiểm tra vault theo các quy ước V01–V10 (`next-steps.md` §3 T4).
- **error:** vault chưa an toàn để gắn baseline hay improve. Lệnh thoát với mã 1.
- **warning:** nên xem nhưng không chặn.

Validate **chỉ đọc**. Ngoại lệ duy nhất là `--fix-refs`: lệnh này ghi lại `refs_out` trong frontmatter, và phần thân note không bị động tới.

Dùng ở ba chỗ:
- **Gate B / V1:** chạy ngay sau `build-vault` và `export --check`. Phải ra 0 error.
- **Sau mỗi lần improve:** guardrail D9 bước 4 trong `CLAUDE.md`.
- **Trong skill:** mọi skill có sửa note đều kết thúc bằng `sg validate`.

## Các rule

| Mã | Mức | Kiểm tra |
|---|---|---|
| V01 | error | Có frontmatter YAML hợp lệ; đủ các trường `id, spec, title, aliases, legacy_number, heading_path, level, anchors, refs_out, status, derived_from`; `id` trùng tên file; `spec` trùng thư mục |
| V02 | error | ID đúng format `<CODE>-<NNNN>`, thuộc đúng spec, không dùng hai lần (tính cả tên note lẫn dòng `<!-- id -->`) |
| V03 | error | Note và `tree` của manifest khớp hai chiều; mọi ID đã được cấp (< `next_id`, đúng `id_width`); ID đã retire không còn xuất hiện |
| V04 | error | Link `#anchor` phải có trong `_anchors.yaml`; link `<ID>.md#frag` (sau T2b) phải trỏ tới note có thật, và `#frag` phải là heading hoặc anchor trong note đó; mọi giá trị trong `_anchors.yaml` phải là ID có thật |
| V05 | error | Mỗi heading con (không phải heading gốc của note) có đúng một dòng `<!-- id: … -->` ngay dưới; dòng id không nằm lung tung; ID trong dòng id khớp với `notes` của `_anchors.yaml`; note (trừ preamble) phải có heading |
| V06 | error | Ảnh được tham chiếu tồn tại (đường dẫn tương đối so với note) |
| V07 | error | `status` ∈ `original, proposed, reviewed, approved`; `derived_from` là ID đã cấp; mục `retired` và `merged_into` hợp lệ |
| V08 | warning | Dòng có link gắn `#broken-ref`. Link đó không bị V04 báo lỗi nữa |
| V09 | warning | Bảng pipe có hàng khác số cột với header (bỏ qua `\|` escape và code span) |
| V10 | warning | `refs_out` khác với các note mà link trong note thực sự trỏ tới |

**Anchor thô (`<span id=…>`) được phép**, vì build giữ nguyên văn (T2-lite).

## Cách dùng

```bash
uv run --project tools sg validate                 # mọi spec đã có vault
uv run --project tools sg validate WRN --all       # in mọi finding, không cắt
uv run --project tools sg validate --json          # cho script / agent
uv run --project tools sg validate --fix-refs      # sửa V10
```

Output:

```
WRN: 247 notes checked
V09 warning     3  pipe table rows with a different column count than the header
    data/vault/WRN/WRN-0412.md:37  1 row(s) differ from the header's 4 columns
summary: 0 error(s), 3 warning(s)
```

| Tuỳ chọn | Tác dụng |
|---|---|
| `CODE…` | Spec cần kiểm tra. Mặc định là mọi spec đã có vault |
| `--limit N` | Số finding hiện cho mỗi rule (mặc định 10) |
| `--all` | Hiện hết |
| `--json` | `{notes, errors, warnings, fixed, findings: [{rule, level, path, line, message}]}` |
| `--fix-refs` | Ghi lại `refs_out` cho khớp link. Chỉ động vào frontmatter |

Số dòng trong finding là **số dòng trong file note**, tính cả frontmatter, nên mở file và nhảy thẳng tới dòng đó được.

## Quy tắc

- **Gate B yêu cầu 0 error.** Warning thì expert xem và quyết.
- **Không sửa tay để "cho qua" lỗi V02/V03/V05.** Đó thường là dấu hiệu note bị tách, gộp hoặc xoá sai quy ước (xem `CLAUDE.md` §Quy ước). ID mới chỉ lấy qua `sg new-id`.
- **Link không resolve được** sau T2b phải được gắn `#broken-ref` trên cùng dòng. Khi đó nó là V08 warning, không phải V04 error. **Không bao giờ đoán đích.**
- `--fix-refs` an toàn để chạy bất cứ lúc nào: `refs_out` là dữ liệu sinh ra, không ai sửa tay.

## Giới hạn đã biết

- **V04 chỉ kiểm link trong cùng spec**, và link `<ID>.md` / `../<CODE>/<ID>.md`. Link `.docx` hay link ngoài không được kiểm (converter không sinh ra).
- **Fragment `#frag` sau relink** được so với anchor tường minh và slug của heading **trong note đích**, theo kiểu pandoc và GitHub. Nếu T2b chọn cách sinh slug khác thì phải cập nhật V04 theo.
- **V05 dựa vào heading ATX.** Heading nằm trong bảng HTML sẽ không được nhận ra (build cũng không cho phép).
- **V09 chỉ kiểm bảng pipe**, không kiểm bảng HTML.

## Cách test

```bash
uv run --project tools --group dev pytest tools/tests/test_validate.py
```

- **Vault vừa build** (3 ngưỡng tách) phải ra 0 finding.
- **Mỗi rule V01–V10** có một test làm hỏng vault theo đúng kiểu đó rồi kiểm tra có bị bắt không.
- **`--fix-refs`** không đổi thân note.
- **CLI:** mã thoát 0 và 1, và `--json`.
