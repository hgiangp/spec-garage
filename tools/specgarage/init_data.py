"""`sg init-data`: create the local data workspace (data/) on the data machine.

data/ is its own git repo and is ignored by the public repo. Existing files are never overwritten.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .config import DATA_DIR, load_specs

TEMPLATE = Path(__file__).parent / "data_template"
LEGACY_DIRS = ("sources", "vault", "reports", "evals")


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
                log.append(f"bỏ qua (đã tồn tại): {target.relative_to(root)}")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), str(target))
            log.append(f"đã chuyển: {f.relative_to(root)} → {target.relative_to(root)}")
        if not _has_files(legacy):
            shutil.rmtree(legacy)
    return log


def init_data(root: Path, migrate: bool = False, git: bool = True) -> list[str]:
    data = root / DATA_DIR
    data.mkdir(exist_ok=True)
    log: list[str] = []

    legacy = [n for n in LEGACY_DIRS if _has_files(root / n)]
    if legacy and migrate:
        log += migrate_legacy(root, data)
    elif legacy:
        log.append(f"CẢNH BÁO: còn dữ liệu ở vị trí cũ: {', '.join(legacy)}/. "
                   "Chạy lại với --migrate-legacy để chuyển vào data/.")

    for src in sorted(TEMPLATE.rglob("*")):
        if src.is_dir() or "__pycache__" in src.parts:
            continue
        dst = data / src.relative_to(TEMPLATE)
        if dst.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        log.append(f"đã tạo: {dst.relative_to(root)}")

    for d in [data / "vault" / "attachments", *(data / "sources" / s.code for s in load_specs(root))]:
        if not d.exists():
            d.mkdir(parents=True)
            log.append(f"đã tạo: {d.relative_to(root)}/")

    if git and not (data / ".git").exists():
        subprocess.run(["git", "init", "-q", str(data)], check=True)
        log.append(f"đã tạo git repo local: {data.relative_to(root)}/.git (không có remote)")
    return log
