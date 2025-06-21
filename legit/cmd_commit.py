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

class Commit(Base):
    def __init__(
        self,
        _dir: Path,
        env: MutableMapping[str, str],
        args: list[str],
        stdin: TextIO,
        stdout: TextIO,
        stderr: TextIO,
    ) -> None:
        super().__init__(_dir, env, args, stdin, stdout, stderr)

    def run(self) -> None:
        repo = Repository(self.dir / ".git")

        repo.index.load()

        root = Tree.from_entries(repo.index.entries)
        root.traverse(lambda tree: repo.database.store(tree))

        try:
            parent: str | None = repo.refs.read_head()
        except FileNotFoundError:
            parent = None

        name: str = os.environ["GIT_AUTHOR_NAME"]
        email: str = os.environ["GIT_AUTHOR_EMAIL"]
        author: Author = Author(name, email, datetime.now().astimezone())
        message: str = self.stdin.read()
    
        assert root.oid is not None
        commit = CommitObject(parent, root.oid, author, message)
        repo.database.store(commit)
        
        repo.refs.update_head(commit.oid)

        is_root: str = "(root-commit)" if parent is None else ""
        print(f"[{is_root} {commit.oid}] {message.splitlines()[0]}")

