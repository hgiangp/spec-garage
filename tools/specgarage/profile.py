"""Phase 0: measure spec files to size the vault split (D1), IDs (D2) and link resolution (D3).

Output is statistics only: counts, anchor ids, heading numbers and file names. No spec text is
printed. `--diagnose` adds markup skeletons in which every word is replaced by `x`, so the report can
still leave the data machine. Token counts are approximate (characters / 4).
"""

from __future__ import annotations

import difflib
import json
import re
from collections import Counter
from pathlib import Path

from .parse import MD_LINK_RE, HTML_LINK_RE, Document, parse_file

CHARS_PER_TOKEN = 4
SAMPLE_LIMIT = 10
DIAGNOSE_LIMIT = 15
# Document numbers of this spec family, e.g. 7820ZXXXXG000 (4 digits, Z, 4 chars, letter, 3 digits).
DOC_NO_RE = re.compile(r"\b\d{4}Z[A-Z0-9]{4}[A-Z]\d{3}\b")
SLUG_LIKE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)+$")


def tokens(chars: int) -> int:
    return round(chars / CHARS_PER_TOKEN)


def percentiles(values: list[int]) -> dict[str, int]:
    if not values:
        return {"n": 0}
    v = sorted(values)

    def pick(q: float) -> int:
        return v[min(len(v) - 1, int(q * len(v)))]

    return {"n": len(v), "min": v[0], "p50": pick(0.5), "p90": pick(0.9), "max": v[-1]}


def plan_notes(doc: Document, max_tokens: int) -> list[tuple[int | None, int]]:
    """Simulate the D1 split: descend until a subtree fits. Returns (heading index, tokens) per note.

    A heading whose subtree is too big becomes a note holding only its own text, and its children
    are split further. Text before the first heading is one note with index None.
    """
    notes: list[tuple[int | None, int]] = []
    if doc.preamble_chars and doc.headings:
        notes.append((None, tokens(doc.preamble_chars)))

    def visit(idx: int) -> None:
        h = doc.headings[idx]
        if tokens(h.subtree_chars) <= max_tokens or not h.children:
            notes.append((idx, tokens(h.subtree_chars)))
            return
        notes.append((idx, tokens(h.own_chars)))
        for c in h.children:
            visit(c)

    for r in doc.roots:
        visit(r.index)
    return notes


def heading_label(doc: Document, idx: int | None) -> str:
    """Structural label only (number or position), never the heading text."""
    if idx is None:
        return "preamble"
    h = doc.headings[idx]
    return h.number or f"H{h.level}@line{h.line}"


def number_stats(doc: Document) -> dict:
    numbered = [h for h in doc.headings if h.number]
    offsets = Counter(h.level - (h.number.count(".") + 1) for h in numbered)
    dup_numbers = sum(c - 1 for c in Counter(h.number for h in numbered).values() if c > 1)
    return {
        "numbered": len(numbered),
        "unnumbered": len(doc.headings) - len(numbered),
        "level_minus_depth": {str(k): v for k, v in sorted(offsets.items())},
        "duplicate_numbers": dup_numbers,
    }


def skeleton(line: str, anchor: str) -> str:
    """Markup shape of a line: tags and attribute names kept, every word replaced by x."""
    def words(text: str) -> str:
        parts = text.split(anchor)
        red = [re.sub(r"x(?:[\s.,;:/()-]*x)+", "x…", re.sub(r"[^\W_]+", "x", p)) for p in parts]
        return "{ANCHOR}".join(red)

    def tag(m: re.Match) -> str:
        def attr(a: re.Match) -> str:
            value = a.group(2)[1:-1]
            shown = "{ANCHOR}" if anchor in value else "…"
            return f'{a.group(1)}="{shown}"'
        return re.sub(r"([\w:-]+)\s*=\s*(\"[^\"]*\"|'[^']*')", attr, m.group(0))

    out, pos = [], 0
    for m in re.finditer(r"<[^>]+>", line):
        out += [words(line[pos:m.start()]), tag(m)]
        pos = m.end()
    out.append(words(line[pos:]))
    return "".join(out).strip()[:200]


def diagnose_unresolved(doc: Document, unresolved: list[str]) -> dict:
    """Is each unresolved anchor present anywhere outside link targets (unrecognised syntax) or absent?"""
    lines = doc.text.splitlines()
    link_free = [HTML_LINK_RE.sub("<a>", MD_LINK_RE.sub("[]()", l)) for l in lines]
    slugs = list(doc.implicit_anchors)
    present, absent_slug, absent_other = 0, 0, 0
    samples, slug_samples, absent_samples = [], [], []
    for a in unresolved:
        rx = re.compile(r"(?<![\w-])" + re.escape(a) + r"(?![\w-])")
        hit = next((i for i, l in enumerate(link_free) if rx.search(l)), None)
        if hit is not None:
            present += 1
            if len(samples) < DIAGNOSE_LIMIT:
                samples.append({"anchor": a, "line": hit + 1, "skeleton": skeleton(lines[hit], a)})
        elif SLUG_LIKE_RE.match(a):
            absent_slug += 1
            if len(slug_samples) < DIAGNOSE_LIMIT:
                close = difflib.get_close_matches(a, slugs, n=1, cutoff=0.6)
                slug_samples.append({"anchor": a, "closest_heading_slug": close[0] if close else None})
        else:
            absent_other += 1
            if len(absent_samples) < DIAGNOSE_LIMIT:
                absent_samples.append(a)
    return {
        "present_but_unrecognised": present,
        "absent_slug_like": absent_slug,
        "absent_other": absent_other,
        "samples": samples,
        "slug_samples": slug_samples,
        "absent_samples": absent_samples,
    }


def profile_docs(docs: list[Document], thresholds: list[int], diagnose: bool = False) -> dict:
    by_stem = {d.path.stem: d for d in docs}
    by_docno = {d.path.stem.split("_")[0]: d for d in docs}

    files = []
    cross_targets: Counter[str] = Counter()
    for d in docs:
        levels = Counter(h.level for h in d.headings)
        dup_titles = sum(c - 1 for c in Counter(h.title.lower() for h in d.headings).values() if c > 1)
        own_docno = d.path.stem.split("_")[0]

        internal = [l for l in d.links if l.kind == "internal"]
        by_slug = sum(1 for l in internal if l.anchor not in d.anchors and l.anchor in d.implicit_anchors)
        unresolved_internal = sorted({l.anchor for l in internal if not d.resolve(l.anchor)[0]})
        cross = [l for l in d.links if l.kind == "cross_file"]
        cross_stats = Counter()
        for l in cross:
            name = Path(l.file_part or "").name
            stem = Path(name).stem
            target = by_stem.get(stem) or by_docno.get(stem.split("_")[0])
            if target is None:
                cross_stats["unknown_file"] += 1
                cross_targets[name] += 1
            elif l.anchor and not target.resolve(l.anchor)[0]:
                cross_stats["file_ok_anchor_missing"] += 1
            else:
                cross_stats["resolved"] += 1

        base = d.path.parent
        missing_images = sorted({i.target for i in d.images if not (base / i.target).exists()})

        split = {}
        for t in thresholds:
            notes = plan_notes(d, t)
            sizes = [n for _, n in notes]
            over = sorted((n for n in notes if n[1] > t), key=lambda n: -n[1])
            split[str(t)] = {
                "notes": len(notes),
                "tokens": percentiles(sizes),
                "over_threshold": len(over),
                "over_sample": [{"heading": heading_label(d, i), "tokens": n} for i, n in over[:SAMPLE_LIMIT]],
                "tiny_under_50": sum(1 for s in sizes if s < 50),
            }

        mentions = Counter(m for m in DOC_NO_RE.findall(d.text) if m != own_docno)

        entry = {
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
            "numbers": number_stats(d),
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
            "anchors": {
                "defined": len(d.anchors),
                "syntax": dict(Counter(a.syntax for a in d.anchor_defs).most_common()),
                "placement": dict(Counter(a.placement for a in d.anchor_defs).most_common()),
                "implicit_heading_slugs": len(d.implicit_anchors),
            },
            "links": {
                "internal": len(internal),
                "internal_resolved_by_slug": by_slug,
                "internal_unresolved_links": sum(1 for l in internal if not d.resolve(l.anchor)[0]),
                "internal_unresolved": len(unresolved_internal),
                "internal_unresolved_sample": unresolved_internal[:SAMPLE_LIMIT],
                "cross_file": len(cross),
                "cross_file_resolution": dict(cross_stats),
                "external": sum(1 for l in d.links if l.kind == "external"),
                "other": sum(1 for l in d.links if l.kind == "other"),
            },
            "doc_number_mentions": dict(mentions.most_common()),
            "split_simulation": split,
        }
        if diagnose:
            entry["diagnose_unresolved"] = diagnose_unresolved(d, unresolved_internal)
        files.append(entry)

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
        n = f["numbers"]
        w(f"  heading numbers: unnumbered {n['unnumbered']}  duplicate numbers {n['duplicate_numbers']}"
          f"  level-minus-depth {n['level_minus_depth']}")
        w("  subtree tokens by level (n / p50 / p90 / max):")
        for lvl, p in f["section_tokens"]["subtree_by_level"].items():
            w(f"    {lvl}: {p['n']:>5} / {p['p50']:>7,} / {p['p90']:>7,} / {p['max']:>8,}")
        t = f["tables"]
        w(f"  tables pipe {t['pipe']}  grid {t['grid']}  html {t['html']}")
        im = f["images"]
        w(f"  images {im['refs']}  missing files {im['missing_files']}")
        a = f["anchors"]
        w(f"  anchors defined {a['defined']}  implicit heading slugs {a['implicit_heading_slugs']}")
        w(f"    syntax {a['syntax']}")
        w(f"    placement {a['placement']}")
        l = f["links"]
        w(f"  links internal {l['internal']} (resolved by slug {l['internal_resolved_by_slug']},"
          f" unresolved {l['internal_unresolved_links']} links / {l['internal_unresolved']} distinct anchors)"
          f"  cross-file {l['cross_file']} {l['cross_file_resolution']}  external {l['external']}  other {l['other']}")
        if l["internal_unresolved_sample"]:
            w(f"    unresolved sample: {', '.join(l['internal_unresolved_sample'])}")
        if f["doc_number_mentions"]:
            w(f"  other doc numbers mentioned in text: {f['doc_number_mentions']}")
        w("  split simulation (threshold → notes, p50 / p90 / max tokens, over, tiny<50):")
        for thr, s in f["split_simulation"].items():
            p = s["tokens"]
            w(f"    {int(thr):>6,} → {s['notes']:>5}  {p.get('p50', 0):>6,} / {p.get('p90', 0):>6,} / {p.get('max', 0):>7,}"
              f"  over {s['over_threshold']}  tiny {s['tiny_under_50']}")
            if s["over_sample"]:
                w("             over: " + ", ".join(f"{o['heading']} ({o['tokens']:,})" for o in s["over_sample"]))
        diag = f.get("diagnose_unresolved")
        if diag:
            w(f"  diagnose unresolved anchors: present but unrecognised {diag['present_but_unrecognised']}"
              f"  absent slug-like {diag['absent_slug_like']}  absent other {diag['absent_other']}")
            for s in diag["samples"]:
                w(f"    present  {s['anchor']} @line {s['line']}: {s['skeleton']}")
            for s in diag["slug_samples"]:
                w(f"    slug     {s['anchor']}  closest heading slug: {s['closest_heading_slug']}")
            if diag["absent_samples"]:
                w(f"    absent   {', '.join(diag['absent_samples'])}")
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


def run(paths: list[Path], thresholds: list[int], as_json: bool, diagnose: bool = False) -> str:
    files = collect(paths)
    if not files:
        raise SystemExit("No .md files found.")
    report = profile_docs([parse_file(f) for f in files], thresholds, diagnose)
    return json.dumps(report, ensure_ascii=False, indent=2) if as_json else render_text(report)
