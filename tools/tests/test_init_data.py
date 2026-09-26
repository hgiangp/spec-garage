from pathlib import Path

import pytest

from specgarage.config import load_specs
from specgarage.init_data import init_data

REGISTRY = """specs:
  - code: WRN
    source: sources/WRN/w.md
"""
# Before T9 the registry sat at the repo root, with paths relative to it.
LEGACY_REGISTRY = """# keep this comment
specs:
  - code: WRN
    source: data/sources/WRN/w.md
    images: "data/sources/WRN/images"
"""


def make_root(tmp_path: Path) -> Path:
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "specs.yaml").write_text(REGISTRY, encoding="utf-8")
    return tmp_path


def test_creates_workspace_without_overwriting(tmp_path):
    root = make_root(tmp_path)
    init_data(root, git=False)
    data = root / "data"
    for p in ("README.md", ".gitignore", "vault/.obsidian/app.json", "knowledge/glossary.md",
              "knowledge/lessons.md", "reports/README.md", "evals/README.md"):
        assert (data / p).is_file(), p
    assert (data / "sources" / "WRN").is_dir()
    assert (data / "vault" / "attachments").is_dir()
    assert (data / "specs.yaml").read_text(encoding="utf-8") == REGISTRY  # the registry is data: kept

    (data / "knowledge" / "glossary.md").write_text("edited", encoding="utf-8")
    init_data(root, git=False)
    assert (data / "knowledge" / "glossary.md").read_text(encoding="utf-8") == "edited"


def test_fresh_workspace_gets_an_empty_registry(tmp_path):
    init_data(tmp_path, git=False)
    assert (tmp_path / "data" / "specs.yaml").is_file()
    assert load_specs(tmp_path) == []


def test_legacy_warning_and_migration(tmp_path):
    root = make_root(tmp_path)
    legacy = root / "sources" / "WRN"
    legacy.mkdir(parents=True)
    (legacy / "w.md").write_text("# spec", encoding="utf-8")
    (root / "reports").mkdir()
    (root / "reports" / "profile.txt").write_text("stats", encoding="utf-8")

    log = init_data(root, git=False)
    assert any("WARNING" in line for line in log)
    assert (legacy / "w.md").exists()

    init_data(root, migrate=True, git=False)
    assert (root / "data" / "sources" / "WRN" / "w.md").read_text(encoding="utf-8") == "# spec"
    assert (root / "data" / "reports" / "profile.txt").exists()
    assert not (root / "sources").exists() and not (root / "reports").exists()


def test_legacy_registry_is_moved_into_data(tmp_path):
    (tmp_path / "specs.yaml").write_text(LEGACY_REGISTRY, encoding="utf-8")
    with pytest.raises(SystemExit, match="--migrate-legacy"):
        load_specs(tmp_path)  # never silently read an empty registry while the real one is elsewhere

    log = init_data(tmp_path, git=False)
    assert any("WARNING" in line and "specs.yaml" in line for line in log)
    assert not (tmp_path / "data" / "specs.yaml").exists()  # no empty template hiding the legacy one

    init_data(tmp_path, migrate=True, git=False)
    assert not (tmp_path / "specs.yaml").exists()
    text = (tmp_path / "data" / "specs.yaml").read_text(encoding="utf-8")
    assert text.startswith("# keep this comment") and "data/" not in text
    [spec] = load_specs(tmp_path)
    assert spec.source == tmp_path / "data" / "sources" / "WRN" / "w.md"
    assert spec.images == tmp_path / "data" / "sources" / "WRN" / "images"


def test_git_init(tmp_path):
    root = make_root(tmp_path)
    init_data(root)
    assert (root / "data" / ".git").is_dir()
