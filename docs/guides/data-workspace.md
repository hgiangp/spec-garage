# Guide: workspace dữ liệu `data/` và `sg init-data`

| | |
|---|---|
| **Task** | F4, P0.1 ([tasks](../tasks.md)) |
| **Trạng thái** | ✅ Đã implement (`f63aa37`) |
| **Code** | `tools/specgarage/init_data.py`, `tools/specgarage/data_template/` |
| **Test** | `tools/tests/test_init_data.py` |

## Tính năng làm gì

Spec là tài liệu mật. Mọi thứ rút ra từ spec được gom vào một thư mục `data/`:
- Repo code **luôn ignore** `data/`.
- `data/` là **một git repo riêng**, remote trỏ tới GitLab nội bộ.

`sg init-data` dựng thư mục này từ khung có sẵn.

| Repo | Chứa | Remote |
|---|---|---|
| `spec-garage` | Code, skill, tri thức chung, tài liệu | GitLab nội bộ `…/spec-garage.git` |
| `data/` | Spec gốc, vault, tri thức domain, report, eval | GitLab nội bộ `…/data.git` |

> Cập nhật 2026-09-23: trước đây repo code nằm public trên GitHub và máy dữ liệu chỉ được pull. Nay cả hai repo đều nội bộ, một máy làm được cả hai việc.

### Vì sao gom vào `data/` thay vì để `sources/`, `vault/`… ở gốc?

Một git repo thứ hai phủ lên các thư mục rải rác ở gốc vẫn phải đọc `.gitignore` của repo code, và git không có tuỳ chọn tắt việc này. Kết quả là repo dữ liệu cũng không thấy các file bị ignore. Gom vào `data/` thì hai repo tách bạch hoàn toàn.

## Cấu trúc `data/`

```
data/                      git repo riêng, remote = GitLab nội bộ
├─ README.md  .gitignore
├─ sources/<CODE>/         spec gốc Word→md + folder ảnh (chỉ đọc)
├─ vault/                  thư mục markdown (Obsidian chỉ là trình xem tuỳ chọn)
│  ├─ .obsidian/app.json   link markdown, không tự sửa link khi đổi tên
│  ├─ <CODE>/              note + _manifest.yaml + _anchors.yaml (sau T2)
│  └─ attachments/<CODE>/
├─ knowledge/              glossary.md, lessons.md: tri thức DOMAIN
├─ reports/                profile, analyze, consistency, validate, review
└─ evals/                  eval case cho skill
```

## Cách dùng

### Lần đầu

```bash
git pull
uv run --project tools sg init-data --migrate-legacy
```

Output mẫu:
```
moved: sources/WRN/7820ZXXXXG000_E_(Warning)_260220.md -> data/sources/WRN/…
created: data/README.md
created: data/knowledge/glossary.md
…
created: data/sources/WRN/
initialised local git repo: data/.git (no remote)
```

Commit lần đầu trong repo dữ liệu, rồi nối remote nội bộ:
```bash
cd data
git add -A && git commit -m "Initial specs"
git remote add origin ssh://git@git3.fsoft.com.vn:2022/GROUP/NSAUTOTEST20/NSTMDCON/user/giangpth13/data.git
git push -u origin main
cd ..
```

`sg init-data` cố tình **không** tự thêm remote: repo này chứa nội dung spec, nên việc nối nó với server nào phải do người làm, có ý thức.

### Tuỳ chọn

| Tuỳ chọn | Tác dụng |
|---|---|
| (không có) | Tạo các file và thư mục còn thiếu, `git init` nếu chưa có. **Không ghi đè** file đã tồn tại, nên chạy lại bao nhiêu lần cũng an toàn |
| `--migrate-legacy` | Chuyển từng file ở vị trí cũ (`sources/`, `vault/`, `reports/`, `evals/`) vào `data/` cùng đường dẫn. File đích đã tồn tại thì bỏ qua và báo. Thư mục cũ bị xoá khi đã rỗng |
| `--no-git` | Không chạy `git init` |

Nếu còn dữ liệu ở vị trí cũ mà không có `--migrate-legacy`, lệnh sẽ in `WARNING: data found in legacy locations…` và không di chuyển gì.

### Git trong `data/`

```bash
cd data
git switch -c improve/WRN-0342-parameters   # mỗi lần improve một branch
git diff main...                            # expert review
git switch main && git merge --no-ff improve/WRN-0342-parameters
git tag baseline-original                   # một lần, sau build-vault đầu tiên được duyệt (V3)
```

## Quy tắc

- **Không bao giờ** `git add -f` các đường dẫn `data/`, `sources/`, `vault/`, `reports/`, `evals/` trong repo code.
- Nội dung trong `data/` (glossary, lessons, report, eval) viết bằng **tiếng Anh**.
- `data/knowledge/` chứa tri thức domain. Quy tắc **chung**, không chứa nội dung spec, thì chuyển sang `knowledge/` hoặc skill của repo code.
- Repo `data/` chỉ push lên GitLab **nội bộ**. Không bao giờ thêm remote ra ngoài.

## Giới hạn đã biết

- Khung `data/` lấy từ `tools/specgarage/data_template/`. Khi khung thay đổi, chạy lại `sg init-data` chỉ **thêm** file còn thiếu, không cập nhật file đã có.
- Không có khoá chống chạy song song. Chỉ một người thao tác trên một bản `data/` tại một thời điểm.

## Test

```bash
uv run --project tools --group dev pytest tools/tests/test_init_data.py
```

Các trường hợp được test:
- tạo đủ khung;
- không ghi đè file đã có;
- cảnh báo khi còn dữ liệu ở vị trí cũ;
- migrate vào thư mục đích đã tồn tại sẵn;
- `git init`.
 