from pathlib import Path
from typing import Optional, cast, TYPE_CHECKING

from legit.blob import Blob
from legit.commit import Commit

if TYPE_CHECKING:
    from legit.database import Database
else:
    Database = None

from legit.index import Entry
from legit.tree import DatabaseEntry, Tree


class TreeDiff:
    def __init__(self, database: Database) -> None:
        self.database: Database = database
        self.changes: dict[Path, list[Optional[DatabaseEntry]]] = {}

    def compare_oids(self, a: Optional[str], b: Optional[str], prefix: Path = Path()) -> None:
        if a == b:
            return

        a_tree = self.oid_to_tree(a)
        assert a_tree is not None
        a_entries = cast(dict[Path, DatabaseEntry], a_tree.entries if a is not None else {})

        b_tree = self.oid_to_tree(b)
        assert b_tree is not None
        b_entries = cast(dict[Path, DatabaseEntry], b_tree.entries if b is not None else {})

        self.detect_deletions(a_entries, b_entries, prefix)
        self.detect_additions(a_entries, b_entries, prefix)

    def oid_to_tree(self, oid: Optional[str]) -> Optional[Tree]:
        assert oid is not None

        obj = self.database.load(oid)

        if obj.type() == 'commit':
            assert not isinstance(obj, Blob)
            assert not isinstance(obj, Tree)
            assert isinstance(obj, Commit)
            tree = self.database.load(obj.tree)
            assert isinstance(tree, Tree)
            return tree
        elif obj.type() == 'tree':
            assert not isinstance(obj, Blob)
            assert not isinstance(obj, Commit)
            assert isinstance(obj, Tree)
            return obj
        else:
            return None

    def detect_deletions(self, a: dict[Path, DatabaseEntry], b: dict[Path, DatabaseEntry], prefix: Path = Path()) -> None:
        for name, entry in a.items():
            path = prefix / name
            other = b.get(name)

            if entry == other:
                continue

            tree_a = entry.oid if entry is not None and entry.is_tree() else None
            tree_b = other.oid if other is not None and other.is_tree() else None

            self.compare_oids(tree_a, tree_b, path)

            blobs = [
                None if entry is not None and entry.is_tree() else entry,
                None if other is not None and other.is_tree() else other,
            ]

            if any(blobs):
                self.changes[path] = blobs

    def detect_additions(self, a: dict[Path, DatabaseEntry], b: dict[Path, DatabaseEntry], prefix: Path = Path()) -> None:
        for name, entry in b.items():
            path = prefix / name
            other = a.get(name)

            if other is not None:
                continue

            if entry.is_tree():
                self.compare_oids(None, entry.oid, path)
            else:
                self.changes[path] = [None, entry]

