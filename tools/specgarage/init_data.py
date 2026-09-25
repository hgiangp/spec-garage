"""`sg init-data`: create the local data workspace (data/) on the data machine.

data/ is its own git repo and is ignored by the public repo. Existing files are never overwritten.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from .config import DATA_DIR, REGISTRY, load_specs, registry_path

TEMPLATE = Path(__file__).parent / "data_template"
LEGACY_DIRS = ("sources", "vault", "reports", "evals")
# Before T9 the registry sat at the repo root with paths relative to it (data/sources/…).
LEGACY_PATH_RE = re.compile(r"^(\s*(?:source|images):\s*[\"']?)data/", re.M)


def migrate_registry(root: Path) -> list[str]:
    """Move <root>/specs.yaml to data/specs.yaml, making its paths relative to data/.

    Line-based rather than a YAML round trip, so the comments in the registry survive.
    """
    legacy, target = root / REGISTRY, registry_path(root)
    if not legacy.is_file():
        return []
    if target.exists():
        return [f"skipped (exists): {target.relative_to(root)}; remove {REGISTRY} at the root by hand"]
    text = LEGACY_PATH_RE.sub(r"\1", legacy.read_text(encoding="utf-8"))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    legacy.unlink()
    return [f"moved: {REGISTRY} -> {target.relative_to(root)} (paths now relative to {DATA_DIR}/)"]


def _has_files(p: Path) -> bool:
    return p.is_dir() and any(f.is_file() and f.name != ".gitkeep" for f in p.rglob("*"))


def migrate_legacy(root: Path, data: Path) -> list[str]:
    """Move content from the first-scaffold locations (root/sources, …) into data/."""
    log = []
    for name in LEGACY_DIRS:
        legacy = root / name
        if not legacy.is_dir():
            continue
        # File by file, so an existing (e.g. empty) target directory is merged into, not skipped.
        for f in sorted(p for p in legacy.rglob("*") if p.is_file() and p.name != ".gitkeep"):
            target = data / name / f.relative_to(legacy)
            if target.exists():
                log.append(f"skipped (exists): {target.relative_to(root)}")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), str(target))
            log.append(f"moved: {f.relative_to(root)} -> {target.relative_to(root)}")
        if not _has_files(legacy):
            shutil.rmtree(legacy)
    return log


def init_data(root: Path, migrate: bool = False, git: bool = True) -> list[str]:
    data = root / DATA_DIR
    data.mkdir(exist_ok=True)
    log: list[str] = []

    legacy = [f"{n}/" for n in LEGACY_DIRS if _has_files(root / n)]
    if (root / REGISTRY).is_file():
        legacy.append(REGISTRY)
    if legacy and migrate:
        log += migrate_legacy(root, data)
        log += migrate_registry(root)
    elif legacy:
        log.append(f"WARNING: data found in legacy locations: {', '.join(legacy)}. "
                   "Re-run with --migrate-legacy to move it into data/.")

    for src in sorted(TEMPLATE.rglob("*")):
        if src.is_dir() or "__pycache__" in src.parts:
            continue
        dst = data / src.relative_to(TEMPLATE)
        if dst.exists():
            continue
        if dst == registry_path(root) and (root / REGISTRY).is_file():
            continue  # an empty registry here would hide the legacy one that is not migrated yet
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        log.append(f"created: {dst.relative_to(root)}")

    specs = load_specs(root) if registry_path(root).is_file() else []
    for d in [data / "vault" / "attachments", *(data / "sources" / s.code for s in specs)]:
        if not d.exists():
            d.mkdir(parents=True)
            log.append(f"created: {d.relative_to(root)}/")

    if git and not (data / ".git").exists():
        subprocess.run(["git", "init", "-q", str(data)], check=True)
        log.append(f"initialised local git repo: {data.relative_to(root)}/.git (no remote)")
    return log
