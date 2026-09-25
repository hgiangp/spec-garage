# Guide: skill `spec-trace`, `sg find` và alias trong registry

| | |
|---|---|
| **Task** | S6a ([tasks](../tasks.md)) |
| **Trạng thái** | ✅ Bản đầu (branch `phase2/s6-spec-trace`), đã chạy eval vòng 1 |
| **Code** | `.claude/skills/spec-trace/` (SKILL.md + `references/`), `tools/specgarage/find.py`, `tools/specgarage/config.py` (`aliases`, `lookup_spec`) |
| **Test** | `tools/tests/test_find.py` (fixture `DMD`). Eval của skill: `data/evals/skills/spec-trace/` (repo dữ liệu) |

## Tính năng làm gì

**`spec-trace`** là skill chỉ đọc. Nó lần **mọi tham chiếu** trong một section tới chỗ định nghĩa gốc rồi ghi một *reference map* vào `data/reports/trace/<ID>.md` (tiếng Anh). Các skill `spec-analyze`, `spec-consistency`, `spec-restructure` dùng map này làm ngữ cảnh trước khi phân tích hoặc sửa.

Skill phân loại tham chiếu như sau:

| Loại | Ví dụ | Cách lần |
|---|---|---|
| `anchor` | `[XX-S01](#xx-s01)` | `sg related <ID>` → `sg get` đích |
| `ref-data` (**Rule 1**) | `XXX operation (Reference data Input)` | Bảng Reference data trong mục Input của chính spec → cột Source Function → `sg specs --lookup` → `sg find` trong spec đích |
| `spec-text` (**Rule 2**) | `refer to SPEC "LIN COMM"` | Đã biết module → `sg specs --lookup` → `sg find` → đọc |
| `section-text` | `refer to 3.2`, `Table 1-3` | `sg find "3.2." --kind heading` |
| `bare-name` | `P99`, `XX_STATE` | Tìm trong spec hiện tại trước, rồi các spec khác |
| `external` | `refer to DWG` | Không lần, chỉ ghi lại |

Mỗi dòng trong map có **bản chất** của thuật ngữ (theo lời spec đích) và **trạng thái**: `resolved`, `resolved-fuzzy`, `ambiguous`, `not-found`, `unregistered-spec`, `broken-link`, `external`. Cột bản chất là thứ làm lộ ra những lỗi kiểu "lúc là operation, lúc là signal".

**Độ sâu mặc định: 1 bước sang spec khác.** Những gì định nghĩa ở spec đích tham chiếu tiếp (parameter, mục khác) được ghi ở mục "Not followed". Nếu thấy chưa đủ thì cải tiến sau.

### Công cụ đi kèm

- **`sg find "<term>"`**: tìm thuật ngữ trong vault, trả về **section nhỏ nhất** chứa nó, loại hit (`heading` / `table` / `text`), `file:dòng`, breadcrumb và trích đoạn.
  - Mặc định khớp **nguyên từ** và không phân biệt hoa thường, nên `FOO operation` không khớp `XFOO operation`.
  - `_` là một phần của tên, nên `R_FOO` **không** khớp `R_FOO_UP`: đó là hai signal khác nhau. Khi tìm nguyên từ mà không có hit nào, lệnh ghi ra stderr các tên dài hơn có chứa thuật ngữ, để phân biệt "không có" với "chỉ có trong tên dài hơn":
    ```
    no whole-word match; --substring finds it inside: R_FOO_UP (3), R_FOO_DOWN (3), R_FOO_PUSH (1)
    0 hit(s) in 0 section(s)
    ```
    Exit code vẫn là 1 và stdout của `--json` vẫn là JSON hợp lệ (`[]`). Liệt kê tối đa 5 tên, số trong ngoặc là số lần xuất hiện.
  - Gạch nối thường khớp cả non-breaking hyphen của Word (`Table 1‑3`).
  - Số mục `3.2.` không khớp `1.3.2.`.
  - Mặc định bỏ qua preamble (mục lục).
- **`sg specs --lookup "<tên>"`**: tên (code, title hoặc alias) ứng với spec nào trong registry. Exit 1 nếu chưa đăng ký.
- **`aliases:` trong `specs.yaml`**: các tên khác mà spec khác dùng để gọi spec này, ví dụ trong cột Source Function. Khi so sánh, hoa/thường, khoảng trắng, dấu chấm và dấu nháy đều được bỏ qua. Hiện cả ba spec đều để `aliases: []`, vì title đã khớp cách các spec gọi nhau (`LIN COMM`, `EnlargeWA`, `Warning`). Chỉ thêm alias khi expert xác nhận.

## Cách dùng

Trong Claude Code, ở gốc repo:

```
/spec-trace EWA-0057
```

hoặc hỏi tự nhiên, ví dụ "các input của EWA-0057 lấy từ đâu?". Skill tự kích hoạt theo description.

Dùng lệnh trực tiếp:

```bash
uv run --project tools sg find "FOO_REQ"
uv run --project tools sg find "FOO_REQ" --spec "LIN COMM" --kind heading
uv run --project tools sg find "Reference data" --spec EWA --kind heading
uv run --project tools sg find "3.2." --spec EWA --kind heading
uv run --project tools sg find "FOO" --substring --json
uv run --project tools sg specs --lookup "LIN COMM"      # LIN  LIN COMM  data/sources/LIN/…
uv run --project tools sg specs --lookup "Unknown Module"  # exit 1: not in specs.yaml
```

Output `find` (fixture giả lập):

```
DMD-0003 (in DMD-0001)  text     data/vault/DMD/DMD-0001.md:55  1. Demo Function > 1.1. Overview > 1.1.1. Sub Behaviour
    The demo lamp shall stay on for 200 ms.
1 hit(s) in 1 section(s)
```

| Tuỳ chọn | Tác dụng |
|---|---|
| `--spec NAME` | Chỉ tìm trong spec này (code, title hoặc alias). Dùng lặp lại được. Mặc định: mọi spec đã có vault |
| `--kind heading\|table\|text` | Lọc theo loại hit. Dùng lặp lại được |
| `--substring` | Khớp cả bên trong từ |
| `--case-sensitive` | Phân biệt hoa thường |
| `--include-preamble` | Tìm cả trong mục lục |
| `--limit N` / `--all` | Số hit in ra (mặc định 30) |
| `--json` | `[{id, note, spec, path, line, kind, breadcrumb, snippet, matches}]`. `matches` là đoạn chữ khớp trên dòng, giữ nguyên cách viết (hữu ích với `--substring`) |

Hit được sắp theo thứ tự `heading` → `table` → `text`, vì chỗ định nghĩa thường là heading.

## Quy tắc

**Cho agent:**
- Chỉ đọc. Không sửa vault và `specs.yaml`. Nếu cần thêm alias hoặc spec mới, ghi vào câu hỏi cho expert.
- Không suy nghĩa theo tên. Một dòng chỉ được ghi `resolved` khi đã thực sự `sg get` section đích.
- `sg find` trả 0 hit thì đọc stderr trước khi ghi `not-found`. Tên dài hơn được gợi ý (ví dụ `R_FOO_UP` khi tìm `R_FOO`) là **tên khác**, chỉ là biến thể: tối đa là `resolved-fuzzy`, kèm câu hỏi cho expert.
- Một spec có thể chứa **nhiều khối chức năng**, mỗi khối có mục Input riêng. Phải dùng đúng bảng Reference data của khối chứa section đang lần.
- Không đưa nội dung spec ra dịch vụ ngoài.

**Cho expert và người dùng:**
- Đọc mục "Missing specs" và "Questions for the expert" trong report. Khi trả lời:
  - thêm alias vào `specs.yaml` (repo code), hoặc
  - thêm spec mới vào registry, hoặc
  - ghi rule mới vào `data/knowledge/lessons.md` (ví dụ quy ước đặt tên giữa hai spec).
- Skill **không bao giờ tự thêm alias**.

## Giới hạn đã biết

- **Độ sâu 1 bước** cross-spec. Chuỗi nhiều bước (ví dụ operation → signal thô → frame LIN) cần yêu cầu rõ.
- **Nhiều spec nguồn chưa có trong registry.** Bảng Reference data hiện nhắc tới khoảng 6–7 module chưa có spec. Thuật ngữ đến từ các module này dừng ở trạng thái `unregistered-spec`. Danh sách cụ thể nằm trong report ở `data/reports/trace/`.
- **`sg find` là tìm theo chữ.** Tên bị viết khác nhau giữa hai spec (ví dụ `L_FOO_UP` và `FOO UP`) chỉ khớp được qua biến thể mà skill thử có kiểm soát, với trạng thái `resolved-fuzzy`, và luôn phải được expert xác nhận.
- **Phân loại `table`** dựa trên dòng bắt đầu bằng `|` hoặc nằm trong `<table>…</table>`. Caption bảng được tính là `text`.
- **Mỗi lần gọi `sg find`, vault được đọc lại** (giống `get`/`related`).

## Cách test

```bash
uv run --project tools --group dev pytest tools/tests/test_find.py
```

Các trường hợp được test:
- chuẩn hoá tên spec và `lookup_spec` theo code, title, alias;
- khớp nguyên từ, khớp tên bị xuống dòng, số mục, non-breaking hyphen;
- hit map về section nhỏ nhất, đúng loại, đúng số dòng trong file;
- sắp heading trước, bỏ preamble, không khớp dòng `<!-- id -->`;
- `_` là một phần của tên (`R_DEMO` không khớp `R_DEMO_UP`), gợi ý tên dài hơn khi 0 hit (tôn trọng `--kind`, `--case-sensitive`), gợi ý ra stderr, không đổi exit code và JSON;
- lọc theo spec, báo lỗi với spec chưa đăng ký, CLI và `--json`.

**Eval skill** (repo dữ liệu, theo quy trình skill-creator):
- `data/evals/skills/spec-trace/evals/evals.json`: các prompt và assertion;
- `data/evals/skills/spec-trace/workspace/iteration-N/`: output có skill và baseline không có skill, `grading.json`, `benchmark.json`.

Ba case vòng 1 kiểm ba nhánh:
- bản chất của các reference data (Rule 1);
- SPEC dạng chữ, hình, bảng, tài liệu ngoài (Rule 2, `section-text`, `external`);
- spec chưa đăng ký.

Nội dung cụ thể của các case nằm trong repo dữ liệu.
