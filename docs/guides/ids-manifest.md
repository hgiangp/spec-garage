# Guide: Section ID, manifest và `sg new-id`

| | |
|---|---|
| **Task** | T1, T6 ([tasks](../tasks.md)) |
| **Trạng thái** | ✅ Đã implement (`8095e35`, branch `phase1/t1-ids-manifest`) |
| **Code** | `tools/specgarage/ids.py`, lệnh `new-id` trong `cli.py` |
| **Test** | `tools/tests/test_ids.py` |
| **Quyết định** | D2 (Section ID), D3 (manifest) trong [design doc](../spec-pipeline-design.md) |

## Tính năng làm gì

Mỗi heading (H1–H6) trong spec có một **Section ID ổn định**, dạng `<CODE>-<NNNN>`, ví dụ `WRN-0342`. ID này là "xương sống" cho:
- link giữa các note;
- truy vết khi improve (tách, gộp, xoá section);
- so sánh before/after ở giai đoạn sau.

`ids.py` quản lý **manifest** của từng spec (`data/vault/<CODE>/_manifest.yaml`):
- cây note theo thứ tự tài liệu (nguồn duy nhất cho thứ tự khi export);
- bộ đếm `next_id`;
- danh sách ID đã retire.

Module này **không** tạo note. Việc đó là của `build-vault` (T2). T2 và các skill dùng API của module này.

## Quy tắc ID (D2)

| Quy tắc | Chi tiết |
|---|---|
| Format | `<CODE>-<NNNN>`. `CODE` gồm 2–5 chữ in hoa, lấy từ `data/specs.yaml` |
| Độ rộng số | `id_width` trong manifest: 4 chữ số, hoặc 5 nếu spec có ≥ 10 000 heading. **Cố định cho cả spec.** Vượt quá thì báo lỗi, không tự đổi |
| Cấp phát | Luôn là `next_id`, tăng dần. Không chèn số vào giữa |
| Không mang ý nghĩa | Không mã hoá số heading hay cấp bậc. Số heading gốc nằm ở `legacy_number` |
| Không đổi, không dùng lại | ID đã retire không bao giờ được cấp lại |
| Preamble | Nội dung trước heading đầu tiên là `<CODE>-0000` (do T2 gán) |

## Định dạng manifest

```yaml
spec: WRN
source: data/sources/WRN/7820ZXXXXG000_E_(Warning)_260220.md
source_sha256: …
built_with: specgarage 0.1.0
max_tokens: 3000
id_width: 4
next_id: 1289
tree:                        # chỉ gồm note; heading con trong note không nằm ở đây
  - WRN-0000
  - WRN-0001:                # note có note con
      - WRN-0002
      - WRN-0339:
          - WRN-0340
  - WRN-0400
retired:
  - {id: WRN-0343, merged_into: WRN-0342}
  - {id: WRN-0350, reason: "duplicates WRN-0120"}
```

Khi đọc manifest, các lỗi sau bị từ chối: ID trùng trong tree, ID chưa được cấp (≥ `next_id`), ID đã retire mà vẫn còn trong tree, ID thuộc spec khác, sai độ rộng.

## `sg new-id`

Cấp ID mới và **ghi ngay** `next_id` vào manifest.

```bash
uv run --project tools sg new-id WRN          # → WRN-1289
uv run --project tools sg new-id WRN -n 3     # → WRN-1290, WRN-1291, WRN-1292
```

- Exit code `1` kèm thông báo lỗi (ví dụ `No manifest at …. Run \`sg build-vault\` first.`) nếu chưa có manifest (chưa chạy `build-vault`) hoặc ID vượt quá độ rộng.
- **Dùng khi:** skill hoặc người thêm heading mới (tách section, thêm mục mới). **Không bao giờ tự đánh số.**

## API cho developer (T2, T4, skill script)

```python
from specgarage.ids import Manifest, load_manifest, save_manifest, manifest_path, width_for

m = Manifest(spec="WRN", id_width=width_for(heading_count))   # T2 tạo mới
m.allocate(3)                       # ["WRN-0001", "WRN-0002", "WRN-0003"], chỉ trong bộ nhớ
m.add("WRN-0003", parent="WRN-0001", after="WRN-0002")
m.walk()                            # (node, parent_id, depth) theo thứ tự tài liệu
m.ids(); m.find(id); m.parent_of(id)
m.remove(id)                        # chỉ note lá
m.retire(id, merged_into=None, reason="…")   # cần một trong hai; tự gỡ khỏi tree
m.check_id(id)                      # kiểm tra format, spec, độ rộng, đã cấp

path = manifest_path(root, "WRN")
save_manifest(m, path)              # ghi atomic, thứ tự khoá cố định (diff dễ đọc)
m = load_manifest(path)
```

Lỗi được báo bằng `IdError`, với thông báo tiếng Anh nói rõ ID nào và vì sao, ví dụ `WRN-0099 has not been allocated (next_id = 8)`.

## Quy tắc cho agent và người dùng

- **Không sửa tay `_manifest.yaml`**, trừ khi đổi cấu trúc có chủ đích. Trường hợp đó phải chạy `sg validate` sau khi sửa (khi T4 xong).
- Tách section: phần mới lấy ID bằng `sg new-id`, ghi `derived_from: [<ID cũ>]` trong frontmatter.
- Gộp section: `retire(<ID bị gộp>, merged_into=<ID giữ lại>)`.
- Xoá section: `retire(<ID>, reason="…")`.
- ID của heading con (H4–H6 bên trong một note) cũng lấy từ `next_id`, nhưng không nằm trong `tree`.

## Giới hạn đã biết

- **Không có khoá khi ghi.** Hai tiến trình cùng chạy `new-id` trên cùng một spec có thể cấp trùng ID. Chỉ chạy tuần tự. `sg validate` (V02) sẽ phát hiện ID trùng.
- **Chưa có lệnh CLI** cho `add`, `remove`, `retire`. Hiện chỉ gọi được qua API. Sẽ bổ sung khi skill cần (Phase 2).

## Test

```bash
uv run --project tools --group dev pytest tools/tests/test_ids.py
```

Có test cho: format/parse, cấp phát tuần tự và tràn độ rộng, thứ tự duyệt cây, `add` (vị trí, trùng, đã retire, chưa cấp, khác spec), `remove` và `retire`, từ chối manifest không nhất quán, lưu/đọc round-trip, `sg new-id`.
