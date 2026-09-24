"""T3: sg get and sg related, on the DMD fixture vault.

At max_tokens=10**6 the notes are DMD-0000 (preamble), DMD-0001 (chapter 1, holding the
sub-headings DMD-0002 "1.1" and DMD-0003 "1.1.1"), DMD-0004 (chapter 2, holding DMD-0005 "2.1")
and DMD-0006 (Appendix).
"""

import json

import pytest

from specgarage.build_vault import build_vault
from specgarage.cli import main
from specgarage.section import get, related
from specgarage.vault import VaultError, load_spec_vault
from test_build_vault import make_root


def built(tmp_path, max_tokens=10**6):
    root = make_root(tmp_path)
    list(build_vault(root, max_tokens=max_tokens))
    return root


def ids(items):
    return [i["id"] for i in items]


# ── the section index ──────────────────────────────────────────────────────────────────────


def test_every_heading_id_is_a_section(tmp_path):
    vault = load_spec_vault(built(tmp_path), "DMD")
    assert sorted(vault.sections) == [f"DMD-000{i}" for i in range(7)]
    sub = vault.sections["DMD-0003"]
    assert (sub.note, sub.parent, sub.level) == ("DMD-0001", "DMD-0002", 3)
    assert vault.breadcrumb(sub) == ["1. Demo Function", "1.1. Overview", "1.1.1. Sub Behaviour"]


# ── get ────────────────────────────────────────────────────────────────────────────────────


def test_get_sub_heading(tmp_path):
    root = built(tmp_path)
    s = get(root, "DMD-0003")
    assert s["note"] == "DMD-0001" and s["path"] == "data/vault/DMD/DMD-0001.md"
    assert s["text"].startswith("### 1.1.1. Sub Behaviour")
    assert "200 ms" in s["text"] and "Second Function" not in s["text"]
    lines = (root / s["path"]).read_text(encoding="utf-8").splitlines()
    first, last = s["lines"]
    assert lines[first - 1:last] == s["text"].splitlines()  # the line range points at the text


def test_get_sub_heading_includes_its_children(tmp_path):
    s = get(built(tmp_path), "DMD-0002")
    assert "### 1.1.1. Sub Behaviour" in s["text"] and "# 2. Second Function" not in s["text"]


def test_get_note_with_and_without_frontmatter(tmp_path):
    root = built(tmp_path)
    full = get(root, "DMD-0006")
    assert full["text"].startswith("---\nid: DMD-0006") and full["lines"][0] == 1
    body = get(root, "DMD-0006", frontmatter=False)
    assert body["text"].startswith("# Appendix")
    lines = (root / body["path"]).read_text(encoding="utf-8").splitlines()
    assert lines[body["lines"][0] - 1] == "# Appendix"


def test_get_unknown_id(tmp_path):
    root = built(tmp_path)
    with pytest.raises(VaultError, match="not found"):
        get(root, "DMD-0099")
    with pytest.raises(VaultError, match="invalid ID"):
        get(root, "nope")


# ── related ────────────────────────────────────────────────────────────────────────────────


def test_related_sub_heading(tmp_path):
    r = related(built(tmp_path), "DMD-0002")
    assert ids(r["out"]) == []
    assert ids(r["in"]) == ["DMD-0001"]  # "[Overview](#overview)" in chapter 1's own text
    assert r["in"][0]["via"] == ["#overview"]


def test_related_note_skips_links_inside_itself(tmp_path):
    r = related(built(tmp_path), "DMD-0001")
    assert ids(r["out"]) == ["DMD-0006"]  # #overview stays inside, #_Ref100010 points at itself
    assert ids(r["in"]) == []  # only the table of contents links here


def test_related_preamble_is_opt_in(tmp_path):
    r = related(built(tmp_path), "DMD-0001", include_preamble=True)
    assert ids(r["in"]) == ["DMD-0000"]
    assert r["in"][0]["via"] == ["#demo-function", "#overview"]


def test_related_depth(tmp_path):
    root = built(tmp_path, 20)  # every heading its own note
    one = related(root, "DMD-0002")
    two = related(root, "DMD-0002", depth=2)
    assert ids(one["in"]) == ["DMD-0001"]
    assert [(i["id"], i["depth"]) for i in two["in"]] == [("DMD-0001", 1)]  # nothing links to DMD-0001


def test_related_follows_relinked_note_links(tmp_path):
    root = built(tmp_path)
    p = root / "data" / "vault" / "DMD" / "DMD-0006.md"
    p.write_text(p.read_text(encoding="utf-8") + "\nSee [sub](DMD-0001.md#sub-behaviour) and [ch2](DMD-0004.md).\n",
                 encoding="utf-8")
    r = related(root, "DMD-0006")
    assert ids(r["out"]) == ["DMD-0003", "DMD-0004"]
    assert related(root, "DMD-0003")["in"][0]["via"] == ["DMD-0001.md#sub-behaviour"]


# ── CLI ────────────────────────────────────────────────────────────────────────────────────


def test_cli(tmp_path, monkeypatch, capsys):
    root = built(tmp_path)
    monkeypatch.chdir(root)
    assert main(["get", "DMD-0003"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("DMD-0003 (in DMD-0001)  data/vault/DMD/DMD-0001.md:")
    assert "1. Demo Function > 1.1. Overview > 1.1.1. Sub Behaviour" in out

    assert main(["get", "DMD-0003", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["note"] == "DMD-0001"

    assert main(["related", "DMD-0002"]) == 0
    assert "linked from (1):\n  DMD-0001  1. Demo Function" in capsys.readouterr().out

    assert main(["related", "DMD-0099"]) == 1
    assert "not found" in capsys.readouterr().err
