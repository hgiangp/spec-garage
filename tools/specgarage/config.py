"""Locate the repo root and read the spec registry (specs.yaml)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REGISTRY = "specs.yaml"
DATA_DIR = "data"  # local-only data repo; ignored by the public repo


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
    """Compare spec names loosely: case, spaces, dots and quotes do not matter ("NAVIG." == "navig")."""
    return re.sub(r"[\s.\"'“”‘’_-]+", "", name).casefold()


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
        if (p / REGISTRY).is_file():
            return p
    raise SystemExit(f"{REGISTRY} not found in {here} or any parent. Run inside the spec-garage repo.")


def load_specs(root: Path) -> list[Spec]:
    data = yaml.safe_load((root / REGISTRY).read_text(encoding="utf-8")) or {}
    specs = []
    for s in data.get("specs") or []:
        specs.append(Spec(
            code=s["code"],
            doc_no=s.get("doc_no", ""),
            title=s.get("title", ""),
            date=str(s.get("date", "")),
            source=root / s["source"],
            images=root / s["images"] if s.get("images") else None,
            aliases=[str(a) for a in s.get("aliases") or []],
        ))
    return specs
