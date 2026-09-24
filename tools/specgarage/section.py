"""`sg get` and `sg related` (T3): what skills call to read a section and find its context.

Both work on section IDs: a note ID or the ID of a sub-heading inside a note. Links are resolved
through ``_anchors.yaml``, so they work on a vault that has not been relinked (T2-lite) as well
as on ``[text](<ID>.md#frag)`` links written by ``sg relink`` later.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .vault import Section, SpecVault, VaultError, load_spec_vault, spec_of

NOTE_LINK_RE = re.compile(r"^([A-Z]{2,5}-\d{4,5})\.md$")


def find_section(vault: SpecVault, section_id: str) -> Section:
    s = vault.sections.get(section_id)
    if s is None:
        raise VaultError(f"{section_id} not found in the {vault.code} vault")
    return s


def get(root: Path, section_id: str, frontmatter: bool = True) -> dict:
    vault = load_spec_vault(root, spec_of(section_id))
    s = find_section(vault, section_id)
    note = vault.notes[s.note]
    whole_note = s.id == s.note
    if whole_note and frontmatter:
        text = note.path.read_text(encoding="utf-8").rstrip("\n")
        first, last = 1, text.count("\n") + 1
    elif whole_note:
        text = note.body.rstrip("\n")
        first, last = note.offset + 1, note.offset + text.count("\n") + 1
    else:
        text = vault.text(s).rstrip("\n")
        first, last = vault.lines(s)
    return {
        "id": s.id, "note": s.note, "path": note.rel, "lines": [first, last],
        "title": s.title, "breadcrumb": vault.breadcrumb(s), "tokens": s.tokens, "text": text,
    }


# ── links between sections ─────────────────────────────────────────────────────────────────


@dataclass
class Edge:
    source: str
    target: str
    via: str  # the anchor, or the file name of a relinked link


def edges(vault: SpecVault) -> list[Edge]:
    """Every link in the vault as (section it sits in) -> (section it points at)."""
    at_line = {(s.note, s.start): s.id for s in vault.sections.values() if s.level}
    out: list[Edge] = []
    for note in vault.notes.values():
        for link in note.doc.links:
            target = None
            if link.kind == "internal" and link.anchor:
                target = vault.anchors.get(link.anchor)
                via = f"#{link.anchor}"
            elif link.kind == "cross_file" and link.file_part and (m := NOTE_LINK_RE.match(link.file_part)):
                via = link.file_part + (f"#{link.anchor}" if link.anchor else "")
                target = m.group(1)
                other = vault.notes.get(target)
                if other is not None and link.anchor:
                    found, idx = other.doc.resolve(link.anchor)
                    if found and idx is not None:
                        target = at_line.get((target, other.doc.headings[idx].line), target)
            if target is None or target not in vault.sections:
                continue
            source = vault.section_at(note.id, link.line).id
            out.append(Edge(source, target, via))
    return out


@dataclass
class Related:
    id: str
    note: str
    title: str
    tokens: int
    depth: int
    via: list[str] = field(default_factory=list)


def related(root: Path, section_id: str, depth: int = 1, include_preamble: bool = False) -> dict:
    vault = load_spec_vault(root, spec_of(section_id))
    query = find_section(vault, section_id)
    all_edges = edges(vault)

    def inside(outer_id: str, inner_id: str) -> bool:
        return vault.contains(vault.sections[outer_id], vault.sections[inner_id])

    def walk(direction: str) -> list[Related]:
        found: dict[str, Related] = {}
        frontier = {query.id}
        for d in range(1, depth + 1):
            nxt: set[str] = set()
            for e in all_edges:
                here, there = (e.source, e.target) if direction == "out" else (e.target, e.source)
                if not any(inside(f, here) for f in frontier):
                    continue
                if inside(query.id, there):
                    continue  # stays within the section asked about
                if direction == "in" and not include_preamble and vault.sections[there].note == vault.preamble:
                    continue  # the table of contents links to everything
                s = vault.sections[there]
                item = found.setdefault(s.id, Related(s.id, s.note, s.title, s.tokens, d))
                if e.via not in item.via:
                    item.via.append(e.via)
                if item.depth == d:
                    nxt.add(s.id)
            frontier = nxt
            if not frontier:
                break
        return sorted(found.values(), key=lambda r: (r.depth, r.id))

    return {
        "id": query.id, "note": query.note, "title": query.title, "tokens": query.tokens,
        "out": [r.__dict__ for r in walk("out")],
        "in": [r.__dict__ for r in walk("in")],
    }
