"""Locate the repo root and read the spec registry (data/specs.yaml).

The registry describes the data, not the code, so it lives in the data repo: registering a spec,
or a new revision of one, is a data commit and never touches spec-garage. Paths in it are relative
to data/.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REGISTRY = "specs.yaml"
DATA_DIR = "data"  # the data repo; ignored by the code repo
# Any of these marks the repo root. tools/pyproject.toml is always there in a checkout; the other
# two let a bare data workspace (as in the tests) or a pre-T9 layout be found too.
ROOT_MARKERS = ("tools/pyproject.toml", f"{DATA_DIR}/{REGISTRY}", REGISTRY)


@dataclass
class Spec:
    code: str
    doc_no: str
    title: str
    date: str
    source: Path
    images: Path | None
    aliases: list[str] = field(default_factory=list)

    def names(self) -> list[str]:
        """Every name another spec may use for this one: code, title and aliases."""
        return [self.code, self.title, *self.aliases]


def normalize_name(name: str) -> str:
    """Compare spec names loosely: case, spaces, dots, slashes and quotes do not matter
    ("NAVIG." == "navig", "ADAS/AD" == "ADAS AD")."""
    return re.sub(r"[\s./\"'“”‘’_-]+", "", name).casefold()


def lookup_spec(specs: list[Spec], name: str) -> Spec | None:
    """The registered spec a name refers to (code, title or alias), or None if it is not registered."""
    key = normalize_name(name)
    for s in specs:
        if any(normalize_name(n) == key for n in s.names() if n):
            return s
    return None


def find_root(start: Path | None = None) -> Path:
    here = (start or Path.cwd()).resolve()
    for p in (here, *here.parents):
        if any((p / m).is_file() for m in ROOT_MARKERS):
            return p
    raise SystemExit(f"spec-garage root not found in {here} or any parent. Run inside the spec-garage repo.")


def registry_path(root: Path) -> Path:
    return root / DATA_DIR / REGISTRY


def load_specs(root: Path) -> list[Spec]:
    path = registry_path(root)
    if not path.is_file():
        if (root / REGISTRY).is_file():
            raise SystemExit(f"{REGISTRY} is at the repo root, but the registry now lives in {DATA_DIR}/. "
                             f"Run `sg init-data --migrate-legacy` to move it.")
        return []  # a fresh data workspace: nothing registered yet
    data_dir = root / DATA_DIR
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    specs = []
    for s in data.get("specs") or []:
        specs.append(Spec(
            code=s["code"],
            doc_no=s.get("doc_no", ""),
            title=s.get("title", ""),
            date=str(s.get("date", "")),
            source=data_dir / s["source"],
            images=data_dir / s["images"] if s.get("images") else None,
            aliases=[str(a) for a in s.get("aliases") or []],
        ))
    return specs
