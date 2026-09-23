"""CLI `sg`. Every mechanical operation on specs and the vault goes through here so skills stay consistent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import profile
from .config import DATA_DIR, find_root, load_specs
from .init_data import init_data

PLANNED = {
    "build-vault": "Phase 1: data/sources/ → data/vault/ (tách note, gán ID, frontmatter, wikilink, copy ảnh)",
    "get": "Phase 1: in section theo ID kèm breadcrumb",
    "related": "Phase 1: các section refer tới / được refer bởi một ID, kể cả cross-file",
    "validate": "Phase 1: link gãy, ID trùng, manifest lệch, bảng thiếu cột",
    "export": "Phase 1: data/vault/ → build/export/<CODE>.md theo _manifest.yaml",
    "new-id": "Phase 1 (T1/T6): cấp ID mới từ next_id trong _manifest.yaml",
}


def cmd_profile(args: argparse.Namespace) -> int:
    paths = args.paths or [find_root() / DATA_DIR / "sources"]
    thresholds = [int(t) for t in args.thresholds.split(",")]
    text = profile.run(paths, thresholds, args.json)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"Đã ghi {args.out}")
    else:
        print(text)
    return 0


def cmd_specs(args: argparse.Namespace) -> int:
    root = find_root()
    specs = load_specs(root)
    for s in specs:
        src = "ok" if s.source.is_file() else "MISSING"
        img = "-" if s.images is None else ("ok" if s.images.is_dir() else "MISSING")
        print(f"{s.code:<5} {s.doc_no:<15} {s.date:<10} source:{src:<7} images:{img:<7} {s.title}")
    return 0


def cmd_init_data(args: argparse.Namespace) -> int:
    for line in init_data(find_root(), migrate=args.migrate_legacy, git=not args.no_git):
        print(line)
    return 0


def cmd_planned(args: argparse.Namespace) -> int:
    print(f"`sg {args.command}` chưa được implement. {PLANNED[args.command]}", file=sys.stderr)
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sg", description="Spec Garage tools")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("profile", help="Phase 0: thống kê cấu trúc spec (heading, độ dài, anchor, link, bảng, ảnh)")
    p.add_argument("paths", nargs="*", type=Path, help="file .md hoặc thư mục (mặc định: data/sources/)")
    p.add_argument("--thresholds", default="2000,3000,5000,8000", help="ngưỡng token để mô phỏng tách note (D1)")
    p.add_argument("--json", action="store_true", help="xuất JSON thay vì text")
    p.add_argument("--out", type=Path, help="ghi ra file, ví dụ data/reports/profile.txt")
    p.set_defaults(func=cmd_profile)

    p = sub.add_parser("init-data", help="tạo workspace dữ liệu local data/ (git repo riêng)")
    p.add_argument("--migrate-legacy", action="store_true",
                   help="chuyển dữ liệu ở vị trí cũ (sources/, vault/, reports/, evals/) vào data/")
    p.add_argument("--no-git", action="store_true", help="không chạy git init trong data/")
    p.set_defaults(func=cmd_init_data)

    p = sub.add_parser("specs", help="liệt kê specs.yaml và kiểm tra file nguồn")
    p.set_defaults(func=cmd_specs)

    for name, desc in PLANNED.items():
        p = sub.add_parser(name, help=f"(chưa implement) {desc}")
        p.add_argument("rest", nargs=argparse.REMAINDER)
        p.set_defaults(func=cmd_planned)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
