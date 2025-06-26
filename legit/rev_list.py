from collections import defaultdict
from typing import Any, Generator, Optional
from legit.commit import Commit
from legit.revision import Revision
from legit.repository import Repository


class RevList:
    def __init__(self, repo: Repository, revs: list[str]) -> None:
        self.repo: Repository = repo
        self.commits: dict[str, Any] = {}
        self.flags = defaultdict(set)
        self.queue = []

    def load_commit(self, oid: Optional[str]) -> None:
        if oid is None:
            return

        assert oid is not None
        self.commits[oid] = self.repo.database.load(oid)

    def mark(self, oid: str, flag: str) -> bool:
        if flag in self.flags[oid]:
            return False
        self.flags[oid].add(flag)
        return True

    def is_marked(self, oid: str, flag: str) -> bool:
        return flag in self.flags[oid]

    def handle_revision(self, rev):
        oid = Revision(self.repo, rev).resolve(Revision.COMMIT)

        commit = self.load_commit(oid)
        self.enqueue_commit(commit)

    def enqueue_commit(self, commit):
        if not self.mark(commit.oid, "seen"):
            return

        index = next(
            (i for i, c in enumerate(self.queue) if c.date < commit.date),
            None
        )

        pos = index if index is not None else len(self.queue)
        self.queue.insert(pos, commit)

    def each(self) -> Generator[Commit]:
        for commit in self.traverse_commits():
            yield commit

    def traverse_commits(self):
        while self.queue:
            commit = self.queue.pop(0)
            self.add_parents(commit)
            yield commit

    def add_parents(self, commit):
        if not self.mark(commit.oid, "added"):
            return

        parent = self.load_commit(commit.parent)
        
        if parent is not None:
            self.enqueue_commit(parent)
