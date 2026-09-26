import pytest
import yaml

from specgarage.cli import main
from specgarage.ids import (
    IdError, Manifest, Node, allocate_ids, format_id, load_manifest, manifest_path, parse_id,
    save_manifest, width_for,
)

TREE_YAML = """
spec: WRN
source: data/sources/WRN/w.md
max_tokens: 3000
id_width: 4
next_id: 8
tree:
  - WRN-0000
  - WRN-0001:
      - WRN-0002
      - WRN-0004:
          - WRN-0005
  - WRN-0006
retired:
  - {id: WRN-0003, merged_into: WRN-0002}
"""


def sample() -> Manifest:
    return Manifest.from_dict(yaml.safe_load(TREE_YAML))


def test_format_and_parse():
    assert format_id("WRN", 42, 4) == "WRN-0042"
    assert format_id("LIN", 42, 5) == "LIN-00042"
    assert parse_id("EWA-0017") == ("EWA", 17)
    for bad in ("wrn-0001", "WRN-12", "WRN0001", "TOOLONG-0001"):
        with pytest.raises(IdError):
            parse_id(bad)
    assert width_for(9999) == 4 and width_for(10000) == 5


def test_allocate_is_sequential_and_bounded():
    m = Manifest(spec="WRN", next_id=9998)
    assert m.allocate() == ["WRN-9998"]
    assert m.allocate() == ["WRN-9999"]
    with pytest.raises(IdError):
        m.allocate()  # width is fixed for the spec; never silently switch to 5 digits
    wide = Manifest(spec="WRN", next_id=9999, id_width=5)
    assert wide.allocate(2) == ["WRN-09999", "WRN-10000"]


def test_walk_order_and_parents():
    m = sample()
    assert m.ids() == ["WRN-0000", "WRN-0001", "WRN-0002", "WRN-0004", "WRN-0005", "WRN-0006"]
    assert [d for _, _, d in m.walk()] == [0, 0, 1, 1, 2, 0]
    assert m.parent_of("WRN-0005") == "WRN-0004"
    assert m.parent_of("WRN-0001") is None


def test_add_positions_and_rules():
    m = sample()
    new, = m.allocate()
    m.add(new, parent="WRN-0001", after="WRN-0002")
    assert m.ids()[:4] == ["WRN-0000", "WRN-0001", "WRN-0002", new]
    with pytest.raises(IdError):
        m.add(new)  # already in tree
    with pytest.raises(IdError):
        m.add("WRN-0003")  # retired
    with pytest.raises(IdError):
        m.add("WRN-0099")  # not allocated
    with pytest.raises(IdError):
        m.add("LIN-0001")  # other spec


def test_remove_and_retire():
    m = sample()
    with pytest.raises(IdError):
        m.remove("WRN-0004")  # has children
    m.retire("WRN-0005", merged_into="WRN-0004")
    assert "WRN-0005" not in m.ids()
    assert m.is_retired("WRN-0005")
    with pytest.raises(IdError):
        m.retire("WRN-0005", reason="again")
    with pytest.raises(IdError):
        m.retire("WRN-0006")  # needs a reason or merged_into
    with pytest.raises(IdError):
        m.retire("WRN-0006", merged_into="WRN-0003")  # target retired
    m.retire("WRN-0006", reason="obsolete")
    assert m.allocate() == ["WRN-0008"]  # retired numbers are never handed out again


def test_from_dict_rejects_inconsistent_trees():
    for tree in ("[WRN-0001, WRN-0001]", "[WRN-0003]", "[WRN-0100]", "[{WRN-0001: [LIN-0001]}]"):
        data = yaml.safe_load(TREE_YAML)
        data["tree"] = yaml.safe_load(tree)
        with pytest.raises(IdError):
            Manifest.from_dict(data)


def test_save_load_roundtrip(tmp_path):
    path = tmp_path / "_manifest.yaml"
    m = sample()
    save_manifest(m, path)
    assert load_manifest(path) == m
    assert list(yaml.safe_load(path.read_text(encoding="utf-8"))) == [
        "spec", "source", "max_tokens", "id_width", "next_id", "tree", "retired",
    ]
    assert not path.with_suffix(".yaml.tmp").exists()


def test_allocate_ids_persists_and_cli(tmp_path, monkeypatch, capsys):
    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "data" / "specs.yaml").write_text("specs: []\n", encoding="utf-8")
    path = manifest_path(tmp_path, "WRN")
    save_manifest(Manifest(spec="WRN", next_id=5, tree=[Node("WRN-0001")]), path)

    assert allocate_ids(tmp_path, "WRN", 2) == ["WRN-0005", "WRN-0006"]
    assert load_manifest(path).next_id == 7

    monkeypatch.chdir(tmp_path)
    assert main(["new-id", "WRN", "-n", "2"]) == 0
    assert capsys.readouterr().out.split() == ["WRN-0007", "WRN-0008"]
    assert main(["new-id", "LIN"]) == 1  # no vault yet
    assert "build-vault" in capsys.readouterr().err
