"""CLI `sg`. Every mechanical operation on specs and the vault goes through here so skills stay consistent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import profile
from .config import DATA_DIR, find_root, load_specs
from .ids import IdError, allocate_ids
from .init_data import init_data

PLANNED = {
    "build-vault": "Phase 1: data/sources/ → data/vault/ (split notes, assign IDs, frontmatter, wikilinks, copy images)",
    "get": "Phase 1: print a section by ID with its breadcrumb",
    "related": "Phase 1: sections an ID links to / is linked from, including cross-file",
    "validate": "Phase 1: broken links, duplicate IDs, manifest drift, table column mismatches",
    "export": "Phase 1: data/vault/ → build/export/<CODE>.md theo _manifest.yaml",
}


def cmd_profile(args: argparse.Namespace) -> int:
    paths = args.paths or [find_root() / DATA_DIR / "sources"]
    thresholds = [int(t) for t in args.thresholds.split(",")]
    text = profile.run(paths, thresholds, args.json, args.diagnose)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"Wrote {args.out}")
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


def cmd_new_id(args: argparse.Namespace) -> int:
    try:
        ids = allocate_ids(find_root(), args.code, args.n)
    except IdError as e:
        print(e, file=sys.stderr)
        return 1
    print("\n".join(ids))
    return 0


def cmd_planned(args: argparse.Namespace) -> int:
    print(f"`sg {args.command}` is not implemented yet. {PLANNED[args.command]}", file=sys.stderr)
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sg", description="Spec Garage tools")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("profile", help="Phase 0: structure statistics (headings, sizes, anchors, links, tables, images)")
    p.add_argument("paths", nargs="*", type=Path, help=".md files or directories (default: data/sources/)")
    p.add_argument("--thresholds", default="2000,3000,5000,8000", help="token thresholds for the note split simulation (D1)")
    p.add_argument("--json", action="store_true", help="output JSON instead of text")
    p.add_argument("--diagnose", action="store_true",
                   help="explain unresolved anchors with redacted markup skeletons (no spec text)")
    p.add_argument("--out", type=Path, help="write to a file, e.g. data/reports/profile.txt")
    p.set_defaults(func=cmd_profile)

    p = sub.add_parser("init-data", help="create the local data workspace data/ (its own git repo)")
    p.add_argument("--migrate-legacy", action="store_true",
                   help="move data from the legacy locations (sources/, vault/, reports/, evals/) into data/")
    p.add_argument("--no-git", action="store_true", help="do not run git init in data/")
    p.set_defaults(func=cmd_init_data)

    p = sub.add_parser("new-id", help="allocate new section IDs from next_id in data/vault/<CODE>/_manifest.yaml")
    p.add_argument("code", help="spec code, e.g. WRN")
    p.add_argument("-n", type=int, default=1, help="number of IDs to allocate")
    p.set_defaults(func=cmd_new_id)

    p = sub.add_parser("specs", help="list specs.yaml and check that source files exist")
    p.set_defaults(func=cmd_specs)

    for name, desc in PLANNED.items():
        p = sub.add_parser(name, help=f"(not implemented) {desc}")
        p.add_argument("rest", nargs=argparse.REMAINDER)
        p.set_defaults(func=cmd_planned)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
