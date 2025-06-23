from pathlib import Path

from legit.database import Database
from legit.index import Index
from legit.refs import Refs
from legit.workspace import Workspace
from legit.status import Status


class Repository:
    def __init__(self, git_path: Path):
        self.git_path: Path = git_path
        self.database: Database = Database(git_path / "objects")
        self.index: Index = Index(git_path / "index")
        self.refs: Refs = Refs(git_path)
        self.workspace: Workspace = Workspace(git_path.parent)

    def status(self) -> Status:
        return Status(self)
