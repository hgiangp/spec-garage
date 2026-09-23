"""Section IDs and the per-spec manifest (D2, D3).

An ID is ``<CODE>-<NNNN>``: CODE from specs.yaml, NNNN a per-spec counter whose width (4 or 5 digits)
is fixed for the whole spec. IDs carry no meaning, are never renumbered and never reused.

``data/vault/<CODE>/_manifest.yaml`` holds the note tree (document order), ``next_id`` and the
retired IDs. It is the only source of ordering for export.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .config import DATA_DIR

MANIFEST = "_manifest.yaml"
ID_RE = re.compile(r"^([A-Z]{2,5})-(\d{4,5})$")


class IdError(ValueError):
    pass


def format_id(code: str, number: int, width: int) -> str:
    if number >= 10 ** width:
        raise IdError(f"{code}: số {number} vượt quá {width} chữ số (id_width)")
    return f"{code}-{number:0{width}d}"


def parse_id(section_id: str) -> tuple[str, int]:
    m = ID_RE.match(section_id)
    if not m:
        raise IdError(f"ID sai format: {section_id!r} (cần <CODE>-<NNNN>)")
    return m.group(1), int(m.group(2))


def width_for(heading_count: int) -> int:
    """ID width for a new spec: 4 digits unless the spec has more headings than that allows (D2)."""
    return 4 if heading_count < 10 ** 4 else 5


@dataclass
class Node:
    id: str
    children: list[Node] = field(default_factory=list)


@dataclass
class Retired:
    id: str
    merged_into: str | None = None
    reason: str = ""


@dataclass
class Manifest:
    spec: str
    next_id: int = 1
    id_width: int = 4
    source: str = ""
    source_sha256: str = ""
    built_with: str = ""
    max_tokens: int | None = None
    tree: list[Node] = field(default_factory=list)
    retired: list[Retired] = field(default_factory=list)

    # ── IDs ─────────────────────────────────────────────────────────────────────

    def allocate(self, n: int = 1) -> list[str]:
        if n < 1:
            raise IdError("n phải ≥ 1")
        ids = [format_id(self.spec, self.next_id + i, self.id_width) for i in range(n)]
        self.next_id += n
        return ids

    def check_id(self, section_id: str) -> int:
        """Validate that an ID belongs to this spec and has been allocated; return its number."""
        code, number = parse_id(section_id)
        if code != self.spec:
            raise IdError(f"{section_id} không thuộc spec {self.spec}")
        if len(section_id) - len(code) - 1 != self.id_width:
            raise IdError(f"{section_id}: sai độ rộng, spec {self.spec} dùng {self.id_width} chữ số")
        if number >= self.next_id:
            raise IdError(f"{section_id} chưa được cấp (next_id = {self.next_id})")
        return number

    def is_retired(self, section_id: str) -> bool:
        return any(r.id == section_id for r in self.retired)

    # ── Tree ────────────────────────────────────────────────────────────────────

    def walk(self) -> Iterator[tuple[Node, str | None, int]]:
        """Yield (node, parent id, depth) in document order."""
        def go(nodes: list[Node], parent: str | None, depth: int):
            for node in nodes:
                yield node, parent, depth
                yield from go(node.children, node.id, depth + 1)
        yield from go(self.tree, None, 0)

    def ids(self) -> list[str]:
        return [node.id for node, _, _ in self.walk()]

    def find(self, section_id: str) -> Node | None:
        return next((node for node, _, _ in self.walk() if node.id == section_id), None)

    def parent_of(self, section_id: str) -> str | None:
        for node, parent, _ in self.walk():
            if node.id == section_id:
                return parent
        raise IdError(f"{section_id} không có trong tree")

    def _siblings(self, parent: str | None) -> list[Node]:
        if parent is None:
            return self.tree
        node = self.find(parent)
        if node is None:
            raise IdError(f"parent {parent} không có trong tree")
        return node.children

    def add(self, section_id: str, parent: str | None = None, after: str | None = None) -> None:
        """Insert a note into the tree: under `parent`, right after sibling `after` (else last)."""
        self.check_id(section_id)
        if self.find(section_id) is not None:
            raise IdError(f"{section_id} đã có trong tree")
        if self.is_retired(section_id):
            raise IdError(f"{section_id} đã retire, không dùng lại")
        siblings = self._siblings(parent)
        pos = len(siblings)
        if after is not None:
            idx = next((i for i, s in enumerate(siblings) if s.id == after), None)
            if idx is None:
                raise IdError(f"{after} không phải con của {parent or 'gốc'}")
            pos = idx + 1
        siblings.insert(pos, Node(section_id))

    def remove(self, section_id: str) -> None:
        """Remove a leaf note from the tree. Children must be moved or removed first."""
        node = self.find(section_id)
        if node is None:
            raise IdError(f"{section_id} không có trong tree")
        if node.children:
            raise IdError(f"{section_id} còn {len(node.children)} note con")
        self._siblings(self.parent_of(section_id)).remove(node)

    def retire(self, section_id: str, merged_into: str | None = None, reason: str = "") -> None:
        """Retire an ID for good (deleted or merged). A note still in the tree is removed from it."""
        self.check_id(section_id)
        if self.is_retired(section_id):
            raise IdError(f"{section_id} đã retire")
        if not merged_into and not reason:
            raise IdError("retire cần merged_into hoặc reason")
        if merged_into is not None:
            if merged_into == section_id:
                raise IdError("merged_into không thể là chính nó")
            self.check_id(merged_into)
            if self.is_retired(merged_into):
                raise IdError(f"{merged_into} đã retire")
        if self.find(section_id) is not None:
            self.remove(section_id)
        self.retired.append(Retired(section_id, merged_into, reason))

    # ── Serialisation ───────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        def dump(nodes: list[Node]) -> list:
            return [{n.id: dump(n.children)} if n.children else n.id for n in nodes]

        data: dict = {"spec": self.spec}
        for key in ("source", "source_sha256", "built_with", "max_tokens"):
            value = getattr(self, key)
            if value not in ("", None):
                data[key] = value
        data["id_width"] = self.id_width
        data["next_id"] = self.next_id
        data["tree"] = dump(self.tree)
        data["retired"] = [
            {k: v for k, v in (("id", r.id), ("merged_into", r.merged_into), ("reason", r.reason)) if v}
            for r in self.retired
        ]
        return data

    @classmethod
    def from_dict(cls, data: dict) -> Manifest:
        def load(items: list | None) -> list[Node]:
            nodes = []
            for item in items or []:
                if isinstance(item, str):
                    nodes.append(Node(item))
                elif isinstance(item, dict) and len(item) == 1:
                    (node_id, children), = item.items()
                    nodes.append(Node(node_id, load(children)))
                else:
                    raise IdError(f"tree: phần tử không hợp lệ: {item!r}")
            return nodes

        m = cls(
            spec=data["spec"],
            next_id=int(data.get("next_id", 1)),
            id_width=int(data.get("id_width", 4)),
            source=data.get("source", ""),
            source_sha256=data.get("source_sha256", ""),
            built_with=data.get("built_with", ""),
            max_tokens=data.get("max_tokens"),
            tree=load(data.get("tree")),
            retired=[Retired(r["id"], r.get("merged_into"), r.get("reason", "")) for r in data.get("retired") or []],
        )
        seen: set[str] = set()
        for section_id in m.ids():
            m.check_id(section_id)
            if section_id in seen:
                raise IdError(f"tree: {section_id} xuất hiện hai lần")
            if m.is_retired(section_id):
                raise IdError(f"tree: {section_id} đã retire nhưng vẫn còn trong tree")
            seen.add(section_id)
        return m


def manifest_path(root: Path, code: str) -> Path:
    return root / DATA_DIR / "vault" / code / MANIFEST


def load_manifest(path: Path) -> Manifest:
    if not path.is_file():
        raise IdError(f"Không có manifest: {path}. Chạy `sg build-vault` trước.")
    return Manifest.from_dict(yaml.safe_load(path.read_text(encoding="utf-8")) or {})


def save_manifest(manifest: Manifest, path: Path) -> None:
    """Write atomically so an interrupted run never leaves a half-written manifest."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".yaml.tmp")
    text = yaml.safe_dump(manifest.to_dict(), sort_keys=False, allow_unicode=True, width=1000)
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def allocate_ids(root: Path, code: str, n: int = 1) -> list[str]:
    """Allocate IDs and persist next_id immediately (used by `sg new-id`)."""
    path = manifest_path(root, code)
    manifest = load_manifest(path)
    ids = manifest.allocate(n)
    save_manifest(manifest, path)
    return ids
