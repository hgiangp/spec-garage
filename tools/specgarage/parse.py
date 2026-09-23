"""Parse a Word-converted spec markdown file into a heading tree plus anchors, links, images and tables.

The converter output format is not fixed yet, so anchors and links are recognised in the common
forms produced by pandoc and similar tools:

- pandoc attributes:   ``# Title {#_Toc123}``, ``[]{#_Ref456 .anchor}``
- HTML anchors:        ``<a id="_Ref456"></a>``, ``<a name="...">``, ``<span id="...">``
- markdown links:      ``[text](#_Ref456)``, ``[text](Other.docx#_Ref789)``, reference definitions
- HTML links:          ``<a href="#_Ref456">``
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote

FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})(.*)$")
ATX_RE = re.compile(r"^\s{0,3}(#{1,6})(?:[ \t]+(.*))?$")
ATX_CLOSE_RE = re.compile(r"(?:^|[ \t]+)#+[ \t]*$")
SETEXT_RE = re.compile(r"^\s{0,3}(=+|-+)\s*$")

ATTR_ID_RE = re.compile(r"\{[^{}\n]*?#([A-Za-z_][\w.:-]*)[^{}\n]*\}")
HTML_ID_RE = re.compile(r"<(?:a|span|div)\b[^>]*?\b(?:id|name)\s*=\s*[\"']([^\"']+)[\"']", re.I)

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
HTML_TABLE_RE = re.compile(r"<table\b", re.I)

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
class Document:
    path: Path
    line_count: int
    total_chars: int
    headings: list[Heading]
    anchors: dict[str, int | None]  # anchor id -> heading index (None = before first heading)
    anchor_syntax: dict[str, int]
    links: list[Link]
    images: list[Image]
    tables: dict[str, int]
    setext_suspects: int
    preamble_chars: int  # text before the first heading

    @property
    def roots(self) -> list[Heading]:
        return [h for h in self.headings if h.parent is None]


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
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    headings: list[Heading] = []
    anchors: dict[str, int | None] = {}
    anchor_syntax = {"attribute": 0, "html": 0}
    links: list[Link] = []
    images: list[Image] = []
    tables = {"pipe": 0, "grid": 0, "html": 0}
    setext_suspects = 0

    in_fence: str | None = None  # opening fence run, e.g. "```"
    prev_grid = False
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

        for rx, kind in ((ATTR_ID_RE, "attribute"), (HTML_ID_RE, "html")):
            for a in rx.findall(line):
                anchor_syntax[kind] += 1
                anchors.setdefault(a, current)
                if m and current is not None and a not in headings[current].anchors:
                    headings[current].anchors.append(a)

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
        tables["html"] += len(HTML_TABLE_RE.findall(line))

    _build_tree(headings, lines)
    first = headings[0].line if headings else len(lines) + 1
    preamble_chars = sum(len(l) + 1 for l in lines[:first - 1])
    return Document(
        path=path, line_count=len(lines), total_chars=len(text), headings=headings,
        anchors=anchors, anchor_syntax=anchor_syntax, links=links, images=images,
        tables=tables, setext_suspects=setext_suspects, preamble_chars=preamble_chars,
    )


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
