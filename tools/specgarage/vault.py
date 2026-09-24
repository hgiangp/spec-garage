"""Read a built vault: notes, sections and the anchor map (shared by validate, get and related).

A *section* is any heading with an ID: a note's own heading (ID = the note ID) or a sub-heading
inside a note (ID from the ``<!-- id: ... -->`` line under it). The preamble note is a section
without a heading.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .config import DATA_DIR
from .export import ExportError, split_note
from .ids import IdError, Manifest, format_id, load_manifest, manifest_path, parse_id
from .notes import tokens
from .parse import Document, parse_text

ID_COMMENT_RE = re.compile(r"^<!-- id: (\S+)(?: \| [^\n]*)? -->$")


@dataclass
class NoteFile:
    id: str
    path: Path
    rel: str
    front: dict | None
    body: str
    offset: int  # lines before the body (frontmatter block)
    doc: Document | None = None


def read_note(path: Path, rel: str) -> tuple[NoteFile, list[str]]:
    """(note, problems). Problems are messages about the frontmatter; the note is still returned."""
    text = path.read_text(encoding="utf-8")
    try:
        body = split_note(text, path)
    except ExportError as e:
        return NoteFile(path.stem, path, rel, None, text, 0), [str(e).split(": ", 1)[-1]]
    front_text = text[4:len(text) - len(body) - 5]
    offset = text[:len(text) - len(body)].count("\n")
    try:
        front = yaml.safe_load(front_text)
    except yaml.YAMLError as e:
        return NoteFile(path.stem, path, rel, None, body, offset), [f"frontmatter is not valid YAML: {e}"]
    if front is not None and not isinstance(front, dict):
        return NoteFile(path.stem, path, rel, None, body, offset), ["frontmatter is not a mapping"]
    return NoteFile(path.stem, path, rel, front, body, offset), []


@dataclass
class Section:
    id: str
    note: str  # ID of the note file holding it
    title: str
    level: int  # 0 for the preamble
    start: int  # body line of the heading (1 for the preamble), inclusive
    end: int  # body line, exclusive: next heading of the same or a higher level, or note end
    parent: str | None  # enclosing section in the same note, None for a note's own heading
    tokens: int


@dataclass
class SpecVault:
    code: str
    root: Path
    manifest: Manifest
    notes: dict[str, NoteFile]
    sections: dict[str, Section]
    anchors: dict[str, str] = field(default_factory=dict)  # anchor -> heading ID
    note_of: dict[str, str] = field(default_factory=dict)  # heading ID -> note ID (when they differ)
    _by_note: dict[str, list[Section]] = field(default_factory=dict, repr=False)

    @property
    def preamble(self) -> str:
        return format_id(self.code, 0, self.manifest.id_width)

    def section_at(self, note_id: str, line: int) -> Section:
        """Smallest section of a note that contains a body line."""
        best = None
        for s in self.in_note(note_id):
            if s.start <= line < s.end and (best is None or s.start >= best.start):
                best = s
        return best or self.sections[note_id]

    def in_note(self, note_id: str) -> list[Section]:
        if not self._by_note:
            for s in self.sections.values():
                self._by_note.setdefault(s.note, []).append(s)
        return self._by_note.get(note_id, [])

    def contains(self, outer: Section, inner: Section) -> bool:
        return outer.note == inner.note and outer.start <= inner.start < outer.end

    def lines(self, s: Section) -> tuple[int, int]:
        """File line range (1-based, inclusive) of a section."""
        offset = self.notes[s.note].offset
        return s.start + offset, s.end - 1 + offset

    def text(self, s: Section) -> str:
        return "\n".join(self.notes[s.note].body.splitlines()[s.start - 1:s.end - 1])

    def breadcrumb(self, s: Section) -> list[str]:
        front = self.notes[s.note].front or {}
        path = list(front.get("heading_path") or [])
        chain = []
        cur: Section | None = s
        while cur is not None and cur.parent is not None:
            chain.append(cur.title)
            cur = self.sections.get(cur.parent)
        return path + list(reversed(chain))


class VaultError(RuntimeError):
    pass


def vault_dir(root: Path, code: str) -> Path:
    return root / DATA_DIR / "vault" / code


def load_spec_vault(root: Path, code: str) -> SpecVault:
    try:
        manifest = load_manifest(manifest_path(root, code))
    except IdError as e:
        raise VaultError(str(e)) from e
    folder = vault_dir(root, code)
    data = {}
    if (folder / "_anchors.yaml").is_file():
        data = yaml.safe_load((folder / "_anchors.yaml").read_text(encoding="utf-8")) or {}

    notes: dict[str, NoteFile] = {}
    for p in sorted(folder.glob("*.md")):
        if p.name.startswith("_"):
            continue
        note, _ = read_note(p, p.relative_to(root).as_posix())
        note.doc = parse_text(note.body, p)
        notes[note.id] = note

    vault = SpecVault(code, root, manifest, notes, {}, data.get("anchors") or {}, data.get("notes") or {})
    for note in notes.values():
        _add_sections(vault, note)
    return vault


def _add_sections(vault: SpecVault, note: NoteFile) -> None:
    doc, lines = note.doc, note.body.splitlines()
    end = len(lines) + 1
    if note.id == vault.preamble or not doc.headings:
        front = note.front or {}
        vault.sections[note.id] = Section(note.id, note.id, front.get("title") or note.id, 0, 1, end, None,
                                          tokens(len(note.body)))
        if note.id == vault.preamble:
            return
    ids: dict[int, str] = {}
    for n, h in enumerate(doc.headings):
        if n == 0:
            ids[h.index] = note.id
            continue
        m = ID_COMMENT_RE.match(lines[h.line]) if h.line < len(lines) else None
        if m:
            ids[h.index] = m.group(1)
    for h in doc.headings:
        sid = ids.get(h.index)
        if sid is None:
            continue
        parent = ids.get(h.parent) if h.parent is not None else None
        stop = min(h.end, end)
        text = "\n".join(lines[h.line - 1:stop - 1])
        vault.sections[sid] = Section(sid, note.id, h.title, h.level, h.line, stop, parent, tokens(len(text)))


def spec_of(section_id: str) -> str:
    try:
        return parse_id(section_id)[0]
    except IdError as e:
        raise VaultError(str(e)) from e
