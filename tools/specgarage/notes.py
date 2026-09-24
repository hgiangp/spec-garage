"""Where a spec is split into notes (D1).

``sg profile`` simulates the split and ``sg build-vault`` performs it. Both call
:func:`plan_notes`, so what the profile reports and what the build writes can never drift
apart -- if they could, the Phase 0 numbers would say nothing about the real vault.

A note is a contiguous range of lines. The notes of a document **tile** it: every line
belongs to exactly one note, which is what lets ``sg export`` be a concatenation.
"""

from __future__ import annotations

from dataclasses import dataclass

from .parse import TABLE_CLOSE_RE, TABLE_OPEN_RE, Document

CHARS_PER_TOKEN = 4


def tokens(chars: int) -> int:
    """Approximate token count. Good enough to size notes, not to fill a context window."""
    return round(chars / CHARS_PER_TOKEN)


class SplitError(ValueError):
    pass


@dataclass
class Note:
    heading: int | None  # index into doc.headings; None = the preamble note (<CODE>-0000)
    start: int  # 1-based, inclusive: the heading line itself
    end: int  # 1-based, exclusive
    chars: int


def plan_notes(doc: Document, max_tokens: int) -> list[Note]:
    """Split a document into notes: descend the heading tree until a subtree fits.

    A heading whose subtree is too big becomes a note holding only the text down to its
    first child; the children then become notes of their own. Text before the first
    heading is one note.
    """
    if not doc.headings:
        return [Note(None, 1, doc.line_count + 1, doc.total_chars)]

    starts = _note_starts(doc, max_tokens)
    starts = _keep_html_tables_whole(doc, starts)
    starts = _pull_leading_anchor_lines(doc, starts)
    offsets = _line_offsets(doc)

    notes = []
    for n, (heading, start) in enumerate(starts):
        end = starts[n + 1][1] if n + 1 < len(starts) else doc.line_count + 1
        notes.append(Note(heading, start, end, offsets[end - 1] - offsets[start - 1]))
    return notes


def _note_starts(doc: Document, max_tokens: int) -> list[tuple[int | None, int]]:
    starts: list[tuple[int | None, int]] = []
    if doc.preamble_chars:
        starts.append((None, 1))

    def visit(idx: int) -> None:
        h = doc.headings[idx]
        starts.append((idx, h.line))
        if tokens(h.subtree_chars) > max_tokens and h.children:
            for c in h.children:
                visit(c)

    for r in doc.roots:
        visit(r.index)
    return starts


def _keep_html_tables_whole(doc: Document, starts: list[tuple[int | None, int]]) -> list[tuple[int | None, int]]:
    """Move any note boundary that would fall inside an HTML table past the end of it.

    The converter leaves large tables as raw HTML (WRN: 219 of them). Cutting one in half
    would destroy it in both the vault and the export.
    """
    spans = _html_table_spans(doc.text.splitlines())
    moved = []
    for heading, line in starts:
        for open_line, close_line in spans:
            if open_line < line <= close_line:
                moved.append((heading, close_line + 1, line))
                break
        else:
            moved.append((heading, line, line))

    for (_, prev_line, _), (heading, line, original) in zip(moved, moved[1:]):
        if line <= prev_line:
            raise SplitError(
                f"{doc.path.name}: the heading at line {original} sits inside an HTML table, "
                f"so a note cannot start there. Fix the source or raise --max-tokens."
            )
    return [(heading, line) for heading, line, _ in moved]


def _pull_leading_anchor_lines(doc: Document, starts: list[tuple[int | None, int]]) -> list[tuple[int | None, int]]:
    """Move an anchor-only line sitting just above a heading into that heading's note.

    Word bookmarks on a heading are emitted on their own line above it, so the anchor and the
    heading it names would otherwise land in different notes.
    """
    lines = doc.text.splitlines()
    owner = {d.line: d.heading for d in doc.anchor_defs if d.placement == "before_heading"}

    out: list[tuple[int | None, int]] = []
    for heading, line in starts:
        floor = out[-1][1] + 1 if out else 1
        pos, pulled = line - 1, line
        while heading is not None and pos >= floor:
            if owner.get(pos) == heading:
                pulled = pos
            elif lines[pos - 1].strip():
                break
            pos -= 1
        out.append((heading, pulled))
    return out


def _html_table_spans(lines: list[str]) -> list[tuple[int, int]]:
    """(first line, last line) of every top-level ``<table>`` block, nesting included."""
    spans: list[tuple[int, int]] = []
    depth, open_line = 0, 0
    for i, line in enumerate(lines, start=1):
        opens = len(TABLE_OPEN_RE.findall(line))
        closes = len(TABLE_CLOSE_RE.findall(line))
        if opens and depth == 0:
            open_line = i
        depth = max(0, depth + opens - closes)
        if closes and depth == 0 and open_line:
            spans.append((open_line, i))
            open_line = 0
    if open_line:  # never closed: treat the rest of the file as part of it
        spans.append((open_line, len(lines)))
    return spans


def _line_offsets(doc: Document) -> list[int]:
    """offsets[k] = number of characters in the first k lines (newline counted)."""
    offsets = [0]
    for line in doc.text.splitlines():
        offsets.append(offsets[-1] + len(line) + 1)
    return offsets