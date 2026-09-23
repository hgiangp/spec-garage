from pathlib import Path

from specgarage.cli import main
from specgarage.parse import classify_link, parse_file
from specgarage.profile import plan_notes, profile_docs

FIXTURES = Path(__file__).parent / "fixtures" / "sources"
LAMP = FIXTURES / "DMA" / "9999ZXXXXA000_E_(Demo Lamp)_260101.md"
BUS = FIXTURES / "DMB" / "9999ZXXXXB000_E_(Demo Bus)_260101.md"


def test_heading_tree():
    doc = parse_file(LAMP)
    assert [h.level for h in doc.headings] == [1, 2, 1, 2, 3, 3, 4, 5, 2, 1]
    timing = doc.headings[5]
    assert timing.title == "2.1.2 Lamp Timing"
    assert timing.number == "2.1.2"
    assert timing.anchors == ["_Ref200001"]
    assert doc.headings[timing.parent].title == "2.1 Lamp Control"
    assert [doc.headings[c].title for c in timing.children] == ["2.1.2.1 Fault Handling"]
    assert doc.headings[6].anchors == ["_Ref200002"]  # HTML anchor on a heading
    assert timing.subtree_chars > timing.own_chars
    assert doc.preamble_chars > 0


def test_code_fence_is_not_a_heading():
    doc = parse_file(LAMP)
    assert not any("inside code" in h.title for h in doc.headings)


def test_links_and_images():
    doc = parse_file(LAMP)
    kinds = sorted(l.kind for l in doc.links)
    assert kinds == ["cross_file", "cross_file", "external", "internal", "internal"]
    cross = [l for l in doc.links if l.kind == "cross_file"]
    assert cross[0].file_part == "9999ZXXXXB000_E_(Demo Bus)_260101.docx"
    assert cross[0].anchor == "_Ref300001"
    assert [i.target for i in doc.images] == ["images/image1.png", "images/missing.png"]
    assert doc.tables["pipe"] == 1


def test_classify_link():
    assert classify_link("#_Ref1") == ("internal", None, "_Ref1")
    assert classify_link("https://x.org") == ("external", None, None)
    assert classify_link("a/b.png") == ("other", "a/b.png", None)
    assert classify_link("Spec.docx") == ("cross_file", "Spec.docx", None)


def test_profile_resolution_and_split():
    lamp, bus = parse_file(LAMP), parse_file(BUS)
    report = profile_docs([lamp, bus], [5])
    f = report["files"][0]
    assert f["links"]["internal_unresolved_sample"] == ["_Ref404404"]
    assert f["links"]["cross_file_resolution"] == {"resolved": 1, "unknown_file": 1}
    assert report["cross_file_targets_not_in_set"] == {"8888ZXXXXC000_E_(Other)_250101.docx": 1}
    assert f["images"]["missing_sample"] == ["images/missing.png"]
    assert f["headings"]["duplicate_titles"] == 0  # "2.1.1 Overview" vs "2.2 Overview" differ by number
    assert report["files"][1]["links"]["cross_file_resolution"] == {"resolved": 1}

    # A tiny threshold splits down to every heading; a huge one keeps each H1 whole.
    assert len(plan_notes(lamp, 1)) == len(lamp.headings) + 1  # + preamble
    assert len(plan_notes(lamp, 10**6)) == len(lamp.roots) + 1


def test_cli_profile(capsys):
    assert main(["profile", str(FIXTURES), "--thresholds", "100"]) == 0
    out = capsys.readouterr().out
    assert "split simulation" in out
    assert "8888ZXXXXC000_E_(Other)_250101.docx" in out


def test_edge_cases(tmp_path):
    md = tmp_path / "edge.md"
    md.write_text(
        "# Title with closing ##\n"
        "####### seven hashes is text\n"
        "#hashtag is text\n"
        "## IGN_ON Handling\n"
        "````\n"
        "```\n"
        "# still code\n"
        "````\n"
        "## After Code\n"
        "Note[^1] and [s](file:///C:/Specs/7821ZXXXXF000_E_(LIN%20COMM)_250620.docx#_Ref1).\n"
        "[^1]: A footnote, not a link\n",
        encoding="utf-8",
    )
    doc = parse_file(md)
    assert [h.title for h in doc.headings] == ["Title with closing", "IGN_ON Handling", "After Code"]
    assert [(l.kind, l.file_part, l.anchor) for l in doc.links] == [
        ("cross_file", "C:/Specs/7821ZXXXXF000_E_(LIN COMM)_250620.docx", "_Ref1"),
    ]


def test_bom_does_not_hide_first_heading(tmp_path):
    md = tmp_path / "bom.md"
    md.write_bytes("﻿# 1 First\n\nText\n".encode("utf-8"))
    assert [h.title for h in parse_file(md).headings] == ["1 First"]


ANCHORS = FIXTURES / "DMC" / "9999ZXXXXC000_E_(Demo Anchors)_260101.md"


def test_anchor_placement_and_html_tags():
    doc = parse_file(ANCHORS)
    by_anchor = {a.anchor: a for a in doc.anchor_defs}
    titles = {h.index: h.title for h in doc.headings}
    # alone on the line before a heading -> belongs to that heading, not the previous section
    assert by_anchor["_Toc500001"].placement == "before_heading"
    assert titles[doc.anchors["_Toc500001"]] == "1 Overview"
    assert by_anchor["_Toc500003"].placement == "before_heading"
    assert titles[doc.anchors["_Ref500004"]] == "1.2 Abnormal Checksum Detection"
    assert by_anchor["_Ref500002"].placement == "after_heading"
    assert titles[doc.anchors["_Ref500002"]] == "1.1 Scope and Limits"
    # id on any tag, and inside HTML tables
    assert by_anchor["_Ref500010"].syntax == "html:p" and by_anchor["_Ref500010"].placement == "inline"
    assert by_anchor["_Ref500020"].placement == "table"
    assert "_Ref500030" not in doc.anchors  # w:name is not an HTML id/name attribute
    assert doc.headings[0].anchors == ["_Toc500001"]


def test_implicit_heading_slugs():
    doc = parse_file(ANCHORS)
    titles = {h.index: h.title for h in doc.headings}
    assert titles[doc.resolve("abnormal-checksum-detection")[1]] == "1.2 Abnormal Checksum Detection"
    assert titles[doc.resolve("overview-1")[1]] == "2 Overview"  # pandoc de-duplication
    assert titles[doc.resolve("11-scope-and-limits")[1]] == "1.1 Scope and Limits"  # GitHub style
    assert doc.resolve("_Ref599999") == (False, None)


def test_profile_diagnose_is_redacted():
    report = profile_docs([parse_file(ANCHORS)], [100], diagnose=True)
    f = report["files"][0]
    assert f["links"]["internal_resolved_by_slug"] == 3
    assert f["links"]["internal_unresolved_sample"] == ["_Ref500030", "_Ref599999", "abnormal-checksum-detect"]
    assert f["doc_number_mentions"] == {"7821ZXXXXF000": 2}
    assert f["anchors"]["placement"]["before_heading"] == 3

    diag = f["diagnose_unresolved"]
    assert (diag["present_but_unrecognised"], diag["absent_slug_like"], diag["absent_other"]) == (1, 1, 1)
    skeleton = diag["samples"][0]["skeleton"]
    assert "{ANCHOR}" in skeleton and "bookmarkStart" in skeleton
    assert "converter" not in skeleton and "markup" not in skeleton.lower()
    assert diag["slug_samples"][0]["closest_heading_slug"] == "abnormal-checksum-detection"
    assert diag["absent_samples"] == ["_Ref599999"]


def test_over_threshold_sample_uses_numbers_not_titles():
    split = profile_docs([parse_file(ANCHORS)], [20])["files"][0]["split_simulation"]["20"]
    assert split["over_sample"]
    assert all(set(o["heading"]) <= set("0123456789.Hpreamble@line") for o in split["over_sample"])
