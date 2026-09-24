"""Check a built vault against the conventions (T4, rules V01-V10 in docs/next-steps.md).

Errors mean the vault is not safe to baseline or improve on; warnings are worth a look but do not
block. The only thing validate ever writes is ``refs_out`` in note frontmatter, and only with
``--fix-refs``.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

from .config import DATA_DIR, load_specs
from .export import ExportError, split_note
from .ids import IdError, format_id, load_manifest, manifest_path, parse_id
from .parse import PIPE_SEP_RE, Document, parse_text

REQUIRED_FIELDS = ("id", "spec", "title", "aliases", "legacy_number", "heading_path", "level",
                   "anchors", "refs_out", "status", "derived_from")
STATUSES = ("original", "proposed", "reviewed", "approved")
ID_COMMENT_RE = re.compile(r"^<!-- id: (\S+)(?: \| [^\n]*)? -->$")
NOTE_LINK_RE = re.compile(r"^(?:\.\./([A-Z]{2,5})/)?([A-Z]{2,5}-\d{4,5})\.md$")
BROKEN_REF = "#broken-ref"

RULES = {
    "V01": "frontmatter missing, malformed, or id/spec not matching the file",
    "V02": "section ID malformed, from another spec, or used twice",
    "V03": "notes and manifest disagree, or an ID is unallocated or retired",
    "V04": "link or anchor map pointing at nothing",
    "V05": "sub-heading without its <!-- id --> line, or id line in the wrong place",
    "V06": "image file missing",
    "V07": "bad status, derived_from or retired entry",
    "V08": "link marked #broken-ref",
    "V09": "pipe table rows with a different column count than the header",
    "V10": "refs_out differs from the links in the note",
}
LEVELS = {r: ("warning" if r in ("V08", "V09", "V10") else "error") for r in RULES}


class ValidateError(RuntimeError):
    pass


@dataclass
class Finding:
    rule: str
    path: str
    line: int
    message: str

    @property
    def level(self) -> str:
        return LEVELS[self.rule]


@dataclass
class Report:
    notes: dict[str, int] = field(default_factory=dict)  # spec code -> notes checked
    findings: list[Finding] = field(default_factory=list)
    fixed: int = 0

    @property
    def errors(self) -> int:
        return sum(1 for f in self.findings if f.level == "error")

    @property
    def warnings(self) -> int:
        return sum(1 for f in self.findings if f.level == "warning")

    def to_dict(self) -> dict:
        return {"notes": self.notes, "errors": self.errors, "warnings": self.warnings, "fixed": self.fixed,
                "findings": [asdict(f) | {"level": f.level} for f in self.findings]}


@dataclass
class NoteFile:
    id: str
    path: Path
    rel: str
    front: dict | None
    body: str
    offset: int  # lines before the body (frontmatter block)
    doc: Document | None = None


# ── reading ────────────────────────────────────────────────────────────────────────────────


def read_note(path: Path, rel: str, out: list[Finding]) -> NoteFile:
    text = path.read_text(encoding="utf-8")
    try:
        body = split_note(text, path)
    except ExportError as e:
        out.append(Finding("V01", rel, 1, str(e).split(": ", 1)[-1]))
        return NoteFile(path.stem, path, rel, None, text, 0)
    front_text = text[4:len(text) - len(body) - 5]
    offset = text[:len(text) - len(body)].count("\n")
    try:
        front = yaml.safe_load(front_text)
    except yaml.YAMLError as e:
        out.append(Finding("V01", rel, 1, f"frontmatter is not valid YAML: {e}"))
        front = None
    if front is not None and not isinstance(front, dict):
        out.append(Finding("V01", rel, 1, "frontmatter is not a mapping"))
        front = None
    return NoteFile(path.stem, path, rel, front, body, offset)


def pipe_rows(line: str) -> int:
    """Number of cells in a pipe-table row (escaped pipes and code spans do not split)."""
    line = re.sub(r"`[^`]*`", "", line.strip())
    line = line[1:] if line.startswith("|") else line
    line = line[:-1] if line.endswith("|") and not line.endswith("\\|") else line
    return len(re.split(r"(?<!\\)\|", line))


# ── checks ─────────────────────────────────────────────────────────────────────────────────


def check_spec(root: Path, code: str, fix_refs: bool, report: Report) -> None:
    out = report.findings
    vault = root / DATA_DIR / "vault" / code
    mpath = manifest_path(root, code)
    rel = lambda p: p.relative_to(root).as_posix()  # noqa: E731

    try:
        manifest = load_manifest(mpath)
    except (IdError, yaml.YAMLError) as e:
        out.append(Finding("V03", rel(mpath), 0, f"manifest unreadable: {e}"))
        return

    apath = vault / "_anchors.yaml"
    anchors: dict[str, str] = {}
    note_of: dict[str, str] = {}
    if apath.is_file():
        data = yaml.safe_load(apath.read_text(encoding="utf-8")) or {}
        anchors, note_of = data.get("anchors") or {}, data.get("notes") or {}
    else:
        out.append(Finding("V04", rel(apath), 0, "missing: links cannot be checked"))

    notes = {p.stem: read_note(p, rel(p), out) for p in sorted(vault.glob("*.md")) if not p.name.startswith("_")}
    report.notes[code] = len(notes)
    retired = {r.id for r in manifest.retired}
    preamble = format_id(code, 0, manifest.id_width)

    # V03: manifest <-> files
    in_tree = set(manifest.ids())
    for sid in sorted(in_tree - notes.keys()):
        out.append(Finding("V03", rel(vault), 0, f"{sid} is in the manifest but {sid}.md does not exist"))
    for sid in sorted(notes.keys() - in_tree):
        out.append(Finding("V03", notes[sid].rel, 0, f"{sid}.md is not in the manifest tree"))

    # V07: retired entries
    for r in manifest.retired:
        for label, sid in (("retired", r.id), ("merged_into", r.merged_into)):
            if sid is None:
                continue
            try:
                manifest.check_id(sid)
            except IdError as e:
                out.append(Finding("V07", rel(mpath), 0, f"{label}: {e}"))
        if r.merged_into in retired:
            out.append(Finding("V07", rel(mpath), 0, f"{r.id} is merged into {r.merged_into}, which is retired"))

    seen: Counter[str] = Counter()
    where: dict[str, str] = {}

    def claim(sid: str, path: str, line: int) -> None:
        try:
            parse_id(sid)
        except IdError as e:
            out.append(Finding("V02", path, line, str(e)))
            return
        if not sid.startswith(f"{code}-"):
            out.append(Finding("V02", path, line, f"{sid} does not belong to spec {code}"))
            return
        try:
            manifest.check_id(sid)
        except IdError as e:
            out.append(Finding("V03", path, line, str(e)))
        if sid in retired:
            out.append(Finding("V03", path, line, f"{sid} is retired but still used"))
        seen[sid] += 1
        if seen[sid] == 2:
            out.append(Finding("V02", path, line, f"{sid} is used twice (also in {where[sid]})"))
        where.setdefault(sid, path)

    targets: dict[Path, set[str]] = {}  # note path -> anchors a link fragment may use

    for sid, note in notes.items():
        claim(sid, note.rel, 0)

        # V01 / V07: frontmatter
        f = note.front
        if f is not None:
            missing = [k for k in REQUIRED_FIELDS if k not in f]
            if missing:
                out.append(Finding("V01", note.rel, 1, f"missing fields: {', '.join(missing)}"))
            if f.get("id") != sid:
                out.append(Finding("V01", note.rel, 1, f"id {f.get('id')!r} does not match the file name"))
            if f.get("spec") != code:
                out.append(Finding("V01", note.rel, 1, f"spec {f.get('spec')!r} does not match the folder {code}"))
            if "status" in f and f["status"] not in STATUSES:
                out.append(Finding("V07", note.rel, 1, f"status {f['status']!r} is not one of {', '.join(STATUSES)}"))
            for d in f.get("derived_from") or []:
                try:
                    manifest.check_id(str(d)) if str(d).startswith(f"{code}-") else parse_id(str(d))
                except IdError as e:
                    out.append(Finding("V07", note.rel, 1, f"derived_from: {e}"))

        note.doc = doc = parse_text(note.body, note.path)
        lines = note.body.splitlines()
        at = lambda ln: ln + note.offset  # noqa: E731  body line -> file line

        # V05: id lines under sub-headings
        heading_lines = {h.line for h in doc.headings}
        own = doc.headings[0].line if doc.headings and sid != preamble else None
        if own is None and sid != preamble:
            out.append(Finding("V05", note.rel, 0, "note has no heading"))
        for i, text in enumerate(lines, start=1):
            m = ID_COMMENT_RE.match(text)
            if m:
                claim(m.group(1), note.rel, at(i))
                if i - 1 not in heading_lines or i - 1 == own:
                    out.append(Finding("V05", note.rel, at(i), f"id line for {m.group(1)} is not directly under a sub-heading"))
                elif note_of.get(m.group(1), m.group(1)) != sid:
                    out.append(Finding("V05", note.rel, at(i),
                                       f"{m.group(1)} lives in {sid} but _anchors.yaml says {note_of.get(m.group(1))}"))
        for h in doc.headings:
            if h.line == own:
                continue
            below = lines[h.line] if h.line < len(lines) else ""
            if not ID_COMMENT_RE.match(below):
                out.append(Finding("V05", note.rel, at(h.line), f"sub-heading {h.number or h.title[:40]!r} has no id line under it"))

        # V06: images
        for img in doc.images:
            if re.match(r"^[a-z][a-z0-9+.-]*:", img.target, re.I):
                continue
            if not (note.path.parent / img.target).is_file():
                out.append(Finding("V06", note.rel, at(img.line), f"image not found: {img.target}"))

        # V08, V09
        for i, text in enumerate(lines, start=1):
            if BROKEN_REF in text:
                out.append(Finding("V08", note.rel, at(i), "link marked #broken-ref"))
            if PIPE_SEP_RE.match(text) and i >= 2:
                header, bad = pipe_rows(lines[i - 2]), 0
                j = i
                while j < len(lines) and lines[j].strip() and "|" in lines[j]:
                    bad += pipe_rows(lines[j]) != header
                    j += 1
                if bad:
                    out.append(Finding("V09", note.rel, at(i - 1), f"{bad} row(s) differ from the header's {header} columns"))

    # anchor map values must name real IDs
    known = set(seen)
    for anchor, sid in anchors.items():
        if sid not in known:
            out.append(Finding("V04", rel(apath), 0, f"anchor {anchor!r} points at {sid}, which exists nowhere in the vault"))

    # V04 / V10: links
    for sid, note in notes.items():
        doc, lines = note.doc, note.body.splitlines()
        refs: list[str] = []
        for link in doc.links:
            line_text = lines[link.line - 1] if link.line <= len(lines) else ""
            if link.kind == "internal":
                target = anchors.get(link.anchor or "")
                if target is None:
                    if BROKEN_REF not in line_text:
                        out.append(Finding("V04", note.rel, link.line + note.offset,
                                           f"link #{link.anchor} is not in _anchors.yaml"))
                    continue
                target = note_of.get(target, target)
            elif link.kind == "cross_file" and link.file_part and NOTE_LINK_RE.match(link.file_part):
                path = (note.path.parent / link.file_part).resolve()
                if not path.is_file():
                    out.append(Finding("V04", note.rel, link.line + note.offset, f"link to missing note {link.file_part}"))
                    continue
                if link.anchor and link.anchor not in _fragments(path, targets):
                    out.append(Finding("V04", note.rel, link.line + note.offset,
                                       f"{link.file_part} has no heading or anchor #{link.anchor}"))
                target = path.stem
            else:
                continue
            if target != sid and target not in refs:
                refs.append(target)

        declared = (note.front or {}).get("refs_out")
        if note.front is not None and sorted(declared or []) != sorted(refs):
            if fix_refs:
                note.front["refs_out"] = refs
                front = yaml.safe_dump(note.front, sort_keys=False, allow_unicode=True, width=10_000).rstrip("\n")
                note.path.write_text(f"---\n{front}\n---\n{note.body}", encoding="utf-8")
                report.fixed += 1
            else:
                out.append(Finding("V10", note.rel, 1, f"refs_out {declared} but links point at {refs}"))


def _fragments(path: Path, cache: dict[Path, set[str]]) -> set[str]:
    if path not in cache:
        text = path.read_text(encoding="utf-8")
        try:
            body = split_note(text, path)
        except ExportError:
            body = text
        doc = parse_text(body, path)
        cache[path] = set(doc.anchors) | set(doc.implicit_anchors)
    return cache[path]


def validate(root: Path, codes: list[str] | None = None, fix_refs: bool = False) -> Report:
    specs = [s.code for s in load_specs(root) if not codes or s.code in codes]
    if codes and not specs:
        raise ValidateError(f"no spec matches {codes}. Run `sg specs` to see the registry.")
    specs = [c for c in specs if manifest_path(root, c).is_file() or codes]
    if not specs:
        raise ValidateError(f"no vault found under {root / DATA_DIR / 'vault'}. Run `sg build-vault` first.")
    report = Report()
    for code in specs:
        check_spec(root, code, fix_refs, report)
    return report
