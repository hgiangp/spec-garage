"""Export a vault back to one markdown file per spec (T5), and check the round trip.

The build (T2-lite) changes a spec in exactly two reversible ways, so export only has to undo
those two and concatenate the notes in manifest order:

- it inserts an ``<!-- id: ... -->`` line under every sub-heading  -> dropped (``--keep-ids`` keeps them)
- it points image links at ``../attachments/<CODE>/<file>``       -> restored to the source path

Blank lines at the end of each note are not kept by the build, so the round trip is exact up to
blank lines: ``--check`` compares the non-blank lines of the export with those of the source.
Links are verbatim in a vault that has not been relinked; exporting a relinked vault (T2b) is
not supported yet.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from .build_vault import HTML_IMAGE_RE, MD_IMAGE_RE
from .config import DATA_DIR, load_specs
from .ids import IdError, load_manifest, manifest_path

EXPORT_DIR = Path("build") / "export"
ID_LINE_RE = re.compile(r"^<!-- id: [A-Z]{2,5}-\d{4,5}(?: \| [^\n]*)? -->$")
ATTACHMENT_RE = re.compile(r"^\.\./attachments/[^/]+/(?P<name>[^/]+)$")


class ExportError(RuntimeError):
    pass


@dataclass
class Exported:
    code: str
    path: Path | None
    notes: int
    lines: int
    warnings: list[str] = field(default_factory=list)
    mismatch: list[str] = field(default_factory=list)  # filled by --check


def split_note(text: str, path: Path) -> str:
    """Body of a note file, without its YAML frontmatter."""
    if not text.startswith("---\n"):
        raise ExportError(f"{path}: no frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ExportError(f"{path}: frontmatter is not closed")
    return text[end + 5:]


def source_image_dests(source_text: str) -> dict[str, str]:
    """Image file name -> the destination exactly as written in the source, e.g. images/media/x.png."""
    dests: dict[str, str] = {}
    for rx in (MD_IMAGE_RE, HTML_IMAGE_RE):
        for m in rx.finditer(source_text):
            raw = m.group(2)
            bare = raw[1:-1] if raw.startswith("<") and raw.endswith(">") else raw
            dests.setdefault(Path(bare).name, raw)
    return dests


def restore_image_paths(text: str, dests: dict[str, str], warnings: list[str]) -> str:
    def back(dest: str) -> str:
        m = ATTACHMENT_RE.match(dest)
        if not m:
            return dest
        original = dests.get(m.group("name"))
        if original is None:
            warnings.append(f"no source path for image {m.group('name')}; kept {dest}")
            return dest
        return original

    text = MD_IMAGE_RE.sub(lambda m: m.group(1) + back(m.group(2)) + m.group(3), text)
    return HTML_IMAGE_RE.sub(lambda m: m.group(1) + back(m.group(2)) + m.group(3), text)


def drop_id_lines(text: str) -> str:
    return "\n".join(l for l in text.split("\n") if not ID_LINE_RE.match(l))


def non_blank(text: str) -> list[str]:
    return [l.rstrip() for l in text.splitlines() if l.strip()]


def compare(exported: str, source: str, limit: int = 10) -> list[str]:
    """Differences between export and source, ignoring blank lines and trailing spaces."""
    a, b = non_blank(exported), non_blank(source)
    diffs = []
    for i, (x, y) in enumerate(zip(a, b), start=1):
        if x != y:
            diffs.append(f"non-blank line {i}: export {x[:80]!r} != source {y[:80]!r}")
            if len(diffs) >= limit:
                return diffs
    if len(a) != len(b):
        diffs.append(f"export has {len(a)} non-blank lines, source has {len(b)}")
    return diffs


def export_spec(root: Path, code: str, keep_ids: bool = False) -> tuple[str, Exported]:
    """(exported text, summary) for one spec's vault."""
    mpath = manifest_path(root, code)
    try:
        manifest = load_manifest(mpath)
    except IdError as e:
        raise ExportError(str(e)) from e

    result = Exported(code, None, 0, 0)
    source = root / manifest.source if manifest.source else None
    source_text = ""
    if source is None or not source.is_file():
        result.warnings.append(f"source {manifest.source or '(none)'} not found: image paths stay in attachments/")
    else:
        raw = source.read_bytes()
        source_text = raw.decode("utf-8-sig", errors="replace")
        if manifest.source_sha256 and hashlib.sha256(raw).hexdigest() != manifest.source_sha256:
            result.warnings.append("source changed since the vault was built (sha256 differs)")
    dests = source_image_dests(source_text)

    parts = []
    for section_id in manifest.ids():
        note = mpath.parent / f"{section_id}.md"
        if not note.is_file():
            raise ExportError(f"{code}: note {section_id} is in the manifest but {note} does not exist")
        body = split_note(note.read_text(encoding="utf-8"), note).rstrip("\n")
        if not keep_ids:
            body = drop_id_lines(body)
        parts.append(restore_image_paths(body, dests, result.warnings))

    text = "\n\n".join(parts) + "\n"
    result.notes = len(parts)
    result.lines = text.count("\n")
    return text, result


def export_vault(root: Path, codes: list[str] | None = None, keep_ids: bool = False,
                 check: bool = False, out_dir: Path | None = None) -> Iterator[Exported]:
    """Write build/export/<CODE>.md for each spec that has a vault; with check, also diff it
    against the source."""
    specs = load_specs(root)
    wanted = [s for s in specs if not codes or s.code in codes]
    if codes and not wanted:
        raise ExportError(f"no spec matches {codes}. Run `sg specs` to see the registry.")
    if not codes:
        wanted = [s for s in wanted if manifest_path(root, s.code).is_file()]
        if not wanted:
            raise ExportError(f"no vault found under {root / DATA_DIR / 'vault'}. Run `sg build-vault` first.")

    target_dir = out_dir or root / EXPORT_DIR
    for spec in wanted:
        text, result = export_spec(root, spec.code, keep_ids)
        target_dir.mkdir(parents=True, exist_ok=True)
        result.path = target_dir / f"{spec.code}.md"
        result.path.write_text(text, encoding="utf-8")
        if check:
            if keep_ids:
                raise ExportError("--check compares against the source, which has no id comments: drop --keep-ids")
            if not spec.source.is_file():
                raise ExportError(f"{spec.code}: cannot check, source not found: {spec.source}")
            result.mismatch = compare(text, spec.source.read_text(encoding="utf-8-sig", errors="replace"))
        yield result
