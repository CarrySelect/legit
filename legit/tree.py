from legit.index import Entry
from typing import Callable, MutableMapping
from pathlib import Path

class Tree:
    def __init__(self) -> None:
        self.entries: MutableMapping[str, 'Entry | Tree'] = {}
        self.oid = None

    @classmethod
    def from_entries(cls, entries: dict[Path, Entry]) -> 'Tree':
        entries = dict(sorted(entries.items(), key=lambda x: x[1].path))

        root = Tree()

        for _, entry in entries.items():
            root.add_entry(entry.parent_directories(), entry)

        return root
    
    def add_entry(self, parents: list[Path], entry: Entry) -> None:
        if not parents:
            self.entries[entry.basename()] = entry
        else:
            head = parents[0]
            tree = self.entries.setdefault(str(head.name), Tree())
            assert isinstance(tree, Tree)
            tree.add_entry(parents[1:], entry)

    def type(self) -> str:
        return "tree"

    def to_bytes(self) -> bytes:
        parts = []
        for name, entry in sorted(self.entries.items()):
            if isinstance(entry, Tree):
                mode_str = '40000'
                assert entry.oid is not None
                oid = entry.oid
            else:
                m = entry.mode()
                mode_str = oct(m)[2:]
                oid = entry.oid

            header = f"{mode_str} {name}".encode("utf-8") + b"\x00"
            sha = bytes.fromhex(oid)
            parts.append(header + sha)
        return b"".join(parts)

    def traverse(self, code: Callable[['Tree'], None]) -> None:
        for name, entry in self.entries.items():
            if isinstance(entry, Tree):
                entry.traverse(code)
        code(self)


