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
        self.repo = Repository(self.dir / ".git")
        
        self.repo.index.load()
        parent = self.repo.refs.read_head()
        message: str = self.stdin.read()
        commit = self.write_commit([parent] if parent else [], message)
    
        is_root: str = "(root-commit) " if parent is None else ""
        self.println(f"[{is_root}{commit.oid}] {message.splitlines()[0]}")

        self.exit(0)

