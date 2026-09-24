# Hướng dẫn triển khai các bước tiếp theo

> Dành cho người hoặc worker (AI agent) nhận làm các bước sau khung repo.
> Đọc trước: `CLAUDE.md` (quy ước, guardrail) và `docs/spec-pipeline-design.md` (lý do các quyết định D1–D13).
> Cập nhật: 2026-09-23
>
> **Trạng thái hiện tại** của từng task: [`tasks.md`](tasks.md). **Hướng dẫn sử dụng** tính năng đã xong: [`guides/`](guides/).

## Tổng quan

| Bước        | Nội dung                                                                         | Ai làm                   | Phụ thuộc                            |
| ------------- | --------------------------------------------------------------------------------- | ------------------------- | -------------------------------------- |
| **§0** | Mô hình hai máy, dựng `data/`, chuẩn bị môi trường                       | Chủ repo                 | —                                     |
| **§2** | Phase 0: profile spec thật, chốt ngưỡng tách và định dạng anchor         | Chủ repo + domain expert | §0                                    |
| **§3** | Phase 1: implement`sg build-vault / get / related / validate / export / new-id` | Worker (T1–T7)           | §2 (có thể bắt đầu T1 song song) |
| **§4** | Build vault từ spec thật, expert kiểm tra, gắn baseline                       | Chủ repo + expert        | §3                                    |
| **§5** | Phase 2: thí điểm skill improve trên một cụm section                        | Expert + agent            | §4                                    |

---

## §0. Trước khi bắt đầu (bắt buộc)

### 0.1 Mô hình hai repo (cập nhật 2026-09-23)

> **Đã đổi.** Trước đây repo code nằm public trên GitHub và máy dữ liệu chỉ được pull, code chuyển đi bằng `git bundle`. Nay **cả hai repo đều ở GitLab nội bộ**, một máy làm được cả hai việc, push trực tiếp. Mọi hướng dẫn về "máy phát triển / máy dữ liệu" và `git bundle` bên dưới chỉ còn giá trị lịch sử.

| Repo | Làm gì | Remote |
|---|---|---|
| **`spec-garage`** | Code `tools/`, skill, tài liệu | GitLab nội bộ `…/giangpth13/spec-garage.git` |
| **`data/`** | Spec gốc, vault, tri thức domain, report, eval | GitLab nội bộ `…/giangpth13/data.git` |

Vẫn giữ tách đôi vì: vòng đời review khác nhau, `data/` có ~370 file ảnh, baseline tag phải độc lập với lịch sử code.

- Repo code ignore `/data/` (và các vị trí cũ `/sources/`, `/vault/`, `/reports/`, `/evals/`). Không bao giờ `git add -f` các đường dẫn đó.
- Mọi thứ rút ra từ spec đều nằm trong `data/`: spec gốc, vault, **glossary và lessons**, report, eval.
- Nếu có git server nội bộ thì `data/` có thể push lên đó. **Không bao giờ push lên remote public.**
- Lý do không dùng một git repo thứ hai phủ lên các thư mục rải rác ở gốc: repo thứ hai vẫn phải đọc `.gitignore` của repo public, và không có cách tắt quy tắc đó. Gom mọi thứ vào `data/` thì hai repo tách bạch hoàn toàn.

### 0.1b Dựng `data/` trên máy dữ liệu

```bash
git pull
uv run --project tools sg init-data --migrate-legacy
```

Lệnh này:
- tạo `data/` từ `tools/specgarage/data_template/`, không ghi đè file đã có;
- tạo `data/sources/<CODE>/` cho từng spec trong registry;
- chạy `git init` trong `data/`;
- với `--migrate-legacy`: chuyển spec và report đã chép vào vị trí cũ (`sources/`, `reports/`…) sang `data/`.

Sau đó commit lần đầu trong repo dữ liệu:

```bash
cd data && git add -A && git commit -m "Initial specs"
```

### 0.2 Môi trường

```bash
# cần uv (https://docs.astral.sh/uv/)
uv run --project tools --group dev pytest tools/tests    # phải pass
uv run --project tools sg specs
```

### 0.3 Git

- **Repo public:** mỗi ticket là một branch `phase1/<ticket>-<mô-tả>` và một PR vào `main`.
- **Repo `data/`:** xem `data/README.md`. `main` luôn là bản đã duyệt, mỗi lần improve là một branch, tag `baseline-original` được gắn ở §4.
- Nếu trên máy dữ liệu lỡ sửa một file của repo public (ví dụ `specs.yaml`), `git pull` sẽ báo conflict. Gửi thay đổi đó cho máy phát triển để commit, rồi `git checkout -- <file>` trên máy dữ liệu.

---

## §1. Kết quả tự review khung repo

### Đã sửa trong lần review

| Vấn đề                                                       | Hậu quả nếu không sửa                                   | Đã sửa                                                   |
| --------------------------------------------------------------- | ------------------------------------------------------------ | ----------------------------------------------------------- |
| `clean_title` xoá mọi dấu `_`                            | Tiêu đề chứa tên signal như`IGN_ON` thành `IGNON` | Chỉ bỏ nhấn mạnh`_x_` đi theo cặp                   |
| Footnote`[^1]: …` bị coi là link reference                 | Đếm sai số link cross-file                                | Loại nhãn bắt đầu bằng`^`                           |
| Word có thể xuất link sang spec khác dạng`file:///C:/…` | Link cross-file bị xếp vào`other`                       | Nhận dạng`file:` là cross-file                         |
| `#######` (7 dấu `#`) bị coi là H6                       | Heading giả                                                 | Bắt buộc có khoảng trắng sau`#`, và tối đa 6 dấu |
| Code fence đóng sai khi lồng nhau (```` và ```)             | Heading trong code block bị đếm                           | So khớp ký tự và độ dài fence                        |
| Repo public, dữ liệu spec có thể bị commit nhầm           | Rò rỉ spec                                                 | Gom toàn bộ dữ liệu vào `data/` (bị ignore, là git repo local riêng), xem §0 |

### Hạn chế còn lại của parser (biết trước, chưa sửa)

- **Setext heading** (`Title` + dòng `===`) không được coi là heading, chỉ được đếm ở `setext_suspects`. Nếu profile cho thấy số này lớn thì cần bổ sung.
- **Anchor nằm trong body** (không nằm trên dòng heading) được gán về section chứa nó, nhưng không nằm trong `Heading.anchors`.
- **Không xử lý** comment HTML nhiều dòng, indented code block (4 dấu cách) và link nằm trong inline code.
- **Token là ước lượng** `ký tự / 4`. Đủ dùng để chọn ngưỡng, không dùng để tính chính xác context.
- **Nhận diện grid table là heuristic.**

Nếu Phase 0 cho thấy converter xuất định dạng khác với những gì parser nhận ra, **thêm fixture giả lập mô phỏng định dạng đó** vào `tools/tests/fixtures/` trước, rồi mới sửa parser. Không copy nội dung spec thật vào fixture.

---

## §2. Phase 0: profile spec thật

### 2.1 Chạy

1. Dựng `data/` theo §0.1b. Spec và folder ảnh nằm ở `data/sources/WRN/`, `data/sources/EWA/`, `data/sources/LIN/`, **giữ nguyên tên file**.
   - Nếu đã chép vào `sources/` (vị trí cũ) thì `--migrate-legacy` sẽ chuyển sang.
   - `images:` trong `specs.yaml` là tuỳ chọn: link ảnh được resolve tương đối so với file md. Không cần sửa `specs.yaml` trên máy dữ liệu.
2. Chạy:
   ```bash
   uv run --project tools sg specs          # source phải "ok"
   uv run --project tools sg profile --out data/reports/profile.txt
   uv run --project tools sg profile --json --out data/reports/profile.json
   ```
3. Nếu cần hỗ trợ đọc kết quả từ máy phát triển: `profile.txt` chỉ chứa số liệu thống kê, ID anchor và tên file, không có nội dung spec, nên có thể gửi đi.

### 2.2 Đọc kết quả và ra quyết định

| Chỉ số trong profile                                | Nếu thấy                                                  | Thì                                                                                                                         |
| ----------------------------------------------------- | ----------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `anchors defined` = 0 nhưng `links internal` > 0 | Parser không nhận ra định dạng anchor của converter   | Mở file, tìm cách một`_Ref…` được định nghĩa, tạo fixture giả lập, mở rộng `ATTR_ID_RE` / `HTML_ID_RE` |
| `internal_unresolved` cao (> ~5 %)                  | Anchor bị mất hoặc sai định dạng                      | Như trên. Nếu anchor thực sự mất thì đối chiếu với quy trình verify đã có                                     |
| `numbered` thấp so với tổng số heading          | Word auto-numbering bị mất khi convert                    | `legacy_number` phải **tính từ vị trí trong cây** thay vì đọc từ text. Ghi vào T2                         |
| `level jumps` > 0                                   | Heading nhảy cấp (H2 → H4)                               | Kiểm tra vài chỗ. Parser vẫn chạy được, nhưng báo cho expert                                                       |
| `setext?` cao                                       | Converter dùng heading setext                              | Bổ sung parser (§1)                                                                                                        |
| `images missing files` > 0                          | Sai đường dẫn ảnh                                      | Kiểm tra folder ảnh có nằm đúng vị trí tương đối so với file md trong `data/sources/<CODE>/` không                  |
| `cross-file … unknown_file`                        | Spec tham chiếu tới spec ngoài bộ 3                     | Danh sách ở cuối report. Quyết định thêm vào`specs.yaml` hay coi là tham chiếu ngoài                            |
| `split simulation`                                  | Số note, kích thước p50 / p90 / max theo từng ngưỡng | Chọn ngưỡng D1 (xem 2.3)                                                                                                  |

### 2.3 Chọn ngưỡng tách (D1)

- Chọn ngưỡng **nhỏ nhất** thoả cả hai điều kiện:
  - `over` gần 0: chỉ còn vài section lá quá lớn, không tách nhỏ hơn được.
  - `tiny` không quá lớn: note tiny là note chỉ có heading, xuất hiện khi section cha bị tách ra.
- Khởi điểm hợp lý: **3000**.
- Section lá vượt ngưỡng: ghi lại ID để expert xem có nên tách theo nội dung ở Phase 2 không.
- **Ghi quyết định** vào `docs/spec-pipeline-design.md` (D1: đánh dấu checkbox, ghi ngưỡng) và thêm `max_tokens:` cho từng spec trong `specs.yaml` nếu cần ngưỡng khác nhau.

### 2.4 Done khi

- [x] Profile chạy trên cả 3 spec, không có lỗi.
- [x] Định dạng anchor đã được parser nhận ra; `internal_unresolved` = **0** trên cả ba spec.
- [x] Đã chốt ngưỡng D1 (**3000**) và cách lấy `legacy_number` (đọc từ tiêu đề).
- [x] Đã có danh sách spec ngoài phạm vi: chỉ `7822ZXXXXA000`, được EWA nhắc 1 lần ở dạng chữ. Không thêm vào registry.

---

## §3. Phase 1: implement công cụ vault

Thứ tự đề xuất: **T1 → T2 → T5 → T4 → T3 → (Gate B, tag baseline) → T2b relink** (T1 và T6 đã xong), với T7 (test) đi kèm từng ticket.

### Định dạng dữ liệu (hợp đồng chung)

**Note** `data/vault/<CODE>/<CODE>-<NNNN>.md`:

```markdown
---
id: WRN-0342
spec: WRN
title: Buzzer Parameters
aliases: ["3.2.4 Buzzer Parameters"]
legacy_number: "3.2.4"
heading_path: ["3 Function Description", "3.2 Buzzer Control", "3.2.4 Buzzer Parameters"]
level: 3
anchors: [_Toc512340001, _Ref512345678]   # mọi anchor nằm trong note (heading + body)
refs_out: [WRN-0120, LIN-0033]            # sinh tự động
status: original
derived_from: []
---
### 3.2.4 Buzzer Parameters

Nội dung… xem [Buzzer Timing](#_Ref512340000).

<span id="_Ref512345678" class="anchor"></span>Table 3‑4 Buzzer parameters

#### 3.2.4.1 Timing constraints
<!-- id: WRN-0343 | legacy: 3.2.4.1 | anchors: _Ref512349999 -->

![](../attachments/WRN/image12.png)
```

Sau `sg relink` (T2b), dòng link trên thành `[Buzzer Timing](WRN-0120.md)`. Trước đó nó **y như trong source**. Anchor (`<span id>`, anchor trên dòng heading) luôn giữ nguyên văn.

Quy tắc:

- **Giữ nguyên cấp heading gốc** (không đưa về H1), để export chỉ cần nối các note lại.
- **Anchor giữ nguyên văn**, cả trên dòng heading lẫn trong body (`<span id=… class="anchor"></span>`). Anchor của converter vốn là thẻ rỗng, không hiển thị, nên đổi sang comment chỉ thêm rủi ro. Danh sách anchor của note nằm trong frontmatter `anchors`. *(Lệch so với bản đầu của đặc tả, đã chốt khi làm T2.)*
- **Thứ duy nhất build chèn thêm** là dòng `<!-- id: … -->` ngay dưới mỗi heading con (heading không phải heading gốc của note).
- **Link giữ nguyên văn** ở bước build (xem T2). Sau `relink` thì là link markdown `[text](<ID>.md)`, không dùng wikilink.
- **Ảnh** dùng link markdown tương đối `../attachments/<CODE>/<file>`, không dùng `![[…]]`: hiển thị được cả trong Obsidian lẫn renderer khác, và giữ alt text. (Điều chỉnh so với D3; cập nhật D3 khi merge T2.)
- **Preamble** (nội dung trước heading đầu tiên, ví dụ trang kiểm soát tài liệu) là note `<CODE>-0000`.

**Manifest** `data/vault/<CODE>/_manifest.yaml`:

```yaml
spec: WRN
source: data/sources/WRN/7820ZXXXXG000_E_(Warning)_260220.md
source_sha256: …
built_with: specgarage 0.1.0
max_tokens: 3000
id_width: 4               # 4 chữ số; 5 nếu spec có > 9999 heading. Cố định cho cả spec
next_id: 1289
tree:                      # chỉ gồm note, theo thứ tự tài liệu
  - WRN-0000
  - WRN-0001:
      - WRN-0002
      - WRN-0339:
          - WRN-0340
          - WRN-0342
retired: []                # { id, merged_into | reason }
```

### T1: `ids.py`, manifest và cấp ID ✅

> Xong (branch `phase1/t1-ids-manifest`). API: `Manifest` (`allocate`, `check_id`, `walk`, `ids`, `find`, `parent_of`, `add`, `remove`, `retire`, `to_dict`/`from_dict`), `load_manifest`, `save_manifest` (ghi atomic), `manifest_path`, `allocate_ids`, `width_for`. `from_dict` từ chối tree có ID trùng, ID chưa cấp, ID đã retire, ID khác spec.


- `load_manifest(code)`, `save_manifest(m)` (YAML, giữ thứ tự khoá).
- `allocate(code, n=1) -> list[str]`: lấy từ `next_id`, tăng và ghi lại. Độ rộng số lấy từ `id_width` của manifest (D2: cố định cho cả spec). Báo lỗi nếu vượt quá độ rộng, không tự đổi độ rộng giữa chừng.
- `retire(id, merged_into=None, reason=…)`.
- Iterator trên cây manifest (thứ tự, cha/con).
- **Test:** cấp liên tiếp, không cấp lại ID đã retire, `id_width` 4 và 5, báo lỗi khi tràn.

### T2: `build_vault.py` (`sg build-vault [CODE…] [--max-tokens N] [--force]`) ✅

> Xong (branch `phase1/t2-vault-decisions`). Guide: [`guides/build-vault.md`](guides/build-vault.md). Trên spec thật: 445 note, nối lại ra đúng văn bản gốc.

> **Phạm vi đã thu hẹp (chốt 2026-09-23): "T2-lite".** Build **không viết lại link**. Việc đó là ticket riêng T2b `sg relink`.
> Lý do: viết lại link là phần rủi ro nhất (link resolve sai đích thì mất dữ liệu ngầm, khó phát hiện) và cũng là phần làm `sg export` khó round-trip. Tách ra thì build + export chứng minh được gần như hiển nhiên, và Gate B tới sớm hơn.

1. Parse spec trong registry, dựng bản đồ `anchor → heading index` **trong từng spec**. (Không có link cross-file: profile đo được 0 trên cả ba spec.)
2. Gán ID cho mọi heading theo thứ tự tài liệu, bắt đầu từ `0001`. Preamble là `0000`.
3. Chọn note root: refactor `profile.plan_notes` để trả về **danh sách heading index** thay vì chỉ kích thước. Profile và build phải dùng chung một thuật toán, ngưỡng mặc định **3000**.
4. Với mỗi note:
   - Viết frontmatter như định dạng trên.
   - Chèn comment ID cho heading con.
   - Giữ nguyên anchor (không đổi sang comment).
5. **Link: giữ nguyên văn.** Không đụng vào `[text](#slug)` hay `[text](#_Ref…)`. Thay vào đó build sinh `data/vault/<CODE>/_anchors.yaml`:
   ```yaml
   spec: WRN
   anchors:            # anchor (tường minh hoặc slug heading) → ID của heading sở hữu nó
     _Ref512345678: WRN-0345
     buzzer-parameters: WRN-0342
   notes:              # heading ID → ID của note chứa heading đó (chỉ ghi khi hai cái khác nhau)
     WRN-0345: WRN-0342
   ```
   Muốn biết note đích của một anchor: `notes.get(anchors[a], anchors[a])`.
   Đây là đầu vào của T2b `relink`, của `sg related` và của `validate` (kiểm link gãy mà không cần link đã được viết lại).
6. Copy ảnh vào `data/vault/attachments/<CODE>/` và viết lại đường dẫn ảnh (đây là thứ **duy nhất** build được phép viết lại, vì file đã đổi chỗ thật).
7. Ghi `_manifest.yaml` và sinh `_toc.md` (danh sách lồng nhau, link markdown `[legacy title](ID.md)`).
8. **An toàn:**
   - Từ chối ghi đè `data/vault/<CODE>/` đã tồn tại nếu không có `--force`.
   - Nếu tag `baseline-original` đã tồn tại trong repo `data/` thì từ chối kể cả khi có `--force`, trừ khi có thêm `--i-know-baseline-exists`.
9. `legacy_number` lấy từ tiêu đề: Phase 0 cho thấy ≥ 98.6 % heading có số. Heading không có số thì để trống.
10. **Từ Phase 0** ([phase0-findings.md](phase0-findings.md)):
    - Dòng chỉ có anchor nằm ngay trước heading (`placement: before_heading`) được **chuyển vào note của heading đó**, giữ nguyên văn, không để lại ở cuối note phía trước.
    - Không cắt giữa bảng HTML (`<table>…</table>`). Bảng HTML được giữ nguyên văn.
    - **Preamble của WRN là mục lục và nặng ~16.5k token** (EWA ~5.7k). Nó luôn vượt mọi ngưỡng — đó là chuyện bình thường, giữ nguyên văn làm note `-0000`, skill bỏ qua note này. Không tách mục lục.

### T2b: `relink.py` (`sg relink [CODE…] [--dry-run] [--report]`) — sau Gate B

Bước riêng, **sửa tại chỗ** trong vault, chỉ động vào link:

- Đọc `_anchors.yaml` của từng spec. Với mỗi link `[text](#anchor)`:
  - anchor thuộc heading gốc của note đích → `[text](<ID>.md)`;
  - anchor thuộc heading con → `[text](<ID>.md#<slug của heading con>)`;
  - không resolve được → **giữ nguyên link gốc**, thêm `#broken-ref`. Không bao giờ đoán đích.
- `--dry-run` in thống kê (resolve được bao nhiêu, gãy bao nhiêu) mà không sửa file.
- Chạy được nhiều lần, kết quả không đổi (idempotent): link đã ở dạng `<ID>.md` thì bỏ qua.
- **Sau `baseline-original`:** mỗi lần relink phải áp lên **cả baseline** và gắn tag mới (`baseline-relinked-1`), nếu không phép so sánh before/after sẽ lệch.

### T5: `export.py` (`sg export [CODE…] [--keep-ids] [--check]`) ✅

> Xong (branch `phase1/t5-export`). Guide: [`guides/export.md`](guides/export.md). `--check` là công cụ round-trip cho Gate B: so từng dòng không rỗng với source, thoát mã 1 nếu lệch. Export vault đã relink chưa được hỗ trợ (chờ T2b).

- Nối các note theo thứ tự `tree`, bỏ frontmatter.
- **Bỏ các dòng `<!-- id: … -->`** mà build chèn dưới heading con (với `--keep-ids` thì giữ).
- Trả đường dẫn ảnh `../attachments/<CODE>/<file>` về đường dẫn gốc trong source (ví dụ `images/media/<file>`). Đường dẫn gốc lấy từ source (`source` trong manifest), vì build chỉ giữ tên file.
- Anchor: không phải làm gì, vì build giữ nguyên văn.
- Link: **nếu vault chưa relink thì không phải làm gì** (link vốn là nguyên văn). Nếu đã relink thì đổi `[text](<ID>.md#…)` ngược về `[text](#<anchor đầu tiên của đích>)`.
- Ghi ra `build/export/<CODE>.md`.
- **Test round-trip (bắt buộc):** `export(build(source))` phải bằng `source` sau khi chuẩn hoá. Chuẩn hoá gồm:

  - Đường dẫn ảnh so theo tên file.
  - Dòng trống (build có thể thêm/bớt dòng trống ở ranh giới note).
  - Khoảng trắng cuối dòng.
  - (Chỉ khi đã relink) link so theo **section đích đã resolve**, không so theo cú pháp.

  Với vault chưa relink, round-trip gần như là "nối các note lại phải ra đúng file gốc" — dễ chứng minh, và đó chính là lý do tách `relink` ra.

  Chạy trên fixture, và trên spec thật ở §4.

### T4: `validate.py` (`sg validate [CODE…] [--json] [--fix-refs]`, exit ≠ 0 nếu có lỗi) ✅

> Xong (branch `phase1/t4-validate`). Guide: [`guides/validate.md`](guides/validate.md). V08 được hiểu là: dòng có `#broken-ref` thì link trên dòng đó chỉ là warning, không phải V04 error.

| Mã | Kiểm tra                                                                                          | Mức    |
| --- | -------------------------------------------------------------------------------------------------- | ------- |
| V01 | Frontmatter đủ trường bắt buộc;`id` trùng tên file; `spec` trùng thư mục            | error   |
| V02 | ID duy nhất trên toàn vault (note và comment heading con); đúng format                       | error   |
| V03 | Note khớp với manifest hai chiều; mọi ID <`next_id`; ID đã retire không còn xuất hiện  | error   |
| V04 | Link resolve được: link dạng`#anchor` phải có trong `_anchors.yaml`; link dạng `<ID>.md` phải có note đích, `#heading` phải tồn tại trong note đó | error   |
| V05 | Mọi heading con (không phải heading gốc của note) có đúng một dòng `<!-- id: … -->` ngay dưới, và ID trong đó khớp với manifest / `_anchors.yaml`. **Anchor thô được phép** (build giữ nguyên văn) | error   |
| V06 | Ảnh được tham chiếu tồn tại                                                                 | error   |
| V07 | `status` hợp lệ; `derived_from` / `merged_into` trỏ tới ID có thật                     | error   |
| V08 | Link còn gắn`#broken-ref`                                                                      | warning |
| V09 | Bảng pipe có số cột nhất quán                                                                | warning |
| V10 | `refs_out` khớp với link thực tế (gợi ý chạy lại cập nhật)                             | warning |

Có `--fix-refs` để cập nhật lại `refs_out`. Đây là thứ duy nhất validate được phép sửa.

### T3: `section.py` ✅

> Xong (branch `phase1/t3-get-related`). Guide: [`guides/get-related.md`](guides/get-related.md). `related` mặc định bỏ link từ mục lục (preamble), thêm `--include-preamble` để tính; bỏ cả link nội bộ của chính section đang hỏi.

- `sg get <ID> [--no-frontmatter]`:
  - In ra breadcrumb (`heading_path`) rồi đến nội dung.
  - Nếu ID là heading con, chỉ in phần đó kèm breadcrumb của note chứa nó.
- `sg related <ID> [--depth 1] [--json]`:
  - **out:** các link đi ra từ ID, resolve qua `_anchors.yaml` (chạy được cả khi chưa relink).
  - **in:** đảo ngược bản đồ đó — các note có link trỏ tới anchor thuộc ID.
  - Mỗi mục in ID, spec, tiêu đề, số token ước lượng. Không in nội dung, để agent tự `sg get` khi cần.

### T6: `sg new-id <CODE> [-n N]` ✅

> Xong cùng T1.


Wrapper CLI của `ids.allocate`, cần cho các skill khi tạo heading mới. Đã có chỗ trong `PLANNED` của `cli.py`. Làm cùng T1 vì chỉ vài dòng.

### T7: Test

- Mở rộng fixture giả lập: preamble; heading con có anchor; link tới heading con; cross-file hai chiều; ảnh; bảng; một link gãy cố ý.
- Mỗi rule V01–V10 có một fixture lỗi tương ứng.
- Test round-trip của T5.

### Done khi (Phase 1)

- [ ] `pytest` pass, round-trip pass trên fixture.
- [ ] `sg build-vault && sg validate` không có lỗi error trên fixture.
- [ ] Cập nhật `CLAUDE.md` (bỏ dòng "chưa implement") và các skill draft (bỏ ghi chú Draft khi lệnh `sg` tương ứng đã có).
- [ ] Cập nhật D3 trong design doc (cách nhúng ảnh, anchor trong body, note `-0000`).

---

## §4. Build vault từ spec thật và gắn baseline

1. Build và kiểm tra:
   ```bash
   uv run --project tools sg build-vault
   uv run --project tools sg validate
   uv run --project tools sg export WRN   # và EWA, LIN; so sánh round-trip
   ```
2. **Expert mở `data/vault/`** (VS Code, GitLab web hoặc Obsidian, tuỳ ý) và kiểm tra khoảng 10 note ngẫu nhiên mỗi spec:
   - Ranh giới note hợp lý chưa?
   - Ảnh hiển thị?
   - Bảng còn nguyên?
   - *Chưa* kiểm link bấm được hay đúng đích: link chỉ được viết lại ở T2b, việc kiểm link thuộc Gate D (`handoff.md` §6).
3. Sửa parser hoặc build nếu cần (kèm fixture tái hiện lỗi), rồi build lại với `--force`.
4. **Gắn baseline (bản "before")** trong repo `data/`:
   ```bash
   cd data
   git add -A && git commit -m "Baseline vault built with specgarage <version>"
   git tag baseline-original
   ```
   **Không bắt đầu improve khi chưa có tag này.** Nếu có git server nội bộ, push tag lên đó để có bản sao lưu.

---

## §5. Phase 2: thí điểm skill improve

1. **Chọn một cụm thí điểm:** 3–5 section liên quan trong `WRN`, tốt nhất là cụm có tham chiếu sang `LIN`, để thử cả `spec-consistency`.
2. **Chạy `spec-analyze`** trên từng section. Expert đọc report trong `data/reports/analyze/` và đánh dấu issue đúng/sai. Issue sai là dữ liệu để sửa skill hoặc checklist.
3. **Chạy `spec-restructure` và `spec-parameterize`** trên 1–2 section. Mỗi section một branch `improve/<ID>-…` trong repo `data/`.
4. **Expert review** bằng `git diff main...improve/<ID>-…` (hoặc xem trong Obsidian). Mỗi điểm accept / reject / sửa **kèm lý do**, ghi trong commit message hoặc `data/reports/review/<ID>.md`. Sau khi merge vào `main` của `data/`:
   - Chưng cất lý do thành rule `L-00x` trong `data/knowledge/lessons.md`.
   - Thuật ngữ mới đưa vào `data/knowledge/glossary.md`.
   - Nếu rút ra được quy tắc **chung, không chứa nội dung domain** (ví dụ một cải tiến quy trình của skill), gửi cho máy phát triển để cập nhật `SKILL.md` hoặc `knowledge/`.
5. **Tạo eval case:** mỗi section đã được duyệt thành một case trong `data/evals/skills/<skill>/` (input, expected, notes). Đủ 10–20 case thì chạy lại mỗi khi sửa skill.
6. **Hoàn thiện 4 skill draft** dựa trên những gì học được: cập nhật `SKILL.md` và bỏ ghi chú Draft.

---

## §6. Quyết định và câu hỏi còn mở

| # | Câu hỏi                                                                   | Người quyết     | Cần trước |
| - | --------------------------------------------------------------------------- | ------------------ | ------------ |
| 1 | ~~Chuyển repo sang private?~~ **Đã chốt 2026-09-23:** cả hai repo chuyển sang GitLab nội bộ, vẫn tách đôi | Chủ repo | — |
| 2 | ~~Định dạng anchor thực tế của converter~~ **Đã xong (P0.5):** slug kiểu pandoc + `<span id>` cho caption; 0 link unresolved trên cả ba spec | Phase 0            | T2           |
| 3 | ~~Ngưỡng tách D1~~ **Đã chốt: 3000** cho cả ba spec                     | Chủ repo + expert | T2           |
| 3b | ~~Cú pháp link trong vault~~ **Đã chốt:** markdown chuẩn, và build không relink (T2-lite) | Chủ repo | T2 |
| 4 | Spec ngoài bộ 3 được tham chiếu: thêm vào registry hay để ngoài? | Expert             | T2           |
| 5 | Quy ước đặt tên parameter và state (`glossary.md` › Naming)        | Expert             | §5 bước 3 |
| 6 | Người review, nhịp review (D10)                                          | Chủ repo          | §5          |

---

## Phụ lục: prompt mẫu giao việc cho worker AI

```
Bạn làm việc trong repo spec-garage.
Đọc CLAUDE.md, docs/spec-pipeline-design.md và docs/next-steps.md.
Nhiệm vụ: implement ticket <T1/T2/…> theo docs/next-steps.md §3 (định dạng dữ liệu + mô tả ticket).
Yêu cầu:
- Làm trên branch phase1/<ticket>-<mô-tả>.
- Thêm test với fixture GIẢ LẬP trong tools/tests/fixtures/. Không copy nội dung spec thật vào fixture hay commit.
- Không commit gì trong data/ (và các vị trí cũ sources/, vault/, reports/, evals/), không git add -f.
- Chạy: uv run --project tools --group dev pytest tools/tests
- Ngôn ngữ theo CLAUDE.md: code, comment, CLI/log/lỗi, commit message và mọi output trong data/ bằng tiếng Anh; tài liệu docs/ có thể tiếng Việt.
- Theo "Definition of done" trong CLAUDE.md: cập nhật docs/tasks.md và docs/guides/<tính-năng>.md (tính năng làm gì, cách dùng, quy tắc, giới hạn, test).
- Kết thúc: tóm tắt thay đổi, các điểm lệch khỏi đặc tả (nếu có) và lý do.
```
 