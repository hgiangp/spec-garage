# spec-garage

Ingest và improve spec automotive (Word → Markdown + ảnh) cùng AI agent.

- **Thiết kế và các quyết định:** [docs/spec-pipeline-design.md](docs/spec-pipeline-design.md)
- **Quy ước cho agent và người:** [CLAUDE.md](CLAUDE.md)
- **Hướng dẫn triển khai bước tiếp theo:** [docs/next-steps.md](docs/next-steps.md)

## Hai máy

- **Máy phát triển:** code, skill, tài liệu. Push lên GitHub.
- **Máy dữ liệu:** chỉ `git pull`. Spec và mọi thứ rút ra từ spec nằm trong `data/`, một git repo local riêng mà repo public luôn ignore.

## Bắt đầu (máy dữ liệu)

Yêu cầu: [uv](https://docs.astral.sh/uv/), Python ≥ 3.11.

```bash
uv run --project tools sg init-data     # tạo data/ + git init (thêm --migrate-legacy nếu đã chép spec vào sources/ cũ)
# chép spec đã convert vào data/sources/<CODE>/ đúng tên trong specs.yaml, kèm folder ảnh
uv run --project tools sg specs
uv run --project tools sg profile --out data/reports/profile.txt
```

## Cấu trúc

```
specs.yaml          registry spec: mã ↔ file nguồn
knowledge/          tri thức chung: style guide, checklist, templates
.claude/skills/     skill improve: spec-analyze, -restructure, -parameterize, -consistency, -diagram
tools/              CLI `sg` (+ data_template/ là khung cho data/)
data/               CHỈ LOCAL: sources/, vault/ (mở trong Obsidian), knowledge/ (glossary, lessons), reports/, evals/
```
