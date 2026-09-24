# Guide: `sg export`

| | |
|---|---|
| **Task** | T5 ([tasks](../tasks.md)) |
| **Trạng thái** | ✅ Đã implement (branch `phase1/t5-export`) |
| **Code** | `tools/specgarage/export.py` |
| **Test** | `tools/tests/test_export.py` (dùng fixture `DMD` của T2) |

## Tính năng làm gì

Ghép vault của một spec trở lại thành **một file markdown**: `build/export/<CODE>.md`. Kèm `--check` để **chứng minh round-trip**: file export phải giống hệt file nguồn. Đây là điều kiện tuyệt đối của Gate B (`handoff.md` §6).

Build (T2-lite) chỉ làm hai thay đổi đảo ngược được, nên export chỉ cần đảo lại hai thứ đó rồi nối các note theo thứ tự của `_manifest.yaml`:

| Build đã làm | Export làm |
|---|---|
| Chèn `<!-- id: … -->` dưới mỗi heading con | Bỏ các dòng đó (`--keep-ids` để giữ lại) |
| Đổi đường dẫn ảnh thành `../attachments/<CODE>/<file>` | Trả về **đúng đường dẫn như trong source**, ví dụ `images/media/image12.png` |

Link và anchor không phải xử lý gì, vì build giữ nguyên văn.

## Cách dùng

```bash
uv run --project tools sg export                 # mọi spec đã có vault
uv run --project tools sg export WRN --check     # export và so với source
uv run --project tools sg export --check --out-dir /tmp/exp
```

Output:

```
WRN: 247 notes, 25,468 lines -> …/build/export/WRN.md
  round-trip OK WRN: identical to the source, ignoring blank lines
```

Nếu khác, lệnh báo tối đa 10 dòng lệch đầu tiên và **thoát với mã 1**:

```
  round-trip FAILED DMD:
    non-blank line 42: export 'Changed overview…' != source 'Text for the first overview…'
```

| Tuỳ chọn | Tác dụng |
|---|---|
| `CODE…` | Spec cần export. Mặc định là mọi spec đã có `data/vault/<CODE>/_manifest.yaml` |
| `--check` | So với source. Không dùng chung với `--keep-ids` được |
| `--keep-ids` | Giữ các dòng `<!-- id: … -->` |
| `--out-dir` | Thư mục ghi ra, mặc định `build/export/` (bị `.gitignore`) |

**Cảnh báo có thể gặp:**
- `source … not found`: không tìm thấy source nên không trả được đường dẫn ảnh gốc, ảnh giữ đường dẫn `attachments/`.
- `source changed since the vault was built (sha256 differs)`: source đã bị sửa sau khi build. `--check` gần như chắc chắn sẽ báo lệch.
- `no source path for image …`: ảnh có trong vault nhưng không có trong source.

## Round-trip "chính xác" nghĩa là gì

So **từng dòng không rỗng**, bỏ khoảng trắng cuối dòng. Dòng trống không được so vì build bỏ các dòng trống ở cuối mỗi note, và export nối các note bằng một dòng trống. Ngoài dòng trống ra, mọi ký tự đều phải khớp, kể cả đường dẫn ảnh.

Test trong repo kiểm điều này với 4 ngưỡng tách (1, 20, 100, 10⁶ token), tức là từ "mỗi heading một note" tới "mỗi chương một note".

## Quy tắc

- **Chạy `sg export --check` ngay sau `sg build-vault`**, trước khi expert xem (Gate B / V1). Có lệch là dừng lại, không gắn baseline.
- **Sau khi improve, `--check` sẽ lệch.** Điều đó là đúng, vì vault đã khác source. Lúc đó `--check` không còn ý nghĩa; export chỉ dùng để xuất bản spec đã cải thiện.
- File export nằm trong `build/`, không commit.

## Giới hạn đã biết

- **Chưa hỗ trợ vault đã relink (T2b).** Khi có T2b, export phải đổi `[text](<ID>.md…)` ngược về `[text](#<anchor>)`. Hiện tại link được xuất nguyên như trong vault.
- **Dòng trống không được khôi phục chính xác** (xem trên). Về nội dung markdown thì không ảnh hưởng.
- **Một dòng trong source trùng đúng dạng `<!-- id: XXX-0000 … -->`** sẽ bị export coi là comment ID và bỏ đi. `--check` sẽ phát hiện.
- **Ảnh có tên chứa khoảng trắng** không được trả về đường dẫn gốc (build đổi thành đường dẫn có khoảng trắng mà không bọc `<…>`). Converter hiện chỉ sinh `imageN.png` nên không gặp.

## Cách test

```bash
uv run --project tools --group dev pytest tools/tests/test_export.py
```

Các trường hợp được test:
- round-trip ở 4 ngưỡng tách;
- `--check` pass, và bắt được note bị sửa;
- `--keep-ids`;
- thiếu source, source bị đổi, thiếu note, chưa có vault;
- trả đường dẫn ảnh cho cả `![…](…)` và `<img src>`;
- CLI (mã thoát 0 và 1).
