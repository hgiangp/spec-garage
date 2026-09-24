"""T5: export concatenates the notes back into the source, and --check proves it."""

import pytest

from specgarage.build_vault import build_vault
from specgarage.cli import main
from specgarage.export import (
    ExportError, compare, drop_id_lines, export_spec, export_vault, non_blank, restore_image_paths,
)
from test_build_vault import DEMO, make_root


def built(tmp_path, max_tokens=20):
    root = make_root(tmp_path)
    list(build_vault(root, max_tokens=max_tokens))
    return root


@pytest.mark.parametrize("max_tokens", [1, 20, 100, 10**6])
def test_round_trip_is_exact_up_to_blank_lines(tmp_path, max_tokens):
    root = built(tmp_path, max_tokens)
    text, result = export_spec(root, "DMD")
    source = DEMO.read_text(encoding="utf-8")
    assert non_blank(text) == non_blank(source)  # image paths restored exactly, not just by name
    assert "images/image1.png" in text and "attachments" not in text
    assert "<!-- id:" not in text
    assert result.warnings == []


def test_check_passes_and_writes_the_file(tmp_path):
    root = built(tmp_path)
    [r] = list(export_vault(root, ["DMD"], check=True))
    assert r.mismatch == []
    assert r.path == root / "build" / "export" / "DMD.md"
    assert r.path.read_text(encoding="utf-8").lstrip().startswith("Synthetic fixture")


def test_check_catches_an_edited_note(tmp_path):
    root = built(tmp_path)
    note = root / "data" / "vault" / "DMD" / "DMD-0002.md"
    note.write_text(note.read_text(encoding="utf-8").replace("Text for the first overview",
                                                             "Changed overview"), encoding="utf-8")
    [r] = list(export_vault(root, ["DMD"], check=True))
    assert r.mismatch and "Changed overview" in r.mismatch[0]


def test_keep_ids(tmp_path):
    root = built(tmp_path, 10**6)
    text, _ = export_spec(root, "DMD", keep_ids=True)
    assert "<!-- id: DMD-0002 | legacy: 1.1 -->" in text
    with pytest.raises(ExportError, match="--keep-ids"):
        list(export_vault(root, ["DMD"], keep_ids=True, check=True))


def test_missing_source_keeps_vault_image_paths_and_warns(tmp_path):
    root = built(tmp_path)
    (root / "data" / "sources" / "DMD" / DEMO.name).unlink()
    text, result = export_spec(root, "DMD")
    assert "../attachments/DMD/image1.png" in text
    assert any("not found" in w for w in result.warnings)


def test_changed_source_is_reported(tmp_path):
    root = built(tmp_path)
    src = root / "data" / "sources" / "DMD" / DEMO.name
    src.write_text(src.read_text(encoding="utf-8") + "\nExtra line.\n", encoding="utf-8")
    [r] = list(export_vault(root, ["DMD"], check=True))
    assert any("sha256" in w for w in r.warnings)
    assert r.mismatch  # the extra line is not in the vault


def test_missing_note_is_an_error(tmp_path):
    root = built(tmp_path)
    (root / "data" / "vault" / "DMD" / "DMD-0003.md").unlink()
    with pytest.raises(ExportError, match="DMD-0003"):
        export_spec(root, "DMD")


def test_no_vault_is_an_error(tmp_path):
    with pytest.raises(ExportError, match="build-vault"):
        list(export_vault(make_root(tmp_path)))


def test_helpers():
    assert drop_id_lines("## 1.1 A\n<!-- id: WRN-0002 | legacy: 1.1 -->\ntext") == "## 1.1 A\ntext"
    assert drop_id_lines("<!-- not an id -->") == "<!-- not an id -->"
    warnings = []
    html = '<img src="../attachments/WRN/a.png" width="5"/> ![x](../attachments/WRN/b.png)'
    assert restore_image_paths(html, {"a.png": "images/media/a.png"}, warnings) == (
        '<img src="images/media/a.png" width="5"/> ![x](../attachments/WRN/b.png)')
    assert warnings == ["no source path for image b.png; kept ../attachments/WRN/b.png"]
    assert compare("a\n\nb\n", "a\nb") == []
    assert compare("a\nc\n", "a\nb\n")[0].startswith("non-blank line 2")


def test_cli_export_check(tmp_path, monkeypatch, capsys):
    root = built(tmp_path)
    monkeypatch.chdir(root)
    assert main(["export", "--check"]) == 0
    out = capsys.readouterr().out
    assert "DMD: 7 notes" in out and "round-trip OK DMD" in out

    note = root / "data" / "vault" / "DMD" / "DMD-0001.md"
    note.write_text(note.read_text(encoding="utf-8") + "\nAdded.\n", encoding="utf-8")
    assert main(["export", "DMD", "--check"]) == 1
    assert "round-trip FAILED DMD" in capsys.readouterr().out
