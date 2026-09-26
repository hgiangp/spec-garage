# data/: workspace dữ liệu spec

Thư mục này là **một git repo riêng**, remote là GitLab nội bộ. Repo code `spec-garage` luôn ignore `data/`.

```
data/
├─ specs.yaml          registry: mã spec ↔ file nguồn (đường dẫn tương đối với data/)
├─ sources/<CODE>/     spec gốc Word→md + folder ảnh (chỉ đọc)
├─ vault/              thư mục markdown (Obsidian chỉ là trình xem tuỳ chọn)
│  ├─ <CODE>/          note theo section + _manifest.yaml + _anchors.yaml + _toc.md
│  └─ attachments/<CODE>/
├─ knowledge/          tri thức domain: glossary.md, lessons.md
├─ reports/            output của sg profile / validate và các skill
└─ evals/              eval case cho skill, câu hỏi vàng
```

Trạng thái từng spec (số note, tag baseline): `uv run --project tools sg specs`.

## Thêm spec

```bash
uv run --project tools sg add-spec "data/sources/<tên>.out" --code <CODE> --build
```

Rồi commit `specs.yaml`, `sources/<CODE>`, `vault/<CODE>`, `vault/attachments/<CODE>` trên một branch riêng và gắn tag `baseline-original-<CODE>`.

## Git trong data/

```bash
cd data
git status / git diff                        # xem thay đổi
git switch -c improve/<CODE>-<NNNN>-…        # mỗi lần improve một branch
git tag -a baseline-original-<CODE> -m "…"   # một lần cho mỗi spec, ngay sau build-vault đầu tiên được duyệt
```

Chỉ push lên git server **nội bộ**. Không bao giờ thêm remote ra ngoài.
