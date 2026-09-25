"""sg find and sg specs --lookup, on the DMD fixture vault (see test_section.py for its layout)."""

import json

import pytest

from specgarage.cli import main
from specgarage.config import load_specs, lookup_spec, normalize_name
from specgarage.find import find, near_misses, term_pattern
from specgarage.vault import VaultError
from test_section import built


def where(hits):
    return [(h.id, h.kind) for h in hits]


# ── spec names ─────────────────────────────────────────────────────────────────────────────


def test_normalize_name_ignores_case_spaces_dots_quotes():
    assert normalize_name("NAVIG.") == normalize_name("navig")
    assert normalize_name("“Demo COMM”") == normalize_name("demo comm") == normalize_name("DEMOCOMM")


def test_lookup_by_code_title_and_alias(tmp_path):
    root = built(tmp_path)
    reg = root / "specs.yaml"
    reg.write_text(reg.read_text(encoding="utf-8") + "    aliases: [Demo COMM]\n", encoding="utf-8")
    specs = load_specs(root)
    assert specs[0].aliases == ["Demo COMM"]
    for name in ("DMD", "demo vault", "Demo  Vault", "DEMO COMM", "“Demo COMM”"):
        assert lookup_spec(specs, name).code == "DMD", name
    assert lookup_spec(specs, "Unknown Module") is None


# ── find ───────────────────────────────────────────────────────────────────────────────────


def test_whole_word_by_default():
    p = term_pattern("FOO operation")
    assert p.search("| 13 | FOO operation | Demo COMM |")
    assert p.search("foo\noperation")  # a line-wrapped name still matches
    assert not p.search("| 16 | XFOO operation | Demo COMM |")
    assert term_pattern("FOO operation", word=False).search("XFOO operation")


def test_section_numbers_and_hyphens():
    p = term_pattern("3.2.")
    assert p.search("## 3.2. Home")
    assert not p.search("### 1.3.2. Hardwire") and not p.search("### 3.2.1. Sub")
    assert term_pattern("Table 1-3").search("Table 1‑3 List of data")  # non-breaking hyphen


def test_hits_map_to_the_smallest_section_and_kind(tmp_path):
    assert where(find(built(tmp_path / "a"), "Table 1-1", kinds=["text"]))[0] == ("DMD-0001", "text")
    hits = find(built(tmp_path), "Demo threshold")
    assert where(hits) == [("DMD-0001", "table")]  # an HTML table cell in chapter 1
    hits = find(built(tmp_path / "b"), "200 ms")
    assert where(hits) == [("DMD-0003", "text")]  # inside sub-heading 1.1.1 of note DMD-0001
    h = hits[0]
    assert h.note == "DMD-0001" and h.breadcrumb[-1] == "1.1.1. Sub Behaviour"
    lines = (tmp_path / "b" / "repo" / h.path).read_text(encoding="utf-8").splitlines()
    assert "200 ms" in lines[h.line - 1]  # the line number points at the file line


def test_headings_sort_first_and_preamble_is_skipped(tmp_path):
    root = built(tmp_path)
    hits = find(root, "Overview")
    assert where(hits)[:2] == [("DMD-0002", "heading"), ("DMD-0005", "heading")]
    assert all(h.note != "DMD-0000" for h in hits)  # the table of contents repeats every heading
    assert any(h.note == "DMD-0000" for h in find(root, "Overview", include_preamble=True))
    assert where(find(root, "Overview", kinds=["heading"])) == [("DMD-0002", "heading"), ("DMD-0005", "heading")]


def test_id_comments_are_not_hits(tmp_path):
    assert find(built(tmp_path), "DMD-0003") == []


def test_word_and_case_options(tmp_path):
    root = built(tmp_path)
    assert find(root, "verview") == []
    assert find(root, "verview", word=False)
    assert find(root, "demo lamp")
    assert find(root, "DEMO LAMP", case_sensitive=True) == []


def with_signals(tmp_path):
    """The fixture vault plus a line naming two signals that share the prefix R_DEMO."""
    root = built(tmp_path)
    note = root / "data" / "vault" / "DMD" / "DMD-0006.md"
    note.write_text(note.read_text(encoding="utf-8")
                    + "\nR_DEMO_UP or R_DEMO_DOWN changes from 0; see also r_demo_up.\n", encoding="utf-8")
    return root


def test_underscore_is_part_of_a_name(tmp_path):
    root = with_signals(tmp_path)
    assert find(root, "R_DEMO") == []  # R_DEMO_UP is another signal, not a use of R_DEMO
    hits = find(root, "R_DEMO_UP")
    assert where(hits) == [("DMD-0006", "text")] and hits[0].matches == ["R_DEMO_UP", "r_demo_up"]


def test_near_misses_list_the_longer_names(tmp_path):
    root = with_signals(tmp_path)
    assert near_misses(root, "R_DEMO") == {"R_DEMO_UP": 1, "R_DEMO_DOWN": 1, "r_demo_up": 1}
    assert near_misses(root, "R_DEMO", case_sensitive=True) == {"R_DEMO_UP": 1, "R_DEMO_DOWN": 1}
    assert near_misses(root, "R_DEMO", kinds=["heading"]) == {}  # --kind applies too
    assert near_misses(root, "no such term") == {}
    assert near_misses(root, "verview")["Overview"] >= 2  # works for inner parts of words as well


def test_spec_filter_by_name_and_unknown_spec(tmp_path):
    root = built(tmp_path)
    assert find(root, "200 ms", specs=["Demo Vault"])
    with pytest.raises(VaultError, match="not a spec in specs.yaml"):
        find(root, "200 ms", specs=["Unknown Module"])
    with pytest.raises(VaultError, match="empty"):
        find(root, "  ")


# ── CLI ────────────────────────────────────────────────────────────────────────────────────


def test_output_is_utf8_on_a_cp1252_console(tmp_path, monkeypatch):
    import io
    import sys

    monkeypatch.chdir(built(tmp_path))
    raw = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(raw, encoding="cp1252"))
    assert main(["find", "Table 1-1", "--kind", "text"]) == 0  # the snippet holds a non-breaking hyphen
    sys.stdout.flush()
    assert "Table 1‑1" in raw.getvalue().decode("utf-8")


def test_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(built(tmp_path))
    assert main(["find", "200 ms"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("DMD-0003 (in DMD-0001)  text     data/vault/DMD/DMD-0001.md:")
    assert "1 hit(s) in 1 section(s)" in out

    assert main(["find", "Overview", "--json", "--kind", "heading"]) == 0
    assert [h["id"] for h in json.loads(capsys.readouterr().out)] == ["DMD-0002", "DMD-0005"]

    assert main(["find", "no such term"]) == 1
    assert main(["find", "x", "--spec", "Unknown Module"]) == 1
    assert "not a spec" in capsys.readouterr().err

    assert main(["specs", "--lookup", "demo vault"]) == 0
    assert capsys.readouterr().out.startswith("DMD  Demo Vault  data/sources/DMD/")
    assert main(["specs", "--lookup", "Unknown Module"]) == 1


def test_cli_hints_at_longer_names_when_nothing_matches(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(with_signals(tmp_path))
    assert main(["find", "R_DEMO"]) == 1  # still no hit: the hint does not change the result
    out, err = capsys.readouterr()
    assert "0 hit(s)" in out
    assert err.strip() == ("no whole-word match; --substring finds it inside: "
                           "R_DEMO_UP (1), R_DEMO_DOWN (1), r_demo_up (1)")

    assert main(["find", "R_DEMO", "--json"]) == 1
    out, err = capsys.readouterr()
    assert json.loads(out) == [] and "R_DEMO_UP" in err  # stdout stays valid JSON

    assert main(["find", "R_DEMO", "--substring", "--json"]) == 0
    out, err = capsys.readouterr()
    assert json.loads(out)[0]["matches"] == ["R_DEMO", "R_DEMO", "r_demo"] and err == ""

    assert main(["find", "no such term"]) == 1
    assert capsys.readouterr().err == ""  # no hint when there is nothing to hint at
