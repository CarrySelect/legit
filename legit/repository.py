import os
from pathlib import Path
from typing import Optional

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

    def status(self, commit_oid: Optional[str] = None) -> Status:
        return Status(self, commit_oid)

    def migration(self, tree_diff: dict[Path, list[DatabaseEntry]]) -> 'Migration':
        return Migration(self, tree_diff)

    def pending_commit(self) -> 'PendingCommit':
        return PendingCommit(self.git_path)

    def hard_reset(self, oid: str) -> None:
        HardReset(self, oid).execute()


class HardReset:
    def __init__(self, repo: Repository, oid: str) -> None:
        self.repo = repo
        self.oid = oid

    def execute(self) -> None:
        self.status = self.repo.status(self.oid)
        changed = [Path(path) for path in self.status.changed]

        for path in changed:
            self.reset_path(path)

    def reset_path(self, path: Path) -> None:
        self.repo.index.remove(path)
        self.repo.workspace.remove(path)

        entry = self.status.head_tree.get(path)
        if entry is None:
            return

        blob = self.repo.database.load(entry.oid)
        self.repo.workspace.write_file(path, blob.data, entry.mode, True)

        stat = self.repo.workspace.stat_file(path)
        self.repo.index.add(path, entry.oid, stat)

class PendingCommit:
    class Error(Exception):
        pass
    
    HEAD_FILES = {
        "merge": "MERGE_HEAD",
        "cherry_pick": "CHERRY_PICK_HEAD",
    }

    def __init__(self, path: Path) -> None:
        self.path = path
        self.message_path = path / "MERGE_MSG"
    
    @property
    def merge_oid(self, ty: str = "merge"):
        head_path = self.path / PendingCommit.HEAD_FILES[ty]
        try:
            return head_path.read_text().strip()
        except FileNotFoundError:
            name = head_path.name
            raise PendingCommit.Error(f"There is no merge in progress ({name} missing).")

    @property
    def merge_message(self):
        return self.message_path.read_text()
    
    def start(self, oid: str, ty: str = "merge") -> None:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        with os.fdopen(os.open(PendingCommit.HEAD_FILES[ty], flags, 0o644), "w") as f:
            f.write(oid)

    def clear(self, ty: str = "merge") -> None:
        head_path = self.path / PendingCommit.HEAD_FILES[ty]
        try:
            head_path.unlink()
            self.message_path.unlink()
        except FileNotFoundError:
            name = head_path.name
            raise PendingCommit.Error(f"There is no merge to abort ({name} missing).")

    def is_in_progress(self) -> bool:
        return self.merge_type() is not None

    def merge_type(self) -> Optional[str]:
        for ty, name in PendingCommit.HEAD_FILES.items():
            path = self.path / name
            if path.exists():
                return ty
        return None
