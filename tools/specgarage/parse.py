"""Parse a Word-converted spec markdown file into a heading tree plus anchors, links, images and tables.

The converter output format is not fixed yet, so anchors and links are recognised in the common
forms produced by pandoc and similar tools:

- pandoc attributes:   ``# Title {#_Toc123}``, ``[]{#_Ref456 .anchor}``
- HTML anchors:        ``id=`` / ``name=`` on any tag: ``<a id="_Ref456"></a>``, ``<p id="...">``, ``<td id="...">``
- implicit heading IDs: slugs of the heading text (pandoc and GitHub styles), e.g. a link to
                       ``#abnormal-checksum-detection`` resolves to ``### 3.2.1 Abnormal Checksum Detection``
- markdown links:      ``[text](#_Ref456)``, ``[text](Other.docx#_Ref789)``, reference definitions
- HTML links:          ``<a href="#_Ref456">``

An anchor alone on the line(s) right before a heading belongs to that heading, not to the previous
section (Word bookmarks on headings are often emitted that way).
"""

from __future__ import annotations

import bisect
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote

FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})(.*)$")
ATX_RE = re.compile(r"^\s{0,3}(#{1,6})(?:[ \t]+(.*))?$")
ATX_CLOSE_RE = re.compile(r"(?:^|[ \t]+)#+[ \t]*$")
SETEXT_RE = re.compile(r"^\s{0,3}(=+|-+)\s*$")

ATTR_ID_RE = re.compile(r"\{[^{}\n]*?#([A-Za-z_][\w.:-]*)[^{}\n]*\}")
HTML_ID_RE = re.compile(r"<([A-Za-z][\w-]*)\b[^>]*?\s(?:id|name)\s*=\s*[\"']([^\"']+)[\"']", re.I)
# A line holding nothing but anchors, e.g. <a id="_Toc1"></a><a id="_Ref2"></a>
ANCHOR_ONLY_RE = re.compile(
    r"^\s*(?:(?:<(a|span)\b[^>]*?(?:/>|>\s*</\1\s*>)|\[\]\{[^}]*\})\s*)+$", re.I)
TABLE_OPEN_RE = re.compile(r"<table\b", re.I)
TABLE_CLOSE_RE = re.compile(r"</table\s*>", re.I)

# Link destination: <anything> or a run without spaces that may contain balanced parentheses,
# because spec file names look like 7820ZXXXXG000_E_(Warning)_260220.docx
_DEST = r"\(\s*(?:<([^>\n]+)>|((?:[^()\s]|\([^()\s]*\))+))(?:\s+\"[^\"]*\")?\s*\)"
MD_LINK_RE = re.compile(r"(?<!!)\[(?:[^\[\]]|\[[^\]]*\])*\]" + _DEST)
HTML_LINK_RE = re.compile(r"<a\b[^>]*?\bhref\s*=\s*[\"']([^\"']+)[\"']", re.I)
REF_DEF_RE = re.compile(r"^\s{0,3}\[(?!\^)([^\]]+)\]:\s*<?(\S+?)>?(?:\s+.*)?$")

MD_IMG_RE = re.compile(r"!\[[^\]]*\]" + _DEST)
HTML_IMG_RE = re.compile(r"<img\b[^>]*?\bsrc\s*=\s*[\"']([^\"']+)[\"']", re.I)
WIKI_IMG_RE = re.compile(r"!\[\[([^\]|#]+)")

PIPE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")
GRID_BORDER_RE = re.compile(r"^\s*\+([-=:]+\+)+\s*$")

NUMBER_RE = re.compile(r"^((?:[A-Z]|\d+)(?:\.\d+)*)\.?\s+(?=\S)")
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".emf", ".wmf", ".tif", ".tiff", ".webp"}


@dataclass
class Heading:
    index: int
    level: int
    raw: str
    title: str
    line: int  # 1-based line of the heading itself
    number: str | None
    anchors: list[str] = field(default_factory=list)
    parent: int | None = None
    children: list[int] = field(default_factory=list)
    body_end: int = 0  # 1-based exclusive: first line of the next heading of any level
    end: int = 0  # 1-based exclusive: first line of the next heading of same or higher level
    own_chars: int = 0
    subtree_chars: int = 0


@dataclass
class Link:
    line: int
    target: str
    kind: str  # internal | cross_file | external | other
    file_part: str | None
    anchor: str | None
    heading: int | None


@dataclass
class Image:
    line: int
    target: str
    heading: int | None


@dataclass
class AnchorDef:
    anchor: str
    line: int
    syntax: str  # "attribute" or "html:<tag>"
    placement: str  # heading | before_heading | after_heading | table | standalone | inline
    heading: int | None  # owning heading index (None = before first heading)


@dataclass
class Document:
    path: Path
    text: str
    line_count: int
    total_chars: int
    headings: list[Heading]
    anchors: dict[str, int | None]  # explicit anchor id -> heading index (None = before first heading)
    implicit_anchors: dict[str, int]  # heading-text slugs -> heading index (never shadow explicit ones)
    anchor_defs: list[AnchorDef]
    links: list[Link]
    images: list[Image]
    tables: dict[str, int]
    setext_suspects: int
    preamble_chars: int  # text before the first heading

    @property
    def roots(self) -> list[Heading]:
        return [h for h in self.headings if h.parent is None]

    def resolve(self, anchor: str | None) -> tuple[bool, int | None]:
        """(found, heading index) for an internal anchor, explicit anchors first."""
        if anchor in self.anchors:
            return True, self.anchors[anchor]
        if anchor in self.implicit_anchors:
            return True, self.implicit_anchors[anchor]
        return False, None


def _dest(match: str | tuple[str, ...]) -> str:
    return match if isinstance(match, str) else next((g for g in match if g), "")


def clean_title(raw: str) -> str:
    text = re.sub(r"\[\]\{[^}]*\}", "", raw)
    text = ATTR_ID_RE.sub("", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[*`]+", "", text)
    text = re.sub(r"(?<!\w)_{1,2}([^_]+?)_{1,2}(?!\w)", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def pandoc_slug(text: str) -> str:
    """pandoc auto_identifiers: keep alnum/_/-/., words joined by '-', drop everything before the first letter."""
    kept = "".join(c for c in text.lower() if c.isalnum() or c in "_-. " or c.isspace())
    slug = "-".join(kept.split())
    return re.sub(r"^[^a-z]+", "", slug) or "section"


def github_slug(text: str) -> str:
    """GitHub style: lowercase, drop punctuation except - and _, each space becomes '-'."""
    return re.sub(r"[^\w\- ]", "", text.lower().strip()).replace(" ", "-")


def _implicit_anchors(headings: list[Heading], explicit: dict[str, int | None]) -> dict[str, int]:
    implicit: dict[str, int] = {}
    variants = (
        lambda h: pandoc_slug(h.title),
        lambda h: github_slug(h.title),
        lambda h: github_slug(NUMBER_RE.sub("", h.title)),
    )
    for make in variants:
        seen: Counter[str] = Counter()
        for h in headings:
            base = make(h)
            slug = base if not seen[base] else f"{base}-{seen[base]}"  # duplicates get -1, -2, …
            seen[base] += 1
            if slug and slug not in explicit and slug not in implicit:
                implicit[slug] = h.index
    return implicit


def classify_link(target: str) -> tuple[str, str | None, str | None]:
    target = target.strip()
    if target.startswith("#"):
        return "internal", None, unquote(target[1:]) or None
    if target.lower().startswith("file:"):
        target = re.sub(r"^file:/*", "", target, flags=re.I)
    elif re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) and not re.match(r"^[a-z]:[\\/]", target, re.I):
        return ("external" if target.lower().startswith(("http", "mailto", "ftp")) else "other"), None, None
    file_part, _, anchor = target.partition("#")
    file_part = unquote(file_part)
    if Path(file_part).suffix.lower() in IMAGE_EXT:
        return "other", file_part, None
    return "cross_file", file_part, unquote(anchor) or None


def parse_file(path: Path) -> Document:
    text = path.read_text(encoding="utf-8-sig", errors="replace")  # BOM-safe (Windows)
    lines = text.splitlines()

    headings: list[Heading] = []
    raw_defs: list[tuple[str, int, str, bool]] = []  # anchor, line, syntax, inside a table
    links: list[Link] = []
    images: list[Image] = []
    tables = {"pipe": 0, "grid": 0, "html": 0}
    setext_suspects = 0

    in_fence: str | None = None  # opening fence run, e.g. "```"
    prev_grid = False
    table_depth = 0
    current: int | None = None

    for i, line in enumerate(lines, start=1):
        fence = FENCE_RE.match(line)
        if in_fence is None:
            if fence:
                in_fence = fence.group(1)
                continue
        else:
            run = fence.group(1) if fence else ""
            if run[:1] == in_fence[0] and len(run) >= len(in_fence) and not fence.group(2).strip():
                in_fence = None
            continue

        m = ATX_RE.match(line)
        if m:
            raw = ATX_CLOSE_RE.sub("", (m.group(2) or "").strip())
            title = clean_title(raw)
            num = NUMBER_RE.match(title)
            current = len(headings)
            headings.append(Heading(
                index=current, level=len(m.group(1)), raw=raw, title=title, line=i,
                number=num.group(1) if num else None,
            ))
        elif SETEXT_RE.match(line) and i > 1 and lines[i - 2].strip() and not PIPE_SEP_RE.match(line):
            setext_suspects += 1

        in_table = table_depth > 0 or line.lstrip().startswith("|")
        for a in ATTR_ID_RE.findall(line):
            raw_defs.append((a, i, "attribute", in_table))
        for tag, a in HTML_ID_RE.findall(line):
            raw_defs.append((a, i, f"html:{tag.lower()}", in_table))
        table_depth = max(0, table_depth + len(TABLE_OPEN_RE.findall(line)) - len(TABLE_CLOSE_RE.findall(line)))

        for rx in (MD_LINK_RE, HTML_LINK_RE):
            for target in map(_dest, rx.findall(line)):
                kind, file_part, anchor = classify_link(target)
                links.append(Link(i, target, kind, file_part, anchor, current))
        ref = REF_DEF_RE.match(line)
        if ref:
            kind, file_part, anchor = classify_link(ref.group(2))
            links.append(Link(i, ref.group(2), kind, file_part, anchor, current))

        for rx in (MD_IMG_RE, HTML_IMG_RE, WIKI_IMG_RE):
            for target in map(_dest, rx.findall(line)):
                images.append(Image(i, unquote(target.strip()), current))

        if PIPE_SEP_RE.match(line):
            tables["pipe"] += 1
        is_grid = bool(GRID_BORDER_RE.match(line))
        if is_grid and not prev_grid:
            tables["grid"] += 1
        prev_grid = is_grid or (prev_grid and line.lstrip().startswith("|"))
        tables["html"] += len(TABLE_OPEN_RE.findall(line))

    _build_tree(headings, lines)
    anchor_defs = _place_anchors(raw_defs, headings, lines)
    anchors: dict[str, int | None] = {}
    for d in anchor_defs:
        anchors.setdefault(d.anchor, d.heading)
        if d.placement in ("heading", "before_heading", "after_heading") and d.heading is not None:
            owner = headings[d.heading]
            if d.anchor not in owner.anchors:
                owner.anchors.append(d.anchor)
    first = headings[0].line if headings else len(lines) + 1
    preamble_chars = sum(len(l) + 1 for l in lines[:first - 1])
    return Document(
        path=path, text=text, line_count=len(lines), total_chars=len(text), headings=headings,
        anchors=anchors, implicit_anchors=_implicit_anchors(headings, anchors), anchor_defs=anchor_defs,
        links=links, images=images,
        tables=tables, setext_suspects=setext_suspects, preamble_chars=preamble_chars,
    )


def _place_anchors(raw_defs: list[tuple[str, int, str, bool]], headings: list[Heading],
                   lines: list[str]) -> list[AnchorDef]:
    heading_at = {h.line: h.index for h in headings}
    heading_lines = [h.line for h in headings]

    def section_of(ln: int) -> int | None:
        k = bisect.bisect_right(heading_lines, ln) - 1
        return headings[k].index if k >= 0 else None

    def neighbour(ln: int, step: int) -> int | None:
        """Nearest line in direction `step` that is neither blank nor anchor-only."""
        j = ln + step
        while 1 <= j <= len(lines):
            if lines[j - 1].strip() and not ANCHOR_ONLY_RE.match(lines[j - 1]):
                return j
            j += step
        return None

    out = []
    for anchor, ln, syntax, in_table in raw_defs:
        if ln in heading_at:
            placement, owner = "heading", heading_at[ln]
        elif in_table:
            placement, owner = "table", section_of(ln)
        elif ANCHOR_ONLY_RE.match(lines[ln - 1]):
            nxt, prev = neighbour(ln, 1), neighbour(ln, -1)
            if nxt in heading_at:
                placement, owner = "before_heading", heading_at[nxt]
            elif prev in heading_at:
                placement, owner = "after_heading", heading_at[prev]
            else:
                placement, owner = "standalone", section_of(ln)
        else:
            placement, owner = "inline", section_of(ln)
        out.append(AnchorDef(anchor, ln, syntax, placement, owner))
    return out


def _build_tree(headings: list[Heading], lines: list[str]) -> None:
    line_chars = [0]
    for line in lines:
        line_chars.append(line_chars[-1] + len(line) + 1)

    def chars(start: int, end: int) -> int:  # 1-based, end exclusive
        return line_chars[end - 1] - line_chars[start - 1]

    stack: list[Heading] = []
    total = len(lines) + 1
    for n, h in enumerate(headings):
        while stack and stack[-1].level >= h.level:
            stack.pop()
        if stack:
            h.parent = stack[-1].index
            stack[-1].children.append(h.index)
        stack.append(h)
        h.body_end = headings[n + 1].line if n + 1 < len(headings) else total
        h.own_chars = chars(h.line + 1, h.body_end)

    for n, h in enumerate(headings):
        end = total
        for later in headings[n + 1:]:
            if later.level <= h.level:
                end = later.line
                break
        h.end = end
        h.subtree_chars = chars(h.line, end)
