from datetime import datetime
import os
import sys
from typing import MutableMapping, TextIO
from pathlib import Path
from legit.repository import Repository
from legit.tree import Tree
from legit.author import Author
from legit.commit import Commit as CommitObject
from legit.cmd_base import Base
from legit.write_commit import WriteCommitMixin


class Commit(WriteCommitMixin, Base):
    def run(self) -> None:
        self.define_write_commit_options()

        self.repo = Repository(self.dir / ".git")
        self.repo.index.load()

        if self.repo.pending_commit().is_in_progress():
            self.resume_merge()

        parent = self.repo.refs.read_head()
        message: str = self.read_message()
        commit = self.write_commit([parent] if parent else [], message)
        
        self.print_commit(commit)

        self.exit(0)

