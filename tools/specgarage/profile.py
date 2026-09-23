"""Phase 0: measure spec files to size the vault split (D1), IDs (D2) and link resolution (D3).

Output is statistics only. Anchor ids and file names are listed for unresolved links; no spec text is printed.
Token counts are approximate (characters / 4).
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .parse import Document, parse_file

CHARS_PER_TOKEN = 4
SAMPLE_LIMIT = 10


def tokens(chars: int) -> int:
    return round(chars / CHARS_PER_TOKEN)


def percentiles(values: list[int]) -> dict[str, int]:
    if not values:
        return {"n": 0}
    v = sorted(values)

    def pick(q: float) -> int:
        return v[min(len(v) - 1, int(q * len(v)))]

    return {"n": len(v), "min": v[0], "p50": pick(0.5), "p90": pick(0.9), "max": v[-1]}


def plan_notes(doc: Document, max_tokens: int) -> list[int]:
    """Simulate the D1 split: descend until a subtree fits, return note sizes in tokens.

    A heading whose subtree is too big becomes a note holding only its own text, and its children
    are split further. Text before the first heading counts as one note.
    """
    sizes: list[int] = []
    if doc.preamble_chars and doc.headings:
        sizes.append(tokens(doc.preamble_chars))

    def visit(idx: int) -> None:
        h = doc.headings[idx]
        if tokens(h.subtree_chars) <= max_tokens or not h.children:
            sizes.append(tokens(h.subtree_chars))
            return
        sizes.append(tokens(h.own_chars))
        for c in h.children:
            visit(c)

    for r in doc.roots:
        visit(r.index)
    return sizes


def profile_docs(docs: list[Document], thresholds: list[int]) -> dict:
    by_stem = {d.path.stem: d for d in docs}
    by_docno = {d.path.stem.split("_")[0]: d for d in docs}

    files = []
    cross_targets: Counter[str] = Counter()
    for d in docs:
        levels = Counter(h.level for h in d.headings)
        dup_titles = sum(c - 1 for c in Counter(h.title.lower() for h in d.headings).values() if c > 1)

        internal = [l for l in d.links if l.kind == "internal"]
        unresolved_internal = sorted({l.anchor for l in internal if l.anchor not in d.anchors})
        cross = [l for l in d.links if l.kind == "cross_file"]
        cross_stats = Counter()
        for l in cross:
            name = Path(l.file_part or "").name
            stem = Path(name).stem
            target = by_stem.get(stem) or by_docno.get(stem.split("_")[0])
            if target is None:
                cross_stats["unknown_file"] += 1
                cross_targets[name] += 1
            elif l.anchor and l.anchor not in target.anchors:
                cross_stats["file_ok_anchor_missing"] += 1
            else:
                cross_stats["resolved"] += 1

        base = d.path.parent
        missing_images = sorted({i.target for i in d.images if not (base / i.target).exists()})

        split = {}
        for t in thresholds:
            sizes = plan_notes(d, t)
            split[str(t)] = {
                "notes": len(sizes),
                "tokens": percentiles(sizes),
                "over_threshold": sum(1 for s in sizes if s > t),
                "tiny_under_50": sum(1 for s in sizes if s < 50),
            }

        files.append({
            "file": str(d.path),
            "lines": d.line_count,
            "tokens_approx": tokens(d.total_chars),
            "headings": {
                "total": len(d.headings),
                "by_level": {f"H{k}": levels.get(k, 0) for k in range(1, 7)},
                "with_number": sum(1 for h in d.headings if h.number),
                "with_anchor": sum(1 for h in d.headings if h.anchors),
                "duplicate_titles": dup_titles,
                "level_jumps": sum(
                    1 for h in d.headings
                    if h.parent is not None and h.level - d.headings[h.parent].level > 1
                ),
                "setext_suspects": d.setext_suspects,
            },
            "section_tokens": {
                "own_text_by_level": {
                    f"H{k}": percentiles([tokens(h.own_chars) for h in d.headings if h.level == k])
                    for k in range(1, 7) if levels.get(k)
                },
                "subtree_by_level": {
                    f"H{k}": percentiles([tokens(h.subtree_chars) for h in d.headings if h.level == k])
                    for k in range(1, 7) if levels.get(k)
                },
            },
            "tables": d.tables,
            "images": {"refs": len(d.images), "missing_files": len(missing_images),
                       "missing_sample": missing_images[:SAMPLE_LIMIT]},
            "anchors": {"defined": len(d.anchors), "syntax": d.anchor_syntax},
            "links": {
                "internal": len(internal),
                "internal_unresolved": len(unresolved_internal),
                "internal_unresolved_sample": unresolved_internal[:SAMPLE_LIMIT],
                "cross_file": len(cross),
                "cross_file_resolution": dict(cross_stats),
                "external": sum(1 for l in d.links if l.kind == "external"),
                "other": sum(1 for l in d.links if l.kind == "other"),
            },
            "split_simulation": split,
        })

    return {
        "note": "tokens ≈ chars/4; statistics only",
        "files": files,
        "cross_file_targets_not_in_set": dict(cross_targets.most_common()),
    }


def render_text(report: dict) -> str:
    out: list[str] = []
    w = out.append
    for f in report["files"]:
        h = f["headings"]
        w(f"=== {f['file']}")
        w(f"  lines {f['lines']:,}  ~tokens {f['tokens_approx']:,}")
        w("  headings " + str(h["total"]) + "  " + "  ".join(f"{k}:{v}" for k, v in h["by_level"].items()))
        w(f"    numbered {h['with_number']}  with anchor {h['with_anchor']}  duplicate titles {h['duplicate_titles']}"
          f"  level jumps {h['level_jumps']}  setext? {h['setext_suspects']}")
        w("  subtree tokens by level (n / p50 / p90 / max):")
        for lvl, p in f["section_tokens"]["subtree_by_level"].items():
            w(f"    {lvl}: {p['n']:>5} / {p['p50']:>7,} / {p['p90']:>7,} / {p['max']:>8,}")
        t = f["tables"]
        w(f"  tables pipe {t['pipe']}  grid {t['grid']}  html {t['html']}")
        im = f["images"]
        w(f"  images {im['refs']}  missing files {im['missing_files']}")
        a = f["anchors"]
        w(f"  anchors defined {a['defined']}  syntax {a['syntax']}")
        l = f["links"]
        w(f"  links internal {l['internal']} (unresolved {l['internal_unresolved']})"
          f"  cross-file {l['cross_file']} {l['cross_file_resolution']}  external {l['external']}  other {l['other']}")
        if l["internal_unresolved_sample"]:
            w(f"    unresolved sample: {', '.join(l['internal_unresolved_sample'])}")
        w("  split simulation (threshold → notes, p50 / p90 / max tokens, over, tiny<50):")
        for thr, s in f["split_simulation"].items():
            p = s["tokens"]
            w(f"    {int(thr):>6,} → {s['notes']:>5}  {p.get('p50', 0):>6,} / {p.get('p90', 0):>6,} / {p.get('max', 0):>7,}"
              f"  over {s['over_threshold']}  tiny {s['tiny_under_50']}")
        w("")
    if report["cross_file_targets_not_in_set"]:
        w("cross-file targets not in the profiled set:")
        for name, n in report["cross_file_targets_not_in_set"].items():
            w(f"  {n:>5}  {name}")
    return "\n".join(out)


def collect(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            files.extend(sorted(p.rglob("*.md")))
        elif p.suffix.lower() == ".md":
            files.append(p)
    return files


def run(paths: list[Path], thresholds: list[int], as_json: bool) -> str:
    files = collect(paths)
    if not files:
        raise SystemExit("Không tìm thấy file .md nào.")
    report = profile_docs([parse_file(f) for f in files], thresholds)
    return json.dumps(report, ensure_ascii=False, indent=2) if as_json else render_text(report)
