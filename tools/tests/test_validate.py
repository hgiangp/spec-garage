"""T4: validate passes a fresh vault and catches each rule V01-V10 when the vault is broken."""

import json

import pytest

from specgarage.build_vault import build_vault
from specgarage.cli import main
from specgarage.validate import ValidateError, pipe_rows, validate
from test_build_vault import make_root


def built(tmp_path, max_tokens=20):
    root = make_root(tmp_path)
    list(build_vault(root, max_tokens=max_tokens))
    return root


def note(root, sid):
    return root / "data" / "vault" / "DMD" / f"{sid}.md"


def edit(root, sid, old, new):
    p = note(root, sid)
    text = p.read_text(encoding="utf-8")
    assert old in text, old
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


def append(root, sid, text):
    p = note(root, sid)
    p.write_text(p.read_text(encoding="utf-8") + text, encoding="utf-8")


def rules(report):
    return sorted({f.rule for f in report.findings})


@pytest.mark.parametrize("max_tokens", [1, 20, 10**6])
def test_fresh_vault_is_clean(tmp_path, max_tokens):
    report = validate(built(tmp_path, max_tokens))
    assert report.findings == []
    assert report.notes["DMD"] > 0


def test_v01_frontmatter(tmp_path):
    root = built(tmp_path)
    edit(root, "DMD-0002", "status: original\n", "")
    edit(root, "DMD-0003", "id: DMD-0003", "id: DMD-0033")
    note(root, "DMD-0004").write_text("# no frontmatter\n", encoding="utf-8")
    msgs = [f.message for f in validate(root).findings if f.rule == "V01"]
    assert any("missing fields: status" in m for m in msgs)
    assert any("does not match the file name" in m for m in msgs)
    assert any("no frontmatter" in m for m in msgs)


def test_v02_duplicate_id(tmp_path):
    root = built(tmp_path, 10**6)  # DMD-0001 holds the id lines for DMD-0002 and DMD-0003
    edit(root, "DMD-0001", "<!-- id: DMD-0003", "<!-- id: DMD-0002")
    assert "V02" in rules(validate(root))


def test_v03_manifest_and_files(tmp_path):
    root = built(tmp_path)
    note(root, "DMD-0003").unlink()
    note(root, "DMD-0099").write_text(note(root, "DMD-0002").read_text(encoding="utf-8")
                                      .replace("id: DMD-0002", "id: DMD-0099"), encoding="utf-8")
    msgs = [f.message for f in validate(root).findings if f.rule == "V03"]
    assert any("DMD-0003 is in the manifest" in m for m in msgs)
    assert any("DMD-0099.md is not in the manifest tree" in m for m in msgs)
    assert any("DMD-0099 has not been allocated" in m for m in msgs)


def test_v04_unresolved_link_and_broken_ref(tmp_path):
    root = built(tmp_path)
    append(root, "DMD-0004", "\nSee [nowhere](#no-such-anchor).\n")
    report = validate(root)
    assert [f.message for f in report.findings if f.rule == "V04"] == [
        "link #no-such-anchor is not in _anchors.yaml"]

    edit(root, "DMD-0004", "(#no-such-anchor).", "(#no-such-anchor). #broken-ref")
    assert rules(validate(root)) == ["V08"]  # a marked broken link is a warning, not an error


def test_v04_relinked_note_links(tmp_path):
    root = built(tmp_path)
    append(root, "DMD-0004", "\n[ok](DMD-0002.md#overview) [gone](DMD-0099.md) [bad](DMD-0002.md#nope)\n")
    msgs = [f.message for f in validate(root).findings if f.rule == "V04"]
    assert msgs == ["link to missing note DMD-0099.md", "DMD-0002.md has no heading or anchor #nope"]


def test_v05_missing_and_misplaced_id_lines(tmp_path):
    root = built(tmp_path, 10**6)
    edit(root, "DMD-0001", "<!-- id: DMD-0003 | legacy: 1.1.1 | anchors: _Ref100020 -->\n", "")
    edit(root, "DMD-0001", "The demo function", "<!-- id: DMD-0003 -->\nThe demo function")
    msgs = [f.message for f in validate(root).findings if f.rule == "V05"]
    assert any("'1.1.1' has no id line" in m for m in msgs)
    assert any("not directly under a sub-heading" in m for m in msgs)


def test_v06_missing_image(tmp_path):
    root = built(tmp_path)
    edit(root, "DMD-0002", "attachments/DMD/image1.png", "attachments/DMD/missing.png")
    assert rules(validate(root)) == ["V06"]


def test_v07_status_and_derived_from(tmp_path):
    root = built(tmp_path)
    edit(root, "DMD-0002", "status: original", "status: done")
    edit(root, "DMD-0003", "derived_from: []", "derived_from: [DMD-0500]")
    msgs = [f.message for f in validate(root).findings if f.rule == "V07"]
    assert any("status 'done'" in m for m in msgs)
    assert any("DMD-0500 has not been allocated" in m for m in msgs)


def test_v09_pipe_table_columns(tmp_path):
    root = built(tmp_path)
    append(root, "DMD-0006", "\n\n| a | b |\n|---|---|\n| 1 | 2 |\n| 1 | 2 | 3 |\n| x \\| y | `a|b` |\n")
    [f] = validate(root).findings
    assert f.rule == "V09" and f.level == "warning" and "1 row(s)" in f.message


def test_v10_refs_out_and_fix(tmp_path):
    root = built(tmp_path)
    edit(root, "DMD-0001", "refs_out:\n- DMD-0002\n- DMD-0006", "refs_out:\n- DMD-0005")
    report = validate(root)
    assert rules(report) == ["V10"] and report.errors == 0

    body_before = note(root, "DMD-0001").read_text(encoding="utf-8").split("\n---\n", 1)[1]
    assert validate(root, fix_refs=True).fixed == 1
    assert validate(root).findings == []
    assert note(root, "DMD-0001").read_text(encoding="utf-8").split("\n---\n", 1)[1] == body_before


def test_pipe_rows():
    assert pipe_rows("| a | b |") == 2
    assert pipe_rows("a | b | c") == 3
    assert pipe_rows("| x \\| y | z |") == 2
    assert pipe_rows("| `a|b` | c |") == 2


def test_no_vault(tmp_path):
    with pytest.raises(ValidateError, match="build-vault"):
        validate(make_root(tmp_path))


def test_cli(tmp_path, monkeypatch, capsys):
    root = built(tmp_path)
    monkeypatch.chdir(root)
    assert main(["validate"]) == 0
    assert "summary: 0 error(s), 0 warning(s)" in capsys.readouterr().out

    edit(root, "DMD-0002", "status: original", "status: done")
    assert main(["validate", "DMD"]) == 1
    out = capsys.readouterr().out
    assert "V07 error" in out and "summary: 1 error(s)" in out

    assert main(["validate", "--json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["errors"] == 1 and data["findings"][0]["rule"] == "V07"
