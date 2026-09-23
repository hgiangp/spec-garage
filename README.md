# spec-garage

Ingest và improve spec automotive (Word → Markdown + ảnh) cùng AI agent.

- **Thiết kế và các quyết định:** [docs/spec-pipeline-design.md](docs/spec-pipeline-design.md)
- **Quy ước cho agent và người:** [CLAUDE.md](CLAUDE.md)
- **Hướng dẫn triển khai bước tiếp theo:** [docs/next-steps.md](docs/next-steps.md)

## Bắt đầu

Yêu cầu: [uv](https://docs.astral.sh/uv/), Python ≥ 3.11.

```bash
# 1. Chép spec đã convert vào sources/<CODE>/ đúng tên trong specs.yaml, kèm folder ảnh
# 2. Kiểm tra registry
uv run --project tools sg specs

# 3. Phase 0: profile
uv run --project tools sg profile --out reports/profile.txt
```

## Cấu trúc

```
specs.yaml          registry spec: mã ↔ file nguồn
sources/<CODE>/     spec gốc (chỉ đọc)
vault/              Obsidian vault: mở đúng thư mục này trong Obsidian
knowledge/          style guide, checklist, glossary, lessons, templates
.claude/skills/     skill improve: spec-analyze, -restructure, -parameterize, -consistency, -diagram
tools/              CLI `sg`
evals/  reports/    eval skill, report
```
