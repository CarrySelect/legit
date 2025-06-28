import os
from pathlib import Path

from legit.blob import Blob
from legit.tree import DatabaseEntry
from legit.database import Database
from legit.index import Index
from legit.refs import Refs
from legit.workspace import Workspace
from legit.status import Status
from legit.migration import Migration


class Repository:
    def __init__(self, git_path: Path):
        self.git_path: Path = git_path
        self.database: Database = Database(git_path / "objects")
        self.index: Index = Index(git_path / "index")
        self.refs: Refs = Refs(git_path)
        self.workspace: Workspace = Workspace(git_path.parent)

    def status(self) -> Status:
        return Status(self)

    def migration(self, tree_diff: dict[Path, list[DatabaseEntry]]) -> 'Migration':
        return Migration(self, tree_diff)

    def pending_commit(self) -> 'PendingCommit':
        return PendingCommit(self.git_path)


class PendingCommit:
    def __init__(self, path: Path) -> None:
        self.head_path = path / "MERGE_HEAD"
        self.message_path = path / "MERGE_MSG"
    
    @property
    def merge_oid(self):
        try:
            return self.head_path.read_text().strip()
        except FileNotFoundError:
            name = self.head_path.name
            raise Exception(f"There is no merge in progress ({name} missing).")

    @property
    def merge_message(self):
        return self.message_path.read_text()
    
    def start(self, oid: str, msg: str) -> None:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        with os.fdopen(os.open(self.head_path, flags, 0o644), "w") as f:
            f.write(oid)
        with os.fdopen(os.open(self.message_path, flags, 0o644), "w") as f:
            f.write(msg)

    def clear(self) -> None:
        self.head_path.unlink()
        self.message_path.unlink()

    def is_in_progress(self) -> bool:
        return self.head_path.exists()
