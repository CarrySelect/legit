import re
from pathlib import Path
from collections import defaultdict
from sys import is_stack_trampoline_active
from typing import Any, Generator, Optional
from legit.commit import Commit
from legit.revision import Revision
from legit.repository import Repository
from legit.pathfilter import PathFilter


class RevList:
    RANGE = re.compile(r"^(.*)\.\.(.*)$")
    EXCLUDE = re.compile(r"^\^(.+)$")

    def __init__(self, repo: Repository, revs: list[str]) -> None:
        self.repo: Repository = repo
        self.commits: dict[str, Any] = {}
        self.flags = defaultdict(set)
        self.limited: bool = False
        self.output = []
        self.queue = []
        self.prune = []
        self.diffs = {}

        for rev in revs:
            self.handle_revision(rev)

        if not self.queue:
            self.handle_revision("HEAD")

        self.filter = PathFilter.build(self.prune)
    
    def tree_diff(self, old_oid, new_oid):
        key = (old_oid, new_oid)
        if key not in self.diffs:
            self.diffs[key] = self.repo.database.tree_diff(
                old_oid, new_oid, self.filter
            )
        return self.diffs[key]

    def load_commit(self, oid: Optional[str]) -> None:
        if oid is None:
            return

        assert oid is not None
        self.commits[oid] = self.repo.database.load(oid)
        return self.commits[oid]

    def mark(self, oid: str, flag: str) -> bool:
        if flag in self.flags[oid]:
            return False
        self.flags[oid].add(flag)
        return True

    def is_marked(self, oid: str, flag: str) -> bool:
        return flag in self.flags[oid]

    def handle_revision(self, rev):
        if self.repo.workspace.stat_file(rev) is not None:
            self.prune.append(Path(rev))
        elif m := RevList.RANGE.match(rev):
            self.set_start_point(m.group(1), False)
            self.set_start_point(m.group(2), True)
        elif m := RevList.EXCLUDE.match(rev):
            self.set_start_point(m.group(1), False)
        else:
            self.set_start_point(rev, True)

    def set_start_point(self, rev, interesting):
        if not rev:
            rev = "HEAD"
        
        oid = Revision(self.repo, rev).resolve(Revision.COMMIT)

        commit = self.load_commit(oid)
        self.enqueue_commit(commit)

        if not interesting:
            self.limited = True
            self.mark(oid, "uninteresting")
            self.mark_parents_uninteresting(commit)

    def mark_parents_uninteresting(self, commit):
        """
        Walk up the chain of parents, marking each one ‘uninteresting’,
        stopping as soon as mark(...) returns False or there’s no parent.
        """
        # While we still have a commit and it has a parent...
        while commit is not None and commit.parent is not None:
            # If marking the parent fails (already marked), stop.
            if not self.mark(commit.parent, 'uninteresting'):
                break
            # Move up to the parent commit object
            commit = self.commits.get(commit.parent)

    def enqueue_commit(self, commit):
        if not self.mark(commit.oid, "seen"):
            return

        index = next(
            (i for i, c in enumerate(self.queue) if c.date() < commit.date()),
            None
        )

        pos = index if index is not None else len(self.queue)
        self.queue.insert(pos, commit)

    def each(self) -> Generator[Commit]:
        if self.limited:
            self.limit_list()

        for commit in self.traverse_commits():
            yield commit

    def limit_list(self):
        while self.still_interesting():
            commit = self.queue.pop(0)
            self.add_parents(commit)

            if not self.is_marked(commit.oid, "uninteresting"):
                self.output.append(commit)
        
        self.queue = self.output

    def still_interesting(self) -> bool:
        # If there’s nothing queued, it can’t be interesting.
        if not self.queue:
            return False

        # The last output vs the first queued
        oldest_out = self.output[-1] if self.output else None
        newest_in  = self.queue[0]

        # If the most‐recently‐output commit is older (or equal) than
        # the next one coming in, we’re still in order => still interesting.
        if oldest_out and oldest_out.date() <= newest_in.date():
            return True

        # Otherwise, if there’s any commit in the queue that isn’t marked
        # uninteresting, we’re still interested.
        if any(not self.is_marked(c.oid, 'uninteresting') for c in self.queue):
            return True

        # Otherwise, nothing left that’s interesting
        return False

    def traverse_commits(self):
        """
        Yield each commit in queue order, after optionally adding parents,
        but skip any already marked uninteresting.
        """
        while self.queue:
            commit = self.queue.pop(0)
            if not self.limited:
                self.add_parents(commit)
            if self.is_marked(commit.oid, 'uninteresting'):
                continue
            if self.is_marked(commit.oid, 'treesame'):
                continue
            yield commit
            
    def add_parents(self, commit):
        if not self.mark(commit.oid, "added"):
            return

        parent = self.load_commit(commit.parent)
    
        if self.is_marked(commit.oid, "uninteresting"):
            if parent is not None:
                self.mark_parents_uninteresting(parent)
        else:
            self.simplify_commit(commit)

        if parent is not None:
            self.enqueue_commit(parent)

    def simplify_commit(self, commit):
        if not self.prune:
            return

        diff = self.tree_diff(commit.parent, commit.oid)

        if not diff:
            self.mark(commit.oid, "treesame")

