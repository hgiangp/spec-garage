"""Build the vault from data/sources/ (T2).

Scope, deliberately narrow ("T2-lite"): this splits a spec into notes, gives every heading a
stable ID, writes frontmatter and copies the images. It does **not** rewrite links, and it does
not rewrite anchors either. Note text is the source text, verbatim, apart from two things:

- image paths, because the files really do move into attachments/;
- an ``<!-- id: ... -->`` comment under every heading that is not the note's own heading.

Everything else a reader might want rewritten -- ``[text](#_Ref123)`` into a link to a note --
is the job of ``sg relink`` (T2b), run later, once the vault has been checked. Keeping the
rewrite out of the build means the baseline is as close to the source as a split can be, and
makes ``sg export`` a concatenation rather than a reverse translation.
"""

from __future__ import annotations

import bisect
import hashlib
import re
import shutil
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import yaml

from . import __version__
from .config import DATA_DIR, Spec, load_specs
from .ids import Manifest, Node, format_id, save_manifest, width_for
from .notes import Note, plan_notes, tokens
from .parse import IMAGE_EXT, NUMBER_RE, Document, parse_file

DEFAULT_MAX_TOKENS = 3000  # D1, decided 2026-09-23 after the Phase 0 profile
BASELINE_TAG = "baseline-original"

MD_IMAGE_RE = re.compile(r"(!\[[^\]]*\]\(\s*)(<[^>\n]+>|(?:[^()\s]|\([^()\s]*\))+)((?:\s+\"[^\"]*\")?\s*\))")
HTML_IMAGE_RE = re.compile(r"(<img\b[^>]*?\bsrc\s*=\s*[\"'])([^\"']+)([\"'])", re.I)


class BuildError(RuntimeError):
    pass


@dataclass
class Built:
    """What one spec turned into, so the caller can report it without re-reading the vault."""
    code: str
    notes: int
    headings: int
    anchors: int
    images: int
    largest: int


# ── ids ─────────────────────────────────────────────────────────────────────────────────────


def assign_ids(doc: Document, code: str, width: int) -> tuple[str, list[str]]:
    """(preamble id, id per heading index). Every heading gets one, not just the note roots,
    so a link into an H5 still has something to point at."""
    preamble = format_id(code, 0, width)
    return preamble, [format_id(code, i + 1, width) for i in range(len(doc.headings))]


def note_id(note: Note, preamble: str, heading_ids: list[str]) -> str:
    return preamble if note.heading is None else heading_ids[note.heading]


# ── note text ───────────────────────────────────────────────────────────────────────────────


def id_comment(section_id: str, legacy: str | None, anchors: list[str]) -> str:
    parts = [f"id: {section_id}"]
    if legacy:
        parts.append(f"legacy: {legacy}")
    if anchors:
        parts.append("anchors: " + ", ".join(anchors))
    return "<!-- " + " | ".join(parts) + " -->"


def rewrite_image_paths(text: str, code: str) -> str:
    """Point image links at attachments/. The only content rewrite the build performs.

    Applied to whole note text, not line by line: pandoc wraps long alt text, so
    ``![two-line alt](images/media/image1.png)`` can straddle a line break.
    """
    def new_dest(dest: str) -> str:
        bare = dest[1:-1] if dest.startswith("<") and dest.endswith(">") else dest
        if Path(bare).suffix.lower() not in IMAGE_EXT:
            return dest
        return f"../attachments/{code}/{Path(bare).name}"

    text = MD_IMAGE_RE.sub(lambda m: m.group(1) + new_dest(m.group(2)) + m.group(3), text)
    return HTML_IMAGE_RE.sub(lambda m: m.group(1) + new_dest(m.group(2)) + m.group(3), text)


def heading_path(doc: Document, idx: int) -> list[str]:
    path, cur = [], idx
    while cur is not None:
        path.append(doc.headings[cur].title)
        cur = doc.headings[cur].parent
    return list(reversed(path))


def clean_number(title: str) -> str:
    """Heading title without its leading number, e.g. '3.2.4 Buzzer' -> 'Buzzer'."""
    return NUMBER_RE.sub("", title).strip() or title


def note_frontmatter(doc: Document, note: Note, section_id: str, code: str,
                     anchors: list[str], refs_out: list[str]) -> dict:
    if note.heading is None:
        return {
            "id": section_id, "spec": code, "title": "Preamble", "aliases": [],
            "legacy_number": "", "heading_path": [], "level": 0, "anchors": anchors,
            "refs_out": refs_out, "status": "original", "derived_from": [],
        }
    h = doc.headings[note.heading]
    title = clean_number(h.title)
    return {
        "id": section_id, "spec": code, "title": title,
        "aliases": [h.title] if h.title != title else [],
        "legacy_number": h.number or "", "heading_path": heading_path(doc, note.heading),
        "level": h.level, "anchors": anchors, "refs_out": refs_out,
        "status": "original", "derived_from": [],
    }


def render_note(doc: Document, note: Note, lines: list[str], code: str, section_id: str,
                heading_ids: list[str], anchors_at: dict[int, list[str]],
                refs_out: list[str]) -> str:
    heading_at = {h.line: h.index for h in doc.headings}
    anchors = sorted({a for ln in range(note.start, note.end) for a in anchors_at.get(ln, [])})

    body: list[str] = []
    for ln in range(note.start, note.end):
        body.append(lines[ln - 1])
        idx = heading_at.get(ln)
        if idx is not None and idx != note.heading:  # a sub-heading inside this note
            h = doc.headings[idx]
            body.append(id_comment(heading_ids[idx], h.number, h.anchors))

    front = yaml.safe_dump(note_frontmatter(doc, note, section_id, code, anchors, refs_out),
                           sort_keys=False, allow_unicode=True, width=10_000).rstrip("\n")
    text = rewrite_image_paths("\n".join(body).rstrip("\n"), code)
    return f"---\n{front}\n---\n{text}\n"


# ── maps written next to the notes ──────────────────────────────────────────────────────────


def anchor_map(doc: Document, preamble: str, heading_ids: list[str]) -> dict[str, str]:
    """anchor -> ID of the heading that owns it. Explicit anchors win over heading slugs."""
    out: dict[str, str] = {}
    for anchor, idx in doc.anchors.items():
        out[anchor] = preamble if idx is None else heading_ids[idx]
    for slug, idx in doc.implicit_anchors.items():
        out.setdefault(slug, heading_ids[idx])
    return out


def build_tree(doc: Document, notes: list[Note], preamble: str, heading_ids: list[str]) -> list[Node]:
    """Note tree, nested by the heading hierarchy (headings that are not notes are skipped)."""
    nodes = {n.heading: Node(note_id(n, preamble, heading_ids)) for n in notes}
    roots: list[Node] = []
    for n in notes:
        if n.heading is None:
            roots.append(nodes[n.heading])
            continue
        parent = doc.headings[n.heading].parent
        while parent is not None and parent not in nodes:
            parent = doc.headings[parent].parent
        (nodes[parent].children if parent is not None else roots).append(nodes[n.heading])
    return roots


def render_toc(doc: Document, notes: list[Note], preamble: str, heading_ids: list[str]) -> str:
    lines = ["# Contents", ""]
    depth = {None: 0}
    for n in notes:
        section_id = note_id(n, preamble, heading_ids)
        if n.heading is None:
            lines.append(f"- [Preamble]({section_id}.md)")
            continue
        h = doc.headings[n.heading]
        parent = h.parent
        while parent is not None and parent not in depth:
            parent = doc.headings[parent].parent
        level = depth[parent] + 1 if parent is not None else 0
        depth[n.heading] = level
        lines.append("  " * level + f"- [{h.title}]({section_id}.md)")
    return "\n".join(lines) + "\n"


# ── images ──────────────────────────────────────────────────────────────────────────────────


def copy_images(doc: Document, dest: Path, dry_run: bool) -> tuple[int, list[str]]:
    """Copy every referenced image into attachments/<CODE>/. Returns (copied, problems)."""
    base = doc.path.parent
    seen: dict[str, Path] = {}
    problems: list[str] = []
    for image in doc.images:
        src = (base / image.target).resolve()
        name = Path(image.target).name
        if name in seen:
            if seen[name] != src:
                problems.append(f"line {image.line}: two different images are both named {name}")
            continue
        if not src.is_file():
            problems.append(f"line {image.line}: missing image {image.target}")
            continue
        seen[name] = src
        if not dry_run:
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest / name)
    return len(seen), problems


# ── safety ──────────────────────────────────────────────────────────────────────────────────


def baseline_tag(code: str) -> str:
    """The tag holding the "before" vault of a spec added after the first baseline."""
    return f"{BASELINE_TAG}-{code}"


def baseline_of(data: Path, code: str) -> str | None:
    """The baseline tag that holds this spec's vault, or None if the spec is not baselined yet.

    Specs in the first baseline are under the shared tag; each spec added later gets its own. A
    spec is baselined only if the tag really contains its vault, so a new spec can be built while
    the others stay frozen.
    """
    for tag in (baseline_tag(code), BASELINE_TAG):
        try:
            done = subprocess.run(["git", "-C", str(data), "cat-file", "-e",
                                   f"{tag}:vault/{code}/_manifest.yaml"],
                                  capture_output=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            return None  # no git here: the caller is not running against a tagged baseline
        if done.returncode == 0:
            return tag
    return None


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ── driver ──────────────────────────────────────────────────────────────────────────────────


def build_spec(spec: Spec, vault: Path, max_tokens: int, dry_run: bool,
               source_path: str = "") -> tuple[Built, list[str]]:
    doc = parse_file(spec.source)
    source_path = source_path or spec.source.as_posix()
    notes = plan_notes(doc, max_tokens)
    width = width_for(len(doc.headings) + 1)
    preamble, heading_ids = assign_ids(doc, spec.code, width)

    anchors_at: dict[int, list[str]] = {}
    for d in doc.anchor_defs:
        anchors_at.setdefault(d.line, []).append(d.anchor)

    anchors = anchor_map(doc, preamble, heading_ids)
    # heading ID -> ID of the note that contains that heading (a note root maps to itself)
    starts = [n.start for n in notes]
    note_of: dict[str, str] = {preamble: preamble}
    for h in doc.headings:
        owner = notes[bisect.bisect_right(starts, h.line) - 1]
        note_of[heading_ids[h.index]] = note_id(owner, preamble, heading_ids)

    lines = doc.text.splitlines()
    out_dir = vault / spec.code
    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    largest = 0
    for n in notes:
        section_id = note_id(n, preamble, heading_ids)
        refs = _refs_out(doc, n, anchors, note_of, section_id)
        text = render_note(doc, n, lines, spec.code, section_id, heading_ids, anchors_at, refs)
        largest = max(largest, tokens(n.chars))
        if not dry_run:
            (out_dir / f"{section_id}.md").write_text(text, encoding="utf-8")

    copied, problems = copy_images(doc, vault / "attachments" / spec.code, dry_run)

    if not dry_run:
        manifest = Manifest(
            spec=spec.code,
            next_id=len(doc.headings) + 1,
            id_width=width,
            source=source_path,
            source_sha256=sha256(spec.source),
            built_with=f"specgarage {__version__}",
            max_tokens=max_tokens,
            tree=build_tree(doc, notes, preamble, heading_ids),
        )
        save_manifest(manifest, out_dir / "_manifest.yaml")
        (out_dir / "_anchors.yaml").write_text(
            yaml.safe_dump({"spec": spec.code, "anchors": anchors,
                            "notes": {h: n for h, n in note_of.items() if h != n}},
                           sort_keys=False, allow_unicode=True, width=10_000),
            encoding="utf-8")
        (out_dir / "_toc.md").write_text(render_toc(doc, notes, preamble, heading_ids), encoding="utf-8")

    return Built(spec.code, len(notes), len(doc.headings), len(anchors), copied, largest), problems


def _refs_out(doc: Document, note: Note, anchors: dict[str, str],
              note_of: dict[str, str], self_id: str) -> list[str]:
    """Notes this one links to, resolved through the anchor map (links themselves stay verbatim)."""
    out: list[str] = []
    for link in doc.links:
        if link.kind != "internal" or not (note.start <= link.line < note.end) or not link.anchor:
            continue
        heading_id = anchors.get(link.anchor)
        if heading_id is None:
            continue
        target = note_of.get(heading_id, heading_id)
        if target != self_id and target not in out:
            out.append(target)
    return out


def build_vault(root: Path, codes: list[str] | None = None, max_tokens: int = DEFAULT_MAX_TOKENS,
                force: bool = False, dry_run: bool = False,
                allow_baseline: bool = False) -> Iterator[str]:
    data = root / DATA_DIR
    vault = data / "vault"
    specs = [s for s in load_specs(root) if not codes or s.code in codes]
    if not specs:
        raise BuildError(f"no spec matches {codes}. Run `sg specs` to see the registry.")

    frozen = {s.code: tag for s in specs if (tag := baseline_of(data, s.code))}
    if frozen and not allow_baseline:
        which = ", ".join(f"{code} ({tag})" for code, tag in frozen.items())
        raise BuildError(
            f"already baselined: {which}. A baseline must never be rebuilt (improvements to "
            f"linking are `sg relink`, in place). Build only the specs that are not baselined, "
            f"or use --i-know-baseline-exists if you are deliberately discarding that baseline."
        )

    for spec in specs:
        if not spec.source.is_file():
            raise BuildError(f"{spec.code}: source not found: {spec.source}")
        out_dir = vault / spec.code
        if out_dir.exists() and any(out_dir.iterdir()) and not force and not dry_run:
            raise BuildError(f"{out_dir} already exists. Use --force to rebuild it.")

    for spec in specs:
        out_dir = vault / spec.code
        if force and not dry_run and out_dir.exists():
            shutil.rmtree(out_dir)
        try:
            rel = spec.source.relative_to(root).as_posix()
        except ValueError:
            rel = spec.source.as_posix()
        built, problems = build_spec(spec, vault, max_tokens, dry_run, rel)
        for p in problems:
            yield f"  WARNING {spec.code}: {p}"
        yield (f"{built.code}: {built.notes} notes, {built.headings} headings, "
               f"{built.anchors} anchors, {built.images} images, largest note ~{built.largest:,} tokens")

    yield ("dry run: nothing written" if dry_run else f"vault written to {vault}")
    if not dry_run:
        fresh = [s.code for s in specs if s.code not in frozen]
        if fresh:
            args = " ".join(fresh)
            yield (f"next: sg export {args} --check, sg validate {args}, commit in {DATA_DIR}/, then "
                   + ", ".join(f"git -C {DATA_DIR} tag -a {baseline_tag(c)} -m \"Before state of the {c} vault\""
                               for c in fresh))