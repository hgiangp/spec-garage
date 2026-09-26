"""`sg find`: where a term (signal, data name, parameter) appears in the vault, by section ID.

Cross-spec references in these specs are plain text (no links, see phase0-findings F5), so skills
look terms up by name. Grep finds lines; this maps each hit to the smallest section holding it and
says whether it is a heading, a table cell or prose, which is what a skill needs to pick the
defining place.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import Spec, load_specs, lookup_spec
from .vault import SpecVault, VaultError, load_spec_vault, vault_dir

KINDS = ("heading", "table", "text")  # also the sort order: definitions tend to be headings, then tables
HEADING_RE = re.compile(r"^#{1,6}\s")
SNIPPET = 160


@dataclass
class Hit:
    id: str  # smallest section holding the line
    note: str
    spec: str
    path: str
    line: int  # file line, 1-based
    kind: str
    breadcrumb: list[str]
    snippet: str
    matches: list[str]  # the matched text on the line, as written there


HYPHENS = "-‐‑‒–"  # Word output uses non-breaking hyphens in "Table 1‑3"


def term_pattern(term: str, case_sensitive: bool = False, word: bool = True) -> re.Pattern:
    """Whole-word by default, so "FOO operation" does not match "XFOO operation".

    Any run of spaces matches any whitespace, and any hyphen matches the typographic ones.
    A term starting with a digit is not matched after a dot either, so "3.2." finds heading
    3.2 and not 1.3.2.
    """
    term = term.strip()
    body = "".join(rf"\s+" if c.isspace() else f"[{HYPHENS}]" if c in HYPHENS else re.escape(c)
                   for c in re.sub(r"\s+", " ", term))
    if word:
        before = r"[\w.]" if term[:1].isdigit() else r"\w"
        body = rf"(?<!{before}){body}(?!\w)"
    return re.compile(body, 0 if case_sensitive else re.IGNORECASE)


def _clean(line: str) -> str:
    text = re.sub(r"<[^>]+>", " ", line)
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= SNIPPET else text[:SNIPPET - 1] + "…"


def find_in_vault(vault: SpecVault, pattern: re.Pattern, include_preamble: bool = False) -> list[Hit]:
    hits: list[Hit] = []
    for note in vault.notes.values():
        if note.id == vault.preamble and not include_preamble:
            continue  # the table of contents repeats every heading
        in_table = False
        for n, line in enumerate(note.body.splitlines(), start=1):
            low = line.lower()
            if "<table" in low:
                in_table = True
            if line.startswith("<!-- id:") or not pattern.search(line):
                if "</table>" in low:
                    in_table = False
                continue
            if HEADING_RE.match(line):
                kind = "heading"
            elif in_table or line.lstrip().startswith("|"):
                kind = "table"
            else:
                kind = "text"
            if "</table>" in low:
                in_table = False
            s = vault.section_at(note.id, n)
            hits.append(Hit(s.id, note.id, vault.code, note.rel, n + note.offset, kind,
                            vault.breadcrumb(s), _clean(line), pattern.findall(line)))
    return hits


def resolve_codes(root: Path, names: list[str] | None) -> list[str]:
    """Spec codes to search: the names given (code, title or alias), or every spec with a vault."""
    specs: list[Spec] = load_specs(root)
    if not names:
        return [s.code for s in specs if vault_dir(root, s.code).is_dir()]
    codes = []
    for name in names:
        s = lookup_spec(specs, name)
        if s is None:
            raise VaultError(f"{name!r} is not a spec in specs.yaml (code, title or aliases)")
        codes.append(s.code)
    return codes


def find(root: Path, term: str, specs: list[str] | None = None, kinds: list[str] | None = None,
         case_sensitive: bool = False, word: bool = True, include_preamble: bool = False) -> list[Hit]:
    if not term.strip():
        raise VaultError("empty search term")
    return _search(root, term_pattern(term, case_sensitive, word), specs, kinds, include_preamble)


def near_misses(root: Path, term: str, specs: list[str] | None = None, kinds: list[str] | None = None,
                case_sensitive: bool = False, include_preamble: bool = False) -> Counter[str]:
    """Longer names holding the term, with their hit counts, for a whole-word search that found nothing.

    "_" is a word character, so "R_FOO" does not match "R_FOO_UP" (a different signal). Without this,
    "0 hits" reads the same whether the term is absent or only part of longer names.
    """
    if not term.strip():
        raise VaultError("empty search term")
    inner = term_pattern(term, case_sensitive, word=False)
    before = r"[\w.]*" if term.strip()[:1].isdigit() else r"\w*"  # same guards as term_pattern
    pattern = re.compile(rf"{before}(?:{inner.pattern})\w*", inner.flags)
    counts: Counter[str] = Counter()
    for h in _search(root, pattern, specs, kinds, include_preamble):
        counts.update(h.matches)
    return counts


def _search(root: Path, pattern: re.Pattern, specs: list[str] | None, kinds: list[str] | None,
            include_preamble: bool) -> list[Hit]:
    hits: list[Hit] = []
    for code in resolve_codes(root, specs):
        hits.extend(find_in_vault(load_spec_vault(root, code), pattern, include_preamble))
    if kinds:
        hits = [h for h in hits if h.kind in kinds]
    return sorted(hits, key=lambda h: (KINDS.index(h.kind), h.spec, h.path, h.line))


def to_dicts(hits: list[Hit]) -> list[dict]:
    return [asdict(h) for h in hits]
