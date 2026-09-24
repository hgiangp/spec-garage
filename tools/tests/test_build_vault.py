"""T2: build-vault splits a spec into notes without changing its text.

The fixture (DMD) mirrors the shapes the real converter emits: a table of contents with page
numbers, caption anchors in their own span, an HTML table, an image with a long alt text and a
width attribute, repeated heading titles and a heading with no number.
"""

from pathlib import Path

import pytest
import yaml

from specgarage.build_vault import BuildError, build_vault, rewrite_image_paths
from specgarage.cli import main
from specgarage.config import Spec
from specgarage.ids import Manifest
from specgarage.notes import plan_notes
from specgarage.parse import parse_file

FIXTURES = Path(__file__).parent / "fixtures" / "sources"
DEMO = FIXTURES / "DMD" / "9999ZXXXXD000_E_(Demo Vault)_260101.md"
ID_COMMENT = "<!-- id: "


def make_root(tmp_path: Path) -> Path:
    """A repo root holding the fixture spec, so build-vault can run end to end."""
    root = tmp_path / "repo"
    sources = root / "data" / "sources" / "DMD"
    sources.mkdir(parents=True)
    (sources / DEMO.name).write_text(DEMO.read_text(encoding="utf-8"), encoding="utf-8")
    (sources / "images").mkdir()
    (sources / "images" / "image1.png").write_bytes((DEMO.parent / "images" / "image1.png").read_bytes())
    (root / "specs.yaml").write_text(
        "specs:\n"
        "  - code: DMD\n"
        "    doc_no: 9999ZXXXXD000\n"
        "    title: Demo Vault\n"
        "    date: 2026-01-01\n"
        f"    source: data/sources/DMD/{DEMO.name}\n",
        encoding="utf-8",
    )
    return root


def build(tmp_path: Path, **kw) -> Path:
    root = kw.pop("root", None) or make_root(tmp_path)
    list(build_vault(root, **kw))
    return root / "data" / "vault"


def read_note(vault: Path, section_id: str) -> tuple[dict, str]:
    text = (vault / "DMD" / f"{section_id}.md").read_text(encoding="utf-8")
    _, front, body = text.split("---\n", 2)
    return yaml.safe_load(front), body


# ── the split ───────────────────────────────────────────────────────────────────────────────


def test_notes_tile_the_document():
    """Every line belongs to exactly one note: that is what makes export a concatenation."""
    doc = parse_file(DEMO)
    for max_tokens in (1, 20, 100, 10**6):
        notes = plan_notes(doc, max_tokens)
        assert notes[0].start == 1
        assert notes[-1].end == doc.line_count + 1
        for a, b in zip(notes, notes[1:]):
            assert a.end == b.start


def test_html_table_is_never_cut():
    doc = parse_file(DEMO)
    lines = doc.text.splitlines()
    for max_tokens in (1, 5, 20, 100):
        for note in plan_notes(doc, max_tokens):
            chunk = "\n".join(lines[note.start - 1:note.end - 1])
            assert chunk.count("<table") == chunk.count("</table")


def test_anchor_line_above_a_heading_moves_into_its_note():
    doc = parse_file(DEMO)
    lines = doc.text.splitlines()
    notes = {doc.headings[n.heading].title if n.heading is not None else None: n for n in plan_notes(doc, 1)}
    overview = notes["2.1. Overview"]
    assert "_Ref100030" in lines[overview.start - 1]  # pulled in, not left in the parent note


# ── what a note contains ────────────────────────────────────────────────────────────────────


def test_note_text_is_the_source_text(tmp_path):
    """Only image paths and added id comments may differ from the source."""
    vault = build(tmp_path, max_tokens=20)
    rebuilt = []
    manifest = Manifest.from_dict(yaml.safe_load((vault / "DMD" / "_manifest.yaml").read_text(encoding="utf-8")))
    for section_id in manifest.ids():
        _, body = read_note(vault, section_id)
        rebuilt += [l for l in body.splitlines() if not l.startswith(ID_COMMENT)]

    expect = rewrite_image_paths(DEMO.read_text(encoding="utf-8"), "DMD").splitlines()
    assert [l for l in rebuilt if l.strip()] == [l for l in expect if l.strip()]


def test_frontmatter_and_id_comments(tmp_path):
    vault = build(tmp_path, max_tokens=20)
    front, body = read_note(vault, "DMD-0002")  # "1.1. Overview" (heading 2 of 6)
    assert front["id"] == "DMD-0002"
    assert front["spec"] == "DMD"
    assert front["title"] == "Overview"
    assert front["aliases"] == ["1.1. Overview"]
    assert front["legacy_number"] == "1.1"
    assert front["heading_path"] == ["1. Demo Function", "1.1. Overview"]
    assert front["level"] == 2
    assert front["status"] == "original"
    # the anchor line above "1.1.1" belongs to that heading, so it is not this note's anchor
    assert front["anchors"] == []
    assert read_note(vault, "DMD-0003")[0]["anchors"] == ["_Ref100020"]
    assert body.count(ID_COMMENT) == 0  # at this threshold every heading is its own note

    preamble, _ = read_note(vault, "DMD-0000")
    assert preamble["title"] == "Preamble" and preamble["level"] == 0


def test_sub_headings_inside_a_note_get_an_id_comment(tmp_path):
    vault = build(tmp_path, max_tokens=10**6)  # one note per H1
    _, body = read_note(vault, "DMD-0001")
    assert "<!-- id: DMD-0002 | legacy: 1.1 -->" in body
    assert "<!-- id: DMD-0003 | legacy: 1.1.1 | anchors: _Ref100020 -->" in body
    assert body.count(ID_COMMENT) == 2  # the note's own heading does not get one


def test_links_are_left_verbatim(tmp_path):
    vault = build(tmp_path, max_tokens=20)
    _, body = read_note(vault, "DMD-0001")
    assert "[Table 1‑1](#_Ref100010)" in body  # not rewritten to a note link
    assert "(#overview)" in body
    # assert '<span id="_Ref100010" class="anchor"></span>' in body  # anchors kept too
    assert "<span id=\"_Ref100010\" class=\"anchor\"></span>" in body  # anchors kept too
 

def test_images_are_copied_and_repointed(tmp_path):
    vault = build(tmp_path, max_tokens=20)
    _, body = read_note(vault, "DMD-0002")
    assert "](../attachments/DMD/image1.png){width=\"5.0in\"" in body
    assert "Demo state machine" in body  # alt text survives, including its line break
    assert (vault / "attachments" / "DMD" / "image1.png").is_file()


def test_rewrite_image_paths_leaves_other_links_alone():
    assert rewrite_image_paths("see [x](#_Ref1) and ![a](images/media/i.png)", "WRN") == (
        "see [x](#_Ref1) and ![a](../attachments/WRN/i.png)")
    assert rewrite_image_paths('<img src="images/i.png" width="5"/>', "WRN") == (
        '<img src="../attachments/WRN/i.png" width="5"/>')
    assert rewrite_image_paths("[a link](other.md)", "WRN") == "[a link](other.md)"


# ── the maps beside the notes ───────────────────────────────────────────────────────────────


def test_manifest_tree_follows_the_heading_hierarchy(tmp_path):
    vault = build(tmp_path, max_tokens=20)
    data = yaml.safe_load((vault / "DMD" / "_manifest.yaml").read_text(encoding="utf-8"))
    manifest = Manifest.from_dict(data)
    assert data["max_tokens"] == 20
    assert data["source_sha256"] and data["built_with"].startswith("specgarage ")
    assert manifest.next_id == 7  # 6 headings, IDs 1..6, preamble is 0
    assert manifest.parent_of("DMD-0003") == "DMD-0002"
    assert manifest.parent_of("DMD-0002") == "DMD-0001"
    assert manifest.parent_of("DMD-0000") is None
    assert manifest.ids() == ["DMD-0000", "DMD-0001", "DMD-0002", "DMD-0003", "DMD-0004", "DMD-0005", "DMD-0006"]


def test_anchor_map_covers_explicit_anchors_and_slugs(tmp_path):
    vault = build(tmp_path, max_tokens=20)
    data = yaml.safe_load((vault / "DMD" / "_anchors.yaml").read_text(encoding="utf-8"))
    assert data["anchors"]["_Ref100010"] == "DMD-0001"  # caption anchor -> the heading that owns it
    assert data["anchors"]["overview"] == "DMD-0002"
    assert data["anchors"]["overview-1"] == "DMD-0005"  # pandoc de-duplication
    assert data["anchors"]["appendix"] == "DMD-0006"  # heading with no number
    # sub-headings that are not notes of their own map back to the note holding them
    assert data["notes"] == {}  # at this threshold every heading is its own note


def test_sub_heading_maps_back_to_its_note(tmp_path):
    vault = build(tmp_path, max_tokens=10**6)
    data = yaml.safe_load((vault / "DMD" / "_anchors.yaml").read_text(encoding="utf-8"))
    assert data["notes"]["DMD-0002"] == "DMD-0001"  # "1.1. Overview" lives inside "1. Demo Function"
    assert data["anchors"]["overview"] == "DMD-0002"  # the anchor still names the heading


def test_refs_out_resolves_through_the_anchor_map(tmp_path):
    vault = build(tmp_path, max_tokens=20)
    front, _ = read_note(vault, "DMD-0001")
    assert front["refs_out"] == ["DMD-0002", "DMD-0006"]  # #_Ref100010 points at itself, so it is dropped


def test_toc_uses_markdown_links(tmp_path):
    vault = build(tmp_path, max_tokens=20)
    toc = (vault / "DMD" / "_toc.md").read_text(encoding="utf-8")
    assert "- [1. Demo Function](DMD-0001.md)" in toc
    assert "  - [1.1. Overview](DMD-0002.md)" in toc
    assert "[[" not in toc


# ── safety ──────────────────────────────────────────────────────────────────────────────────


def test_refuses_to_overwrite_without_force(tmp_path):
    root = make_root(tmp_path)
    build(tmp_path, root=root, max_tokens=20)
    with pytest.raises(BuildError, match="--force"):
        list(build_vault(root, max_tokens=20))
    list(build_vault(root, max_tokens=20, force=True))  # allowed with --force


def test_dry_run_writes_nothing(tmp_path):
    root = make_root(tmp_path)
    lines = list(build_vault(root, max_tokens=20, dry_run=True))
    assert "DMD: 7 notes" in lines[0]
    assert not (root / "data" / "vault" / "DMD").exists()


def test_unknown_code_is_an_error(tmp_path):
    with pytest.raises(BuildError, match="no spec matches"):
        list(build_vault(make_root(tmp_path), ["NOPE"]))


def test_cli_build_vault(tmp_path, monkeypatch, capsys):
    root = make_root(tmp_path)
    monkeypatch.chdir(root)
    assert main(["build-vault", "DMD", "--max-tokens", "20"]) == 0
    assert "DMD: 7 notes" in capsys.readouterr().out
    assert main(["build-vault", "DMD", "--max-tokens", "20"]) == 1  # refuses to overwrite
 