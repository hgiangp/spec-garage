# spec-garage

Ingest và improve spec automotive (Word → Markdown + ảnh) cùng AI agent.

- **Bàn giao / điểm bắt đầu:** [docs/handoff.md](docs/handoff.md)
- **Thiết kế và các quyết định:** [docs/spec-pipeline-design.md](docs/spec-pipeline-design.md)
- **Quy ước cho agent và người:** [CLAUDE.md](CLAUDE.md)
- **Hướng dẫn triển khai bước tiếp theo:** [docs/next-steps.md](docs/next-steps.md)
- **Task list và trạng thái:** [docs/tasks.md](docs/tasks.md)
- **Kết quả Phase 0 (profile):** [docs/phase0-findings.md](docs/phase0-findings.md)
- **Hướng dẫn sử dụng từng tính năng:**
  - [workspace `data/` và `sg init-data`](docs/guides/data-workspace.md)
  - [`sg profile`, `sg specs`, parser](docs/guides/profile.md)
  - [Section ID, manifest, `sg new-id`](docs/guides/ids-manifest.md)
  - [thêm spec: `sg add-spec`, registry `data/specs.yaml`](docs/guides/add-spec.md)
  - [skill improve và tri thức](docs/guides/skills.md)

## Hai máy

- **Máy phát triển:** code, skill, tài liệu. Push lên GitHub.
- **Máy dữ liệu:** chỉ `git pull`. Spec và mọi thứ rút ra từ spec nằm trong `data/`, một git repo local riêng mà repo public luôn ignore.

## Bắt đầu (máy dữ liệu)

Yêu cầu: [uv](https://docs.astral.sh/uv/), Python ≥ 3.11.

```bash
uv run --project tools sg init-data     # tạo data/ + git init (thêm --migrate-legacy nếu còn specs.yaml hoặc sources/ ở gốc)
uv run --project tools sg add-spec "<thư mục .out của converter>" --code <CODE> --build   # thêm từng spec
uv run --project tools sg specs         # trạng thái: source, ảnh, số note, tag baseline
uv run --project tools sg profile --out data/reports/profile.txt
```

Thêm spec chỉ thay đổi repo `data/`, không sửa gì trong repo này: [guide](docs/guides/add-spec.md).

## Cấu trúc

```
knowledge/          tri thức chung: style guide, checklist, templates
.claude/skills/     skill improve: spec-analyze, -restructure, -parameterize, -consistency, -diagram
tools/              CLI `sg` (+ data_template/ là khung cho data/)
data/               repo dữ liệu riêng: specs.yaml (registry), sources/, vault/, knowledge/ (glossary, lessons), reports/, evals/
```
