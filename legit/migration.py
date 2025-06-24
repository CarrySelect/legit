from legit.blob import Blob
from typing import TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from legit.repository import Repository
else:
    Repository = None


class Migration:
    def __init__(self, repo: Repository, tree_diff) -> None:
        self.repo: Repository = repo
        self.tree_diff = tree_diff
        self.changes = {k: [] for k in ("create", "update", "delete")}
        self.mkdirs = set()
        self.rmdirs = set()

    def blob_data(self, oid: str) -> str:
        blob = self.repo.database.load(oid)
        assert isinstance(blob, Blob)
        return blob.data

    def apply_changes(self) -> None:
        self.plan_changes()
        self.update_workspace()

    def plan_changes(self) -> None:
        for path, (old_item, new_item) in self.tree_diff.items():
            self.record_change(path, old_item, new_item)

    @staticmethod
    def _ancestor_dirs(p: Path) -> list[Path]:
        return list(reversed([parent for parent in p.parents if parent != Path(".")]))

    def record_change(self, path, old_item, new_item) -> None:
        dir_chain = self._ancestor_dirs(path.parent)

        if old_item is None:
            self.mkdirs.update(dir_chain)
            action = "create"
        elif new_item is None:
            self.rmdirs.update(dir_chain)
            action = "delete"
        else:
            self.mkdirs.update(dir_chain)
            action = "update"

        self.changes[action].append((path, new_item))

    def update_workspace(self) -> None:
        self.repo.workspace.apply_migration(self)
