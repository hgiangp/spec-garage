"""`sg add-spec`: put a converted spec in place and register it, without touching the code repo.

Input is what the converter produces: a folder holding one ``<doc_no>_<lang>_(<title>)_<yymmdd>.md``
and its ``images/``, or the .md alone when it has no images. The folder becomes
``data/sources/<CODE>/`` (moved when it already sits under data/sources/, copied from anywhere
else) and an entry is appended to ``data/specs.yaml``. doc_no, lang, title and date come from
the file name. The code is the one thing a person must choose, because it is the permanent
prefix of every section ID.

Appending text rather than dumping YAML keeps the comments in the registry.
"""

from __future__ import annotations

import json
import re
import shutil
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from .config import DATA_DIR, load_specs, lookup_spec, registry_path
from .ids import CODE_RE
from .init_data import TEMPLATE
from .parse import parse_file

FILE_NAME_RE = re.compile(r"^(?P<doc_no>[0-9A-Z]+)_(?P<lang>[A-Z]+)_\((?P<title>[^()]+)\)_(?P<date>\d{6})$")
EMPTY_LIST_RE = re.compile(r"^specs:[ \t]*\[\][ \t]*$", re.M)


class AddSpecError(ValueError):
    pass


@dataclass
class NameParts:
    doc_no: str
    lang: str
    title: str
    date: str  # ISO, 2026-02-20


def parse_file_name(stem: str) -> NameParts | None:
    m = FILE_NAME_RE.match(stem)
    if not m:
        return None
    d = m["date"]
    return NameParts(m["doc_no"], m["lang"], m["title"].strip(), f"20{d[:2]}-{d[2:4]}-{d[4:]}")


def find_source(path: Path) -> tuple[Path, Path | None]:
    """(the .md, the folder that moves with it or None when only the file moves)."""
    if path.is_file():
        if path.suffix.lower() != ".md":
            raise AddSpecError(f"{path} is not a .md file")
        return path, None
    if path.is_dir():
        mds = sorted(p for p in path.glob("*.md") if p.is_file())
        if len(mds) != 1:
            raise AddSpecError(f"{path} must hold exactly one .md file, found {len(mds)}")
        return mds[0], path
    raise AddSpecError(f"{path} does not exist")


def local_images(md: Path) -> list[str]:
    """Image targets that are files next to the spec (not URLs), as written in the source."""
    return [i.target for i in parse_file(md).images
            if not re.match(r"^[a-z][a-z0-9+.-]*:", i.target, re.I)]


def registry_entry(code: str, parts: NameParts, aliases: list[str], source: str, images: str | None) -> str:
    q = json.dumps  # a JSON string is a valid YAML scalar, whatever the title holds
    return (f"\n  - code: {code}\n"
            f"    doc_no: {q(parts.doc_no)}\n"
            f"    lang: {q(parts.lang)}\n"
            f"    title: {q(parts.title)}\n"
            f"    aliases: [{', '.join(q(a) for a in aliases)}]\n"
            f"    date: {parts.date}\n"
            f"    source: {q(source)}\n"
            f"    images: {q(images) if images else 'null'}\n")


def add_spec(root: Path, path: Path, code: str, title: str | None = None, doc_no: str | None = None,
             date: str | None = None, aliases: list[str] | None = None,
             dry_run: bool = False) -> Iterator[str]:
    data = root / DATA_DIR
    if not data.is_dir():
        raise AddSpecError(f"{data} does not exist. Run `sg init-data` first.")
    if not CODE_RE.match(code):
        raise AddSpecError(f"code {code!r} must be 2 to 5 capital letters (it prefixes every section ID)")

    md, folder = find_source(path.resolve())
    parts = parse_file_name(md.stem) or NameParts("", "", "", "")
    parts.doc_no, parts.title, parts.date = doc_no or parts.doc_no, title or parts.title, date or parts.date
    if not (parts.doc_no and parts.title and parts.date):
        raise AddSpecError(f"{md.name} does not follow <doc_no>_<lang>_(<title>)_<yymmdd>.md; "
                           f"pass --doc-no, --title and --date")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", parts.date):
        raise AddSpecError(f"date {parts.date!r} must be YYYY-MM-DD")
    aliases = [a for a in aliases or [] if a.strip()]

    specs = load_specs(root)
    if any(s.code == code for s in specs):
        raise AddSpecError(f"{code} is already registered. A code is permanent; pick another one.")
    same_doc = [s.code for s in specs if s.doc_no and s.doc_no == parts.doc_no]
    if same_doc:
        raise AddSpecError(f"doc_no {parts.doc_no} is already registered as {same_doc[0]}: this looks like "
                           f"a new revision, which add-spec does not handle (the vault would need a merge, "
                           f"not a new code)")
    for name in (parts.title, *aliases):
        other = lookup_spec(specs, name)
        if other:
            raise AddSpecError(f"name {name!r} already refers to {other.code} ({other.title})")

    dest = data / "sources" / code
    if dest.exists() and any(dest.iterdir()):
        raise AddSpecError(f"{dest} already exists and is not empty")

    # Images must travel with the spec, or build-vault will not find them afterwards.
    images = local_images(md)
    if folder is None and images:
        raise AddSpecError(f"{md.name} links {len(images)} image(s): pass the folder that holds the .md "
                           f"and its images, not the .md alone")
    escaping = [t for t in images if not (folder / t).resolve().is_relative_to(folder.resolve())]
    if escaping:
        raise AddSpecError(f"{len(escaping)} image link(s) point outside {folder.name}, e.g. {escaping[0]!r}: "
                           f"they would break after the move")
    missing = sorted({t for t in images if not (folder / t).is_file()})

    inside = (data / "sources").resolve()
    move = (folder or md).resolve().is_relative_to(inside)
    verb = "move" if move else "copy"
    has_images = folder is not None and (folder / "images").is_dir()
    source_rel = f"sources/{code}/{md.name}"
    images_rel = f"sources/{code}/images" if has_images else None

    yield (f"{code}: {parts.title} (doc_no {parts.doc_no}, lang {parts.lang or '-'}, date {parts.date})")
    yield f"  {verb} {(folder or md)} -> {dest}"
    yield f"  register in {registry_path(root).relative_to(root).as_posix()}: source {source_rel}" + \
          (f", images {images_rel}" if images_rel else "")
    for t in missing[:5]:
        yield f"  WARNING {code}: missing image {t}"
    if len(missing) > 5:
        yield f"  WARNING {code}: … {len(missing) - 5} more missing images"
    if dry_run:
        yield "dry run: nothing moved or written"
        return

    if dest.exists():
        dest.rmdir()  # empty, checked above
    dest.parent.mkdir(parents=True, exist_ok=True)
    if folder is not None:
        (shutil.move if move else shutil.copytree)(str(folder), str(dest))
    else:
        dest.mkdir()
        (shutil.move if move else shutil.copy2)(str(md), str(dest / md.name))

    reg = registry_path(root)
    text = reg.read_text(encoding="utf-8") if reg.is_file() else (TEMPLATE / "specs.yaml").read_text(encoding="utf-8")
    text = EMPTY_LIST_RE.sub("specs:", text)
    reg.write_text(text.rstrip("\n") + "\n" + registry_entry(code, parts, aliases, source_rel, images_rel),
                   encoding="utf-8")
    if not any(s.code == code and s.source.is_file() for s in load_specs(root)):
        raise AddSpecError(f"{reg} was written but {code} does not read back; check the file by hand")
    yield f"registered {code}. next: sg build-vault {code}, or run add-spec with --build"
