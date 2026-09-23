# data/: workspace dữ liệu spec (chỉ local)

Thư mục này là **một git repo riêng**, chỉ tồn tại trên máy có dữ liệu. Repo public `spec-garage` luôn ignore `data/`.

```
data/
├─ sources/<CODE>/     spec gốc Word→md + folder ảnh (chỉ đọc)
├─ vault/              Obsidian vault: mở đúng thư mục này trong Obsidian
│  ├─ <CODE>/          note theo section + _manifest.yaml + _toc.md
│  └─ attachments/<CODE>/
├─ knowledge/          tri thức domain: glossary.md, lessons.md
├─ reports/            output của sg profile / validate và các skill
└─ evals/              eval case cho skill, câu hỏi vàng
```

## Git trong data/

```bash
cd data
git status / git diff              # xem thay đổi
git switch -c improve/WRN-0342-…   # mỗi lần improve một branch
git tag baseline-original          # một lần, ngay sau build-vault đầu tiên được duyệt
```

Có thể push lên git server **nội bộ** nếu có. Không bao giờ push lên remote public.
