# Task list

Theo dõi toàn bộ công việc của Spec Garage: trạng thái, branch/commit, và hướng dẫn đi kèm.

- **Đặc tả chi tiết** của từng task: [`next-steps.md`](next-steps.md).
- **Lý do thiết kế:** [`spec-pipeline-design.md`](spec-pipeline-design.md).
- **Hướng dẫn sử dụng** từng tính năng đã có: [`guides/`](guides/).

**Trạng thái:** ✅ xong · 🔄 đang làm · ⏳ chưa làm · ⛔ bị chặn (ghi lý do)
**Máy:** 💻 máy phát triển (push GitHub) · 🗄️ máy dữ liệu (chỉ pull, có `data/`)

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

| # | Task | Trạng thái | Máy | Branch / commit | Guide | Ghi chú |
|---|---|---|---|---|---|---|
| F1 | Design doc + quyết định D1–D13 | ✅ | 💻 | `scaffold/repo-skeleton` · `0ea4f00` | [design](spec-pipeline-design.md) | D1 (ngưỡng tách) chờ Phase 0 |
| F2 | Khung repo: `CLAUDE.md`, `specs.yaml`, skills, `knowledge/` | ✅ | 💻 | `0ea4f00`, `fcd3ce0` | [skills](guides/skills.md) | |
| F3 | Parser + `sg profile` + `sg specs` | ✅ | 💻 | `0ea4f00`, sửa ở `fcd3ce0`, `f63aa37` | [profile](guides/profile.md) | |
| F4 | Mô hình hai máy, `data/` + `sg init-data` | ✅ | 💻 | `f63aa37` | [data-workspace](guides/data-workspace.md) | |
| F6 | Quy tắc ngôn ngữ: code/log/output tiếng Anh, tài liệu tiếng Việt | ✅ | 💻 | `phase1/t1-ids-manifest` | [CLAUDE.md §Ngôn ngữ](../CLAUDE.md) | CLI help, log, lỗi, format report, glossary/lessons chuyển sang tiếng Anh |
| F5 | Tạo PR `scaffold/repo-skeleton` → `main` | ⏳ | 💻 | | | Máy chưa có `gh`, tạo PR trên web |

## Phase 0: profile dữ liệu thật

| # | Task | Trạng thái | Máy | Branch / commit | Guide | Ghi chú |
|---|---|---|---|---|---|---|
| P0.1 | `sg init-data --migrate-legacy`, commit đầu tiên trong `data/` | ⏳ | 🗄️ | (repo `data/`) | [data-workspace](guides/data-workspace.md) | |
| P0.2 | Chạy `sg profile` trên 3 spec | ⏳ | 🗄️ | | [profile](guides/profile.md) | Đã chạy một lần ở vị trí cũ, cần chạy lại sau khi migrate |
| P0.3 | Đọc profile: định dạng anchor, tỷ lệ link gãy, `legacy_number` | ⏳ | 🗄️ + 💻 | | [profile §Đọc kết quả](guides/profile.md#đọc-kết-quả) | Gửi `profile.txt` (chỉ thống kê) sang máy phát triển nếu cần hỗ trợ |
| P0.4 | Chốt ngưỡng tách D1 | ⏳ | 🗄️ + expert | | [profile §Chọn ngưỡng](guides/profile.md#chọn-ngưỡng-tách-d1) | Ghi vào design doc D1 |
| P0.5 | Sửa parser nếu converter có định dạng lạ | ⏳ | 💻 | | [profile §Giới hạn](guides/profile.md#giới-hạn-đã-biết) | Chỉ làm nếu P0.3 cần. Fixture giả lập, không dùng spec thật |

## Phase 1: công cụ vault

| # | Task | Trạng thái | Máy | Branch / commit | Guide | Ghi chú |
|---|---|---|---|---|---|---|
| T1 | `ids.py`: manifest, cấp ID, cây note, retire | ✅ | 💻 | `phase1/t1-ids-manifest` · `8095e35` | [ids-manifest](guides/ids-manifest.md) | `id_width` cố định cho cả spec |
| T6 | `sg new-id <CODE> [-n N]` | ✅ | 💻 | `8095e35` | [ids-manifest §new-id](guides/ids-manifest.md#sg-new-id) | Làm cùng T1 |
| T2 | `sg build-vault` | ⛔ | 💻 | | | Chờ P0.3, P0.4 (định dạng anchor, ngưỡng) |
| T5 | `sg export` + test round-trip | ⏳ | 💻 | | | Sau T2 |
| T4 | `sg validate` (V01–V10) | ⏳ | 💻 | | | |
| T3 | `sg get`, `sg related` | ⏳ | 💻 | | | Cần cho 4 skill draft |
| T7 | Mở rộng fixture và test | 🔄 | 💻 | | | Làm dần theo từng ticket |
| T8 | Tạo PR `phase1/t1-ids-manifest` → `main` | ⏳ | 💻 | | | Sau F5 |

## Phase 1b: vault từ spec thật

| # | Task | Trạng thái | Máy | Ghi chú |
|---|---|---|---|---|
| V1 | `sg build-vault && sg validate` trên 3 spec | ⏳ | 🗄️ | Sau T2, T4 |
| V2 | Expert kiểm tra khoảng 10 note mỗi spec trong Obsidian | ⏳ | 🗄️ + expert | Checklist: next-steps §4 |
| V3 | Tag `baseline-original` trong repo `data/` | ⏳ | 🗄️ | **Bắt buộc có trước Phase 2** |

## Phase 2: thí điểm improve

| # | Task | Trạng thái | Máy | Ghi chú |
|---|---|---|---|---|
| S1 | Chọn cụm thí điểm 3–5 section (WRN ↔ LIN) | ⏳ | 🗄️ + expert | |
| S2 | `spec-analyze` trên cụm thí điểm, expert đánh giá report | ⏳ | 🗄️ | Chạy được ngay trên `data/sources/`, trước khi có vault. Xem [skills](guides/skills.md) |
| S3 | `spec-restructure`, `spec-parameterize` trên 1–2 section | ⏳ | 🗄️ | Cần T3 |
| S4 | Vòng review → `lessons.md`, `glossary.md` | ⏳ | 🗄️ + expert | |
| S5 | Eval case 10–20 section | ⏳ | 🗄️ | |
| S6 | Hoàn thiện 4 skill draft | ⏳ | 💻 | Chỉ cải tiến quy trình, không đưa nội dung domain |

## Câu hỏi mở

Xem [`next-steps.md` §6](next-steps.md#6-quyết-định-và-câu-hỏi-còn-mở).
