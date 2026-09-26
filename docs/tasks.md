# Task list

Theo dõi toàn bộ công việc của Spec Garage: trạng thái, branch/commit, và hướng dẫn đi kèm.

- **Đặc tả chi tiết** của từng task: [`next-steps.md`](next-steps.md).
- **Lý do thiết kế:** [`spec-pipeline-design.md`](spec-pipeline-design.md).
- **Hướng dẫn sử dụng** từng tính năng đã có: [`guides/`](guides/).

**Trạng thái:** ✅ xong · 🔄 đang làm · ⏳ chưa làm · ⛔ bị chặn (ghi lý do)
**Máy:** cột này chỉ còn giá trị lịch sử — từ 2026-09-23 một máy làm cả hai việc. 💻 = làm trên repo code · 🗄️ = cần `data/`

## Điểm bắt đầu

Bắt đầu từ [`handoff.md`](handoff.md): trạng thái, quy trình convert, các quyết định Q1–Q7 đã chốt, đặc tả T2–T5, gate A/B/C/D, thứ tự việc.

**Đã đổi 2026-09-23:** cả repo code và repo `data/` đều nằm trên GitLab nội bộ, push trực tiếp. Mô hình "máy phát triển / máy dữ liệu" và `git bundle` không còn dùng.

## Quy tắc cập nhật

Mỗi commit hoặc PR hoàn thành (một phần) task phải kèm:

1. **Cập nhật file này:** trạng thái, branch/commit, ghi chú.
2. **Guide của tính năng** trong `docs/guides/`, tạo mới hoặc cập nhật:
   - Tính năng làm gì.
   - Cách dùng (lệnh, ví dụ, output).
   - Quy tắc cho agent và người dùng.
   - Giới hạn đã biết.
   - Cách test.
3. **Cập nhật `CLAUDE.md`** nếu thêm hoặc đổi lệnh, quy ước.

Commit chỉ có code, không kèm các mục trên, thì chưa được coi là xong.

---

## Nền tảng

| #  | Task                                                                      | Trạng thái | Máy | Branch / commit                               | Guide                                     | Ghi chú                                                                                      |
| -- | ------------------------------------------------------------------------- | ------------ | ---- | --------------------------------------------- | ----------------------------------------- | --------------------------------------------------------------------------------------------- |
| F1 | Design doc + quyết định D1–D13                                        | ✅           | 💻   | `scaffold/repo-skeleton` · `0ea4f00`     | [design](spec-pipeline-design.md)          | D1 (ngưỡng tách) chờ Phase 0                                                              |
| F2 | Khung repo:`CLAUDE.md`, `specs.yaml`, skills, `knowledge/`          | ✅           | 💻   | `0ea4f00`, `fcd3ce0`                      | [skills](guides/skills.md)                 |                                                                                               |
| F3 | Parser +`sg profile` + `sg specs`                                     | ✅           | 💻   | `0ea4f00`, sửa ở `fcd3ce0`, `f63aa37` | [profile](guides/profile.md)               |                                                                                               |
| F4 | Mô hình hai máy,`data/` + `sg init-data`                           | ✅           | 💻   | `f63aa37`                                   | [data-workspace](guides/data-workspace.md) |                                                                                               |
| F6 | Quy tắc ngôn ngữ: code/log/output tiếng Anh, tài liệu tiếng Việt  | ✅           | 💻   | `phase1/t1-ids-manifest`                    | [CLAUDE.md §Ngôn ngữ](../CLAUDE.md)     | CLI help, log, lỗi, format report, glossary/lessons chuyển sang tiếng Anh                  |
| F5 | ~~Tạo PR `scaffold/repo-skeleton` → `main`~~                       | ✅           | 💻   |                                               |                                           | Không còn cần: mọi commit đã nằm trên`main`, repo đã chuyển sang GitLab nội bộ |
| F7 | Chuyển hai repo sang GitLab nội bộ, chốt Q4/Q5/Q6/Q7, cập nhật docs | ✅           | 💻   | `phase1/t2-vault-decisions`                 | [handoff](handoff.md)                      | Bước 1 của kế hoạch: quy ước link, phạm vi T2-lite, chính sách hai repo             |

## Phase 0: profile dữ liệu thật

| #    | Task                                                                    | Trạng thái | Máy          | Branch / commit                                 | Guide                                                 | Ghi chú                                                                                                                                       |
| ---- | ----------------------------------------------------------------------- | ------------ | ------------- | ----------------------------------------------- | ----------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| P0.1 | `sg init-data --migrate-legacy`, commit đầu tiên trong `data/`   | ✅           | 🗄️          | `data/` · `e0ce919`                        | [data-workspace](guides/data-workspace.md)             | 386 file tracked, branch`main`, đã push lên GitLab nội bộ                                                                               |
| P0.2 | Chạy`sg profile` trên 3 spec                                        | ✅           | 🗄️          |                                                 | [findings](phase0-findings.md)                         | Đã chạy lại sau P0.5, số liệu ở`phase0-findings.md` §1                                                                               |
| P0.3 | Đọc profile: định dạng anchor, tỷ lệ link gãy,`legacy_number` | ✅           | 🗄️          |                                                 | [handoff §4](handoff.md#4-các-câu-hỏi-đã-chốt)  | Q1–Q3 đóng:**0 link unresolved** trên cả ba spec sau P0.5, không phải sửa converter                                              |
| P0.4 | Chốt ngưỡng tách D1 (Q4)                                            | ✅           | 🗄️ + expert |                                                 | [findings §3](phase0-findings.md#3-ngưỡng-tách-d1) | **3000** cho cả ba spec → 445 note                                                                                                     |
| P0.5 | Sửa parser theo định dạng thật của converter                      | ✅           | 🗄️          | `phase0/p05-anchor-resolution` · `e091821` | [profile](guides/profile.md)                           | `id` trên mọi tag, placement, slug ngầm kiểu pandoc (kể cả hậu tố `-1`), `--diagnose`, số heading, số tài liệu được nhắc |

## Phase 1: công cụ vault

| #   | Task                                                                               | Trạng thái | Máy      | Branch / commit                           | Guide                                                                                         | Ghi chú                                                                      |
| --- | ---------------------------------------------------------------------------------- | ------------ | --------- | ----------------------------------------- | --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| T1  | `ids.py`: manifest, cấp ID, cây note, retire                                   | ✅           | 💻        | `phase1/t1-ids-manifest` · `8095e35` | [ids-manifest](guides/ids-manifest.md)                                                         | `id_width` cố định cho cả spec                                          |
| T6  | `sg new-id <CODE> [-n N]`                                                        | ✅           | 💻        | `8095e35`                               | [ids-manifest §new-id](guides/ids-manifest.md#sg-new-id)                                      | Làm cùng T1                                                                 |
| Q5  | Chốt cú pháp link trong vault                                                   | ✅           | chủ repo |                                           | [handoff §4](handoff.md#4-các-câu-hỏi-đã-chốt)                                          | **Markdown chuẩn**, không wikilink                                    |
| Q6  | Có cần Obsidian không                                                           | ✅           | chủ repo |                                           | [handoff §4](handoff.md#4-các-câu-hỏi-đã-chốt)                                          | **Không.** Trình xem tuỳ chọn, không nằm trên đường tới hạn |
| Q7  | Phạm vi T2                                                                        | ✅           | chủ repo |                                           | [handoff §4](handoff.md#4-các-câu-hỏi-đã-chốt)                                          | **T2-lite:** build không viết lại link; relink tách thành T2b      |
| T2  | `sg build-vault` (T2-lite: tách note, ID, frontmatter, ảnh, `_anchors.yaml`) | ✅           | 🗄️      | `phase1/t2-vault-decisions`             | [build-vault](guides/build-vault.md)                                                           | 445 note trên spec thật; nối lại ra đúng bản gốc                      |
| T5  | `sg export` + `--check` round-trip | ✅ | 💻 | `phase1/t5-export` | [export](guides/export.md) | Round-trip chính xác (trừ dòng trống) trên fixture ở 4 ngưỡng. **Trên 3 spec thật: round-trip OK cả ba** (2026-09-24) |
| T4  | `sg validate` (V01–V10) | ✅ | 💻 | `phase1/t4-validate` | [validate](guides/validate.md) | Vault vừa build ra 0 finding trên fixture. **Chạy trên 3 spec thật ở V1** |
| T3  | `sg get`, `sg related` | ✅ | 💻 | `phase1/t3-get-related` | [get-related](guides/get-related.md) | Kèm `vault.py` (chỉ mục section, dùng chung với validate). Skill draft giờ đã có đủ lệnh `sg` |
| T7  | Mở rộng fixture và test                                                         | 🔄           | 🗄️      |                                           |                                                                                               | Làm dần theo từng ticket                                                   |
| T9  | Thêm spec không sửa repo code: registry sang `data/specs.yaml`, `sg add-spec`, baseline theo từng spec, `sg specs` in số note + tag | ✅ | 💻 | `phase1/t9-spec-independent` (xếp trên `phase2/s6-find-near-miss`) | [add-spec](guides/add-spec.md) | Docs chỉ còn quy tắc, không chép số liệu từng spec. Chuẩn hoá tên spec bỏ qua cả `/`. Chạy thật: ADAS AD (V4) |
| T2b | `sg relink`: viết lại link sang `[text](<ID>.md)`, tại chỗ                 | ⏳           | 🗄️      |                                           | [next-steps §3 T2b](next-steps.md#t2b-relinkpy-sg-relink-code---dry-run---report--sau-gate-b) | **Sau Gate B.** Phải áp lên cả baseline, gắn tag mới              |
| T8  | ~~Tạo PR `phase0/p05-anchor-resolution` → `main`~~                          | ✅           | 💻        |                                           |                                                                                               | Không còn cần:`main` đã chứa toàn bộ commit đó                    |

### T2 — kế hoạch chi tiết

Đặc tả: [next-steps §3 T2](next-steps.md#t2-build_vaultpy-sg-build-vault-code--max-tokens-n---force). Code mới: `tools/specgarage/build_vault.py`, guide: `docs/guides/build-vault.md`.

**Đầu ra mong đợi** (chạy trên 3 spec thật): 445 note · 2,206 ID · 4,519 anchor trong `_anchors.yaml` · 408 ảnh copy sang `attachments/`.

| #    | Bước                                                                                                                                                                                                    | Xong |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- |
| T2.1 | Planner dùng chung`notes.plan_notes` (profile và build cùng ranh giới), note phủ kín file                                                                                                         | ✅   |
| T2.2 | Gán ID cho**mọi** heading theo thứ tự tài liệu; preamble `-0000`; `id_width: 4`                                                                                                           | ✅   |
| T2.3 | Cắt note theo ranh giới T2.1,**không cắt giữa `<table>` HTML**                                                                                                                               | ✅   |
| T2.4 | Sinh nội dung note: frontmatter, comment ID cho heading con, anchor trước heading kéo vào note của heading đó.**Link và anchor giữ nguyên văn** (lệch so với đặc tả, xem ghi chú) | ✅   |
| T2.5 | Copy ảnh sang`attachments/<CODE>/` và viết lại đường dẫn ảnh (thứ duy nhất được viết lại)                                                                                               | ✅   |
| T2.6 | Ghi`_manifest.yaml`, `_anchors.yaml`, `_toc.md`                                                                                                                                                     | ✅   |
| T2.7 | An toàn:`--force`, chặn khi có tag `baseline-original`, `--dry-run`                                                                                                                              | ✅   |
| T2.8 | Fixture`DMD` kiểu pandoc + 18 test + [guide](guides/build-vault.md)                                                                                                                                     | ✅   |

**Kết quả trên spec thật:** 445 note (WRN 247, EWA 127, LIN 71) · 2,206 heading có ID · 5,661 anchor · 366 ảnh.
Nối note lại theo manifest ra **đúng** văn bản gốc trên cả ba spec (WRN 19,613 dòng không rỗng, EWA 6,275, LIN 5,383).

**Hai điểm lệch so với đặc tả `next-steps.md`:**

1. **Anchor trong body giữ nguyên văn**, không đổi sang `<!-- anchor: … -->`, và anchor trên dòng heading cũng không bị xoá. Lý do: anchor của converter là `<span id=… class="anchor">` rỗng, vốn không hiển thị, nên việc đổi chỉ thêm rủi ro và làm round-trip khó hơn mà không được gì.
2. **Sửa parser:** link và ảnh giờ được quét trên **toàn văn bản** thay vì từng dòng, vì pandoc ngắt dòng alt text — `![alt xuống dòng](image.png)` trước đây bị bỏ sót hoàn toàn. Số liệu profile trên ba spec không đổi (301/98/9 ảnh), nhưng fixture cho thấy lỗi là thật.

**Không thuộc T2:** viết lại link (T2b), validate (T4), export (T5).

## Phase 1b: vault từ spec thật

| #  | Task                                                                            | Trạng thái | Máy          | Ghi chú                                                                              |
| -- | ------------------------------------------------------------------------------- | ------------ | ------------- | ------------------------------------------------------------------------------------- |
| V1 | `sg build-vault && sg export --check && sg validate` trên 3 spec | ✅ | 🗄️ | Round-trip OK và validate xong trên cả ba spec (2026-09-24) |
| V2 | Expert kiểm tra khoảng 10 note mỗi spec (VS Code, GitLab web hoặc Obsidian) | ✅ | 🗄️ + expert | Ranh giới note, bảng, ảnh, frontmatter, dòng id (2026-09-24). Link chưa kiểm: thuộc Gate D |
| V3 | Tag `baseline-original` trong repo `data/` | ✅ | 🗄️ | `data/` commit `8e0bba9`. **Gate B đạt**: từ đây không chạy lại `build-vault` cho các spec trong tag này |
| V4 | Thêm spec ADAS AD (mã `ADAS`) | 🔄 | 🗄️ + expert | Build, round-trip OK, validate 0 lỗi, tag `baseline-original-ADAS` (`data/` commit `d08ee11`, branch `ingest/ADAS-baseline`). Còn: expert xem ~10 note, rồi merge vào `main` của `data/` |

## Phase 2: thí điểm improve

| #  | Task                                                               | Trạng thái | Máy          | Ghi chú                                                                                        |
| -- | ------------------------------------------------------------------ | ------------ | ------------- | ----------------------------------------------------------------------------------------------- |
| S1 | Chọn cụm thí điểm 3–5 section (WRN ↔ LIN)                   | ⏳           | 🗄️ + expert |                                                                                                 |
| S2 | `spec-analyze` trên cụm thí điểm, expert đánh giá report | ⏳           | 🗄️          | Chạy được ngay trên`data/sources/`, trước khi có vault. Xem [skills](guides/skills.md) |
| S3 | `spec-restructure`, `spec-parameterize` trên 1–2 section     | ⏳           | 🗄️          | Cần T3                                                                                         |
| S4 | Vòng review →`lessons.md`, `glossary.md`                     | ⏳           | 🗄️ + expert |                                                                                                 |
| S5 | Eval case 10–20 section                                           | ⏳           | 🗄️          |                                                                                                 |
| S6a | Skill `spec-trace` + `sg find`, `sg specs --lookup`, `aliases` trong registry | ✅ bản đầu | 🗄️ | Branch `phase2/s6-spec-trace`. Eval vòng 1: 3 lượt chạy xong (có skill 17/17 assertion; baseline 9/10 trên case 1); 3 lượt dừng vì hết hạn mức API, cần chạy lại. Xem [spec-trace](guides/spec-trace.md). Bổ sung (branch `phase2/s6-find-near-miss`): `sg find` 0 hit thì gợi ý tên dài hơn ra stderr (`R_SCROLL` → `R_SCROLL_UP`…), JSON thêm `matches` |
| S6 | Hoàn thiện 4 skill draft                                         | ⏳           | 💻            | Chỉ cải tiến quy trình, không đưa nội dung domain                                       |

## Câu hỏi mở

Xem [`next-steps.md` §6](next-steps.md#6-quyết-định-và-câu-hỏi-còn-mở).
