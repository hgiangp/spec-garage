"""T9: add-spec puts a converted spec in place and registers it, so adding a spec is a data-only change."""

import shutil
from pathlib import Path

import pytest

from specgarage.add_spec import AddSpecError, add_spec, parse_file_name
from specgarage.cli import main
from specgarage.config import load_specs
from test_build_vault import DEMO, make_root

HEADER = "# a comment that must survive\nspecs:\n"


def converter_output(where: Path) -> Path:
    """What the converter leaves behind: <name>.out/ holding the .md and images/."""
    out = where / f"{DEMO.stem}.out"
    out.mkdir(parents=True)
    shutil.copy2(DEMO, out / DEMO.name)
    shutil.copytree(DEMO.parent / "images", out / "images")
    return out


def empty_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "data").mkdir(parents=True)
    (root / "data" / "specs.yaml").write_text(HEADER, encoding="utf-8")
    return root


def test_file_name_parts():
    parts = parse_file_name("7821ZXXXXJ000_E_(ADAS AD)_260220")
    assert (parts.doc_no, parts.lang, parts.title, parts.date) == ("7821ZXXXXJ000", "E", "ADAS AD", "2026-02-20")
    assert parse_file_name("notes") is None


def test_moves_a_drop_in_folder_and_registers_it(tmp_path):
    root = empty_root(tmp_path)
    out = converter_output(root / "data" / "sources")
    lines = list(add_spec(root, out, "DEMO", aliases=["Demo/V"]))
    assert lines[1].startswith("  move ")

    dest = root / "data" / "sources" / "DEMO"
    assert not out.exists()  # moved: no second copy of the images left behind
    assert (dest / DEMO.name).is_file() and (dest / "images" / "image1.png").is_file()

    text = (root / "data" / "specs.yaml").read_text(encoding="utf-8")
    assert text.startswith(HEADER)
    [s] = load_specs(root)
    assert (s.code, s.doc_no, s.title, s.date, s.aliases) == ("DEMO", "9999ZXXXXD000", "Demo Vault",
                                                              "2026-01-01", ["Demo/V"])
    assert s.source == dest / DEMO.name and s.images == dest / "images"


def test_copies_from_outside_data(tmp_path):
    root = empty_root(tmp_path)
    out = converter_output(tmp_path / "downloads")
    lines = list(add_spec(root, out, "DEMO"))
    assert lines[1].startswith("  copy ")
    assert (out / DEMO.name).is_file()  # the original stays where it was
    assert (root / "data" / "sources" / "DEMO" / DEMO.name).is_file()


def test_dry_run_changes_nothing(tmp_path):
    root = empty_root(tmp_path)
    out = converter_output(root / "data" / "sources")
    lines = list(add_spec(root, out, "DEMO", dry_run=True))
    assert lines[-1].startswith("dry run")
    assert out.is_dir() and not (root / "data" / "sources" / "DEMO").exists()
    assert (root / "data" / "specs.yaml").read_text(encoding="utf-8") == HEADER


def test_an_empty_list_registry_is_extended(tmp_path):
    root = empty_root(tmp_path)
    (root / "data" / "specs.yaml").write_text("specs: []\n", encoding="utf-8")
    list(add_spec(root, converter_output(tmp_path / "in"), "DEMO"))
    assert [s.code for s in load_specs(root)] == ["DEMO"]


def test_a_bare_md_without_images(tmp_path):
    root = empty_root(tmp_path)
    md = tmp_path / "in" / "1234ZXXXXA000_E_(Plain Spec)_250101.md"
    md.parent.mkdir()
    md.write_text("# 1. Plain\n\nText only.\n", encoding="utf-8")
    list(add_spec(root, md, "PLN"))
    [s] = load_specs(root)
    assert s.source.is_file() and s.images is None


@pytest.mark.parametrize("code, message", [
    ("demo", "2 to 5 capital letters"),
    ("TOOLONG", "2 to 5 capital letters"),
    ("DMD", "already registered"),
])
def test_bad_or_taken_code(tmp_path, code, message):
    root = make_root(tmp_path)  # DMD is registered there
    with pytest.raises(AddSpecError, match=message):
        list(add_spec(root, converter_output(tmp_path / "in"), code))


def test_same_document_or_name_is_refused(tmp_path):
    root = make_root(tmp_path)
    with pytest.raises(AddSpecError, match="new revision"):
        list(add_spec(root, converter_output(tmp_path / "in"), "DMX"))
    with pytest.raises(AddSpecError, match="already refers to DMD"):
        list(add_spec(root, converter_output(tmp_path / "in2"), "DMX", doc_no="1111ZXXXXZ000"))
    with pytest.raises(AddSpecError, match="already refers to DMD"):
        list(add_spec(root, converter_output(tmp_path / "in3"), "DMX", doc_no="1111ZXXXXZ000",
                      title="Other", aliases=["demo.vault"]))


def test_inputs_that_would_break_image_links(tmp_path):
    root = empty_root(tmp_path)
    out = converter_output(tmp_path / "in")
    with pytest.raises(AddSpecError, match="not the .md alone"):
        list(add_spec(root, out / DEMO.name, "DEMO"))
    (out / "second.md").write_text("# x\n", encoding="utf-8")
    with pytest.raises(AddSpecError, match="exactly one .md"):
        list(add_spec(root, out, "DEMO"))


def test_file_name_off_pattern_needs_overrides(tmp_path):
    root = empty_root(tmp_path)
    md = tmp_path / "in" / "spec.md"
    md.parent.mkdir()
    md.write_text("# 1. Plain\n", encoding="utf-8")
    with pytest.raises(AddSpecError, match="--doc-no, --title and --date"):
        list(add_spec(root, md, "PLN"))
    list(add_spec(root, md, "PLN", title="Plain", doc_no="1234ZXXXXA000", date="2025-01-01"))
    assert load_specs(root)[0].title == "Plain"


def test_cli_build_runs_the_gate_b_checks(tmp_path, monkeypatch, capsys):
    root = empty_root(tmp_path)
    out = converter_output(root / "data" / "sources")
    monkeypatch.chdir(root)
    assert main(["add-spec", str(out), "--code", "DEMO", "--build", "--max-tokens", "20"]) == 0
    text = capsys.readouterr().out
    assert "registered DEMO" in text and "DEMO: 7 notes" in text
    assert "round-trip OK DEMO" in text and "summary: 0 error(s)" in text
    assert main(["add-spec", str(out), "--code", "DEMO"]) == 1  # gone: it was moved
    capsys.readouterr()

    assert main(["specs"]) == 0  # the live state that docs no longer carry
    row = capsys.readouterr().out
    assert row.startswith("DEMO ") and "notes:7 " in row and "baseline:- " in row
    assert main(["specs", "--lookup", "Demo/Vault"]) == 0  # slashes are ignored, like spaces
