"""CLI `sg`. Every mechanical operation on specs and the vault goes through here so skills stay consistent."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import profile
from .build_vault import DEFAULT_MAX_TOKENS, BuildError, build_vault
from .config import DATA_DIR, find_root, load_specs, lookup_spec
from .export import ExportError, export_vault
from .find import find as find_term, near_misses as find_near_misses, to_dicts as find_to_dicts
from .ids import IdError, allocate_ids
from .init_data import init_data
from .section import get as get_section, related as related_sections
from .vault import VaultError
from .validate import RULES, ValidateError, validate
from .notes import SplitError

PLANNED = {
    "relink": "Phase 1: rewrite in-vault links to markdown links pointing at note IDs, in place (run after build-vault)",
}
NEAR_MISSES = 5  # longer names listed when a whole-word `find` has no hits


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
    if args.lookup is not None:
        s = lookup_spec(specs, args.lookup)
        if s is None:
            print(f"{args.lookup!r} is not in specs.yaml (code, title or aliases)", file=sys.stderr)
            return 1
        print(f"{s.code}  {s.title}  {s.source.relative_to(root).as_posix()}")
        return 0
    for s in specs:
        src = "ok" if s.source.is_file() else "MISSING"
        img = "-" if s.images is None else ("ok" if s.images.is_dir() else "MISSING")
        aka = f"  (aka {', '.join(s.aliases)})" if s.aliases else ""
        print(f"{s.code:<5} {s.doc_no:<15} {s.date:<10} source:{src:<7} images:{img:<7} {s.title}{aka}")
    return 0


def cmd_init_data(args: argparse.Namespace) -> int:
    for line in init_data(find_root(), migrate=args.migrate_legacy, git=not args.no_git):
        print(line)
    return 0


def cmd_build_vault(args: argparse.Namespace) -> int:
    try:
        for line in build_vault(find_root(), args.codes, args.max_tokens, args.force,
                                args.dry_run, args.i_know_baseline_exists):
            print(line)
    except (BuildError, SplitError) as e:
        print(e, file=sys.stderr)
        return 1
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    failed = False
    try:
        for r in export_vault(find_root(), args.codes, args.keep_ids, args.check, args.out_dir):
            print(f"{r.code}: {r.notes} notes, {r.lines:,} lines -> {r.path}")
            for w in dict.fromkeys(r.warnings):
                print(f"  WARNING {r.code}: {w}")
            if args.check:
                if r.mismatch:
                    failed = True
                    print(f"  round-trip FAILED {r.code}:")
                    for m in r.mismatch:
                        print(f"    {m}")
                else:
                    print(f"  round-trip OK {r.code}: identical to the source, ignoring blank lines")
    except ExportError as e:
        print(e, file=sys.stderr)
        return 1
    return 1 if failed else 0


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        report = validate(find_root(), args.codes, args.fix_refs)
    except ValidateError as e:
        print(e, file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        return 1 if report.errors else 0

    for code, n in report.notes.items():
        print(f"{code}: {n} notes checked")
    by_rule: dict[str, list] = {}
    for f in report.findings:
        by_rule.setdefault(f.rule, []).append(f)
    for rule in sorted(by_rule):
        items = by_rule[rule]
        print(f"{rule} {items[0].level:<7} {len(items):>5}  {RULES[rule]}")
        for f in items if args.all else items[:args.limit]:
            where = f"{f.path}:{f.line}" if f.line else f.path
            print(f"    {where}  {f.message}")
        if not args.all and len(items) > args.limit:
            print(f"    … {len(items) - args.limit} more (use --all)")
    if report.fixed:
        print(f"fixed refs_out in {report.fixed} note(s)")
    print(f"summary: {report.errors} error(s), {report.warnings} warning(s)")
    return 1 if report.errors else 0


def cmd_get(args: argparse.Namespace) -> int:
    try:
        s = get_section(find_root(), args.id, frontmatter=not args.no_frontmatter)
    except VaultError as e:
        print(e, file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(s, ensure_ascii=False, indent=2))
        return 0
    first, last = s["lines"]
    where = s["id"] if s["id"] == s["note"] else f"{s['id']} (in {s['note']})"
    print(f"{where}  {s['path']}:{first}-{last}  ~{s['tokens']:,} tokens")
    print(" > ".join(s["breadcrumb"]) or s["title"])
    print()
    print(s["text"])
    return 0


def cmd_related(args: argparse.Namespace) -> int:
    try:
        r = related_sections(find_root(), args.id, args.depth, args.include_preamble)
    except VaultError as e:
        print(e, file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0
    print(f"{r['id']}  {r['title']}  ~{r['tokens']:,} tokens")
    for direction, label in (("out", "links to"), ("in", "linked from")):
        items = r[direction]
        print(f"{label} ({len(items)}):")
        for i in items:
            inside = f" (in {i['note']})" if i["note"] != i["id"] else ""
            hop = f"  depth {i['depth']}" if args.depth > 1 else ""
            print(f"  {i['id']}{inside}  {i['title']}  ~{i['tokens']:,} tokens  via {', '.join(i['via'])}{hop}")
    return 0


def cmd_find(args: argparse.Namespace) -> int:
    try:
        hits = find_term(find_root(), args.term, args.spec, args.kind, args.case_sensitive,
                         not args.substring, args.include_preamble)
    except VaultError as e:
        print(e, file=sys.stderr)
        return 1
    if not hits and not args.substring:
        near = find_near_misses(find_root(), args.term, args.spec, args.kind, args.case_sensitive,
                                args.include_preamble)
        if near:
            names = ", ".join(f"{name} ({n})" for name, n in near.most_common(NEAR_MISSES))
            more = f", … {len(near) - NEAR_MISSES} more" if len(near) > NEAR_MISSES else ""
            print(f"no whole-word match; --substring finds it inside: {names}{more}", file=sys.stderr)
    if args.json:
        print(json.dumps(find_to_dicts(hits), ensure_ascii=False, indent=2))
        return 0 if hits else 1
    for h in hits[:None if args.all else args.limit]:
        inside = f" (in {h.note})" if h.note != h.id else ""
        print(f"{h.id}{inside}  {h.kind:<7}  {h.path}:{h.line}  {' > '.join(h.breadcrumb)}")
        print(f"    {h.snippet}")
    if not args.all and len(hits) > args.limit:
        print(f"… {len(hits) - args.limit} more (use --all)")
    print(f"{len(hits)} hit(s) in {len({h.id for h in hits})} section(s)")
    return 0 if hits else 1


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

    p = sub.add_parser("build-vault", help="Phase 1: data/sources/ → data/vault/ (split into notes, assign IDs, "
                                           "frontmatter, copy images; links are kept verbatim)")
    p.add_argument("codes", nargs="*", help="spec codes to build (default: all in specs.yaml)")
    p.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS,
                   help=f"split threshold per note (D1, default {DEFAULT_MAX_TOKENS})")
    p.add_argument("--force", action="store_true", help="rebuild a vault directory that already exists")
    p.add_argument("--dry-run", action="store_true", help="report what would be written, write nothing")
    p.add_argument("--i-know-baseline-exists", action="store_true",
                   help="build even though the baseline-original tag exists (this discards the baseline)")
    p.set_defaults(func=cmd_build_vault)

    p = sub.add_parser("export", help="Phase 1: data/vault/ → build/export/<CODE>.md, following _manifest.yaml")
    p.add_argument("codes", nargs="*", help="spec codes to export (default: every spec that has a vault)")
    p.add_argument("--keep-ids", action="store_true", help="keep the <!-- id: --> lines under sub-headings")
    p.add_argument("--check", action="store_true",
                   help="compare the export with the source (round trip, ignoring blank lines); exit 1 on a difference")
    p.add_argument("--out-dir", type=Path, help="directory to write to (default: build/export/)")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("validate", help="Phase 1: check the vault against the conventions (V01-V10); exit 1 on errors")
    p.add_argument("codes", nargs="*", help="spec codes to check (default: every spec that has a vault)")
    p.add_argument("--json", action="store_true", help="output JSON")
    p.add_argument("--fix-refs", action="store_true", help="rewrite refs_out in frontmatter to match the links (V10)")
    p.add_argument("--limit", type=int, default=10, help="findings shown per rule (default 10)")
    p.add_argument("--all", action="store_true", help="show every finding")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("get", help="print a section (note or sub-heading) by ID, with its file, lines and breadcrumb")
    p.add_argument("id", help="section ID, e.g. WRN-0342")
    p.add_argument("--no-frontmatter", action="store_true", help="for a note, print the body only")
    p.add_argument("--json", action="store_true", help="output JSON (id, note, path, lines, breadcrumb, tokens, text)")
    p.set_defaults(func=cmd_get)

    p = sub.add_parser("related", help="sections a section links to and is linked from (no text, just IDs)")
    p.add_argument("id", help="section ID, e.g. WRN-0342")
    p.add_argument("--depth", type=int, default=1, help="follow links this many hops (default 1)")
    p.add_argument("--include-preamble", action="store_true",
                   help="count links from the preamble (table of contents), which points at every heading")
    p.add_argument("--json", action="store_true", help="output JSON")
    p.set_defaults(func=cmd_related)

    p = sub.add_parser("find", help="sections where a term (signal, data name, parameter) appears, "
                                    "as heading, table or text; exit 1 if none")
    p.add_argument("term", help='text to look for, e.g. "FOO operation" (whole word, any case)')
    p.add_argument("--spec", action="append",
                   help="spec to search, by code, title or alias (e.g. LIN, 'LIN COMM'); repeatable. Default: all")
    p.add_argument("--kind", action="append", choices=["heading", "table", "text"],
                   help="only hits of this kind; repeatable")
    p.add_argument("--case-sensitive", action="store_true", help="match case exactly")
    p.add_argument("--substring", action="store_true",
                   help="match inside words too (by default 'FOO operation' does not match 'XFOO operation', "
                        "nor 'R_FOO' 'R_FOO_UP'; with no whole-word hit, stderr lists such longer names)")
    p.add_argument("--include-preamble", action="store_true", help="search the preamble (table of contents) too")
    p.add_argument("--limit", type=int, default=30, help="hits shown (default 30)")
    p.add_argument("--all", action="store_true", help="show every hit")
    p.add_argument("--json", action="store_true", help="output JSON")
    p.set_defaults(func=cmd_find)

    p = sub.add_parser("new-id", help="allocate new section IDs from next_id in data/vault/<CODE>/_manifest.yaml")
    p.add_argument("code", help="spec code, e.g. WRN")
    p.add_argument("-n", type=int, default=1, help="number of IDs to allocate")
    p.set_defaults(func=cmd_new_id)

    p = sub.add_parser("specs", help="list specs.yaml and check that source files exist")
    p.add_argument("--lookup", metavar="NAME",
                   help="which spec a name refers to (code, title or alias, e.g. 'LIN COMM'); exit 1 if not registered")
    p.set_defaults(func=cmd_specs)

    for name, desc in PLANNED.items():
        p = sub.add_parser(name, help=f"(not implemented) {desc}")
        p.add_argument("rest", nargs=argparse.REMAINDER)
        p.set_defaults(func=cmd_planned)

    return parser


def use_utf8_output() -> None:
    """Spec text is full of non-ASCII (→, ‑, “”); a Windows cp1252 console would crash on print."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure") and (stream.encoding or "").lower().replace("-", "") != "utf8":
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    use_utf8_output()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
