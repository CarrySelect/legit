from collections import defaultdict
from legit.commit import Commit
from legit.database import Database


class CommonAncestors:
    def __init__(self, database: Database, one: str, two: str) -> None:
        self.database: Database = database
        self.flags = defaultdict(set)
        self.queue = []

        self.insert_by_date(self.queue, self.database.load(one))
        self.flags[one].add("parent1")

        self.insert_by_date(self.queue, self.database.load(two))
        self.flags[two].add("parent2")

    def insert_by_date(self, structure, commit) -> None:
        index = next(
            (i for i, c in enumerate(structure) if c.date() < commit.date()),
            None,
        )
        pos = index if index is not None else len(structure)
        structure.insert(pos, commit)

    def find(self) -> str:
        while self.queue:
            commit = self.queue.pop(0)
            flags = self.flags[commit.oid]

            if flags == set(["parent1", "parent2"]):
                return commit.oid

            self.add_parents(commit, flags)

    def add_parents(self, commit: Commit, flags: set[str]) -> None:
        if commit.parent is None:
            return

        parent = self.database.load(commit.parent)
        if self.flags[parent.oid].issuperset(flags):
            return

        self.flags[parent.oid].update(flags)
        self.insert_by_date(self.queue, parent)
