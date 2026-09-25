# Guide: thêm spec mới (`sg add-spec`) và registry `data/specs.yaml`

| | |
|---|---|
| **Task** | T9 ([tasks](../tasks.md)) |
| **Trạng thái** | ✅ Đã implement |
| **Code** | `tools/specgarage/add_spec.py`, `config.py` (registry), `build_vault.py` (`baseline_of`), `init_data.py` (migrate registry) |
| **Test** | `tools/tests/test_add_spec.py`, `test_build_vault.py::test_baseline_freezes_only_the_specs_it_holds`, `test_init_data.py` |

## Tính năng làm gì

**Thêm một spec chỉ đụng tới repo `data/`, không sửa gì trong `spec-garage`.**

Có ba thay đổi đi cùng nhau:

1. **Registry nằm trong `data/specs.yaml`**, không còn ở gốc repo code.
   - Registry mô tả dữ liệu (tên file, doc_no, ngày, alias), và đổi khi dữ liệu đổi.
   - Vì vậy một commit trong `data/` chứa trọn registry, source và vault, và tag baseline ghim được cả ba.
   - Đường dẫn trong registry **tương đối với `data/`**: `sources/<CODE>/…`.
2. **`sg add-spec`** đưa output của converter vào đúng chỗ và đăng ký nó:
   - chuyển thư mục vào `data/sources/<CODE>/`;
   - đọc `doc_no`, `lang`, `title`, `date` từ tên file;
   - thêm entry vào registry;
   - với `--build`: chạy luôn `build-vault`, `export --check` và `validate`.
3. **Baseline theo từng spec.**
   - Spec có từ đầu nằm trong tag chung `baseline-original`.
   - Mỗi spec thêm sau có tag riêng `baseline-original-<CODE>`.
   - `build-vault` chỉ chặn spec **đã có vault trong một tag baseline**, nên build được spec mới trong khi spec cũ vẫn đóng băng.

Ngoài ra:
- `sg specs` in trạng thái sống của từng spec: số note trong vault và tag baseline. Tài liệu vì thế không cần chép số liệu từng spec.
- So khớp tên spec bỏ qua cả dấu `/`, nên `ADAS/AD` và `ADAS AD` là một.

## Cách dùng

### Thêm spec

Converter sinh ra một thư mục `<tên>.out/` gồm một file `.md` và `images/`. Thả nó vào `data/sources/` (hoặc để ở đâu cũng được), rồi:

```bash
uv run --project tools sg add-spec "data/sources/7821ZXXXXJ000_E_(ADAS AD)_260220.out" --code ADAS --dry-run
uv run --project tools sg add-spec "data/sources/7821ZXXXXJ000_E_(ADAS AD)_260220.out" --code ADAS --build
```

Output (có `--build`):

```
ADAS: ADAS AD (doc_no 7821ZXXXXJ000, lang E, date 2026-02-20)
  move …/data/sources/7821ZXXXXJ000_E_(ADAS AD)_260220.out -> …/data/sources/ADAS
  register in data/specs.yaml: source sources/ADAS/7821ZXXXXJ000_E_(ADAS AD)_260220.md, images sources/ADAS/images
registered ADAS. next: sg build-vault ADAS, or run add-spec with --build
ADAS: 300 notes, 1097 headings, 2683 anchors, 345 images, largest note ~7,292 tokens
vault written to …/data/vault
next: sg export ADAS --check, sg validate ADAS, commit in data/, then git -C data tag -a baseline-original-ADAS -m "Before state of the ADAS vault"
ADAS: 300 notes, 22,075 lines -> …/build/export/ADAS.md
  round-trip OK ADAS: identical to the source, ignoring blank lines
ADAS: 300 notes checked
summary: 0 error(s), 0 warning(s)
```

Sau đó, trong repo `data/`, trên một branch riêng từ `main`:

```bash
git -C data switch -c ingest/ADAS-baseline main
git -C data add specs.yaml sources/ADAS vault/ADAS vault/attachments/ADAS
git -C data commit -m "Baseline vault for ADAS AD: …"
git -C data tag -a baseline-original-ADAS -m "Before state of the ADAS AD vault: never rewrite"
```

Expert xem khoảng 10 note (Gate B), rồi merge vào `main` của `data/`.

| Tuỳ chọn | Tác dụng |
|---|---|
| `--code` | **Bắt buộc.** 2–5 chữ in hoa, là tiền tố vĩnh viễn của mọi Section ID. Chọn tên dễ nhận ra từ title, ví dụ `ADAS` cho "ADAS AD" |
| `--alias NAME` | Tên khác mà spec khác dùng để gọi spec này. Lặp lại được. Không cần cho khác biệt về hoa/thường, khoảng trắng, dấu chấm, `/` và dấu nháy |
| `--title`, `--doc-no`, `--date` | Ghi đè giá trị lấy từ tên file. Bắt buộc khi tên file không theo mẫu `<doc_no>_<lang>_(<title>)_<yymmdd>.md` |
| `--build` | Chạy tiếp `build-vault`, `export --check`, `validate`; exit 1 nếu một bước lỗi |
| `--max-tokens N` | Ngưỡng tách cho `--build` (mặc định 3000, D1) |
| `--dry-run` | Chỉ in kế hoạch, không di chuyển hay ghi gì |

### Xem trạng thái

```bash
uv run --project tools sg specs
```

```
WRN   7820ZXXXXG000   2026-02-20 source:ok  images:ok  notes:247  baseline:baseline-original       Warning
ADAS  7821ZXXXXJ000   2026-02-20 source:ok  images:ok  notes:300  baseline:baseline-original-ADAS  ADAS AD
```

### Chuyển registry cũ (một lần, trên máy đã có `specs.yaml` ở gốc)

```bash
uv run --project tools sg init-data --migrate-legacy
# moved: specs.yaml -> data/specs.yaml (paths now relative to data/)
```

Chuyển từng dòng, bỏ tiền tố `data/` ở `source:`/`images:`, nên comment trong file được giữ nguyên. Khi `specs.yaml` còn ở gốc, mọi lệnh `sg` dừng với lời nhắc chạy lệnh trên, để không bao giờ lặng lẽ đọc một registry rỗng.

## Quy tắc cho agent và người dùng

- **Mã spec là vĩnh viễn.** `add-spec` từ chối mã đã có. Chọn mã một lần, trước khi build.
- **Revision mới của spec đã đăng ký** (cùng `doc_no`) **không** dùng `add-spec`: lệnh từ chối vì vault cần được merge chứ không phải một mã mới. Việc này chưa có công cụ.
- `add-spec` từ chối khi title hoặc alias đã trỏ tới spec khác, để `sg find --spec` và `sg specs --lookup` luôn trả lời một nghĩa.
- **Nguồn trong `data/sources/` thì được chuyển (move), nguồn ở chỗ khác thì được chép (copy).** Nhờ vậy không có hai bản ảnh trong `data/`, còn file ngoài `data/` không bị động tới.
- Truyền **thư mục** nếu `.md` có ảnh. Truyền riêng file `.md` có link ảnh sẽ bị từ chối, vì ảnh không đi theo.
- **Không chạy lại `build-vault` cho spec đã có baseline.** `--i-know-baseline-exists` chỉ dùng khi cố ý bỏ baseline của chính spec đó.
- Sửa `data/specs.yaml` bằng tay vẫn được (alias, `images`). Entry mới thì nên qua `add-spec`.

## Giới hạn đã biết

- Không xử lý revision mới của một spec đã có (xem trên).
- Không tự gợi ý mã spec: người chọn, vì mã không đổi được.
- Không tự commit hay gắn tag trong `data/`. Lệnh chỉ in lệnh git gợi ý, vì commit và tag là quyết định review của người.
- Không tự dò alias. Muốn biết spec khác gọi spec mới là gì, tìm `refer to SPEC` trong các source: `sg find "SPEC" --kind text`.

## Cách test

```bash
uv run --project tools --group dev pytest tools/tests/test_add_spec.py tools/tests/test_init_data.py tools/tests/test_build_vault.py
```

Các trường hợp được test (fixture `DMD` giả lập, tên file đúng mẫu converter):
- thư mục `.out` trong `data/sources/` được move, ngoài `data/` được copy;
- entry đọc lại đúng, comment trong registry còn nguyên, `specs: []` được mở rộng;
- `.md` không có ảnh; tên file lệch mẫu cần `--title/--doc-no/--date`;
- từ chối: mã sai định dạng, mã đã có, cùng `doc_no`, title/alias trùng, `.md` có ảnh nhưng truyền riêng, thư mục có nhiều `.md`;
- `--dry-run` không đổi gì; `--build` chạy đủ ba bước; `sg specs` in số note và tag baseline;
- tag `baseline-original` và `baseline-original-<CODE>` chỉ khoá spec có vault trong tag đó;
- migrate `specs.yaml` từ gốc vào `data/`, và báo lỗi thay vì đọc registry rỗng khi chưa migrate.
