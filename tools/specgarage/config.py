"""Locate the repo root and read the spec registry (specs.yaml)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

REGISTRY = "specs.yaml"


@dataclass
class Spec:
    code: str
    doc_no: str
    title: str
    date: str
    source: Path
    images: Path | None


def find_root(start: Path | None = None) -> Path:
    here = (start or Path.cwd()).resolve()
    for p in (here, *here.parents):
        if (p / REGISTRY).is_file():
            return p
    raise SystemExit(f"Không tìm thấy {REGISTRY} từ {here} trở lên. Hãy chạy trong repo spec-garage.")


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
        ))
    return specs
