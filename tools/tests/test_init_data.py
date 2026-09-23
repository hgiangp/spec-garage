from pathlib import Path

from specgarage.init_data import init_data

REGISTRY = """specs:
  - code: WRN
    source: data/sources/WRN/w.md
"""


def make_root(tmp_path: Path) -> Path:
    (tmp_path / "specs.yaml").write_text(REGISTRY, encoding="utf-8")
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

    (data / "knowledge" / "glossary.md").write_text("edited", encoding="utf-8")
    init_data(root, git=False)
    assert (data / "knowledge" / "glossary.md").read_text(encoding="utf-8") == "edited"


def test_legacy_warning_and_migration(tmp_path):
    root = make_root(tmp_path)
    legacy = root / "sources" / "WRN"
    legacy.mkdir(parents=True)
    (legacy / "w.md").write_text("# spec", encoding="utf-8")
    (root / "reports").mkdir()
    (root / "reports" / "profile.txt").write_text("stats", encoding="utf-8")

    log = init_data(root, git=False)
    assert any("CẢNH BÁO" in line for line in log)
    assert (legacy / "w.md").exists()

    init_data(root, migrate=True, git=False)
    assert (root / "data" / "sources" / "WRN" / "w.md").read_text(encoding="utf-8") == "# spec"
    assert (root / "data" / "reports" / "profile.txt").exists()
    assert not (root / "sources").exists() and not (root / "reports").exists()


def test_git_init(tmp_path):
    root = make_root(tmp_path)
    init_data(root)
    assert (root / "data" / ".git").is_dir()
