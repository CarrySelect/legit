import os
import stat
from pathlib import Path
from typing import TYPE_CHECKING, Optional


if TYPE_CHECKING:
    from legit.repository import Repository
else:
    Repository = None


from legit.blob import Blob


class Inspector:
    def __init__(self, repo: Repository) -> None:
        self.repo: Repository = repo

    def compare_index_to_workspace(self, entry, stat: os.stat_result | None) -> Optional[str]:
        if entry is None:
            return "untracked"

        if stat is None:
            return "deleted"

        if not entry.stat_match(stat):
            return "modified"

        if entry.times_match(stat):
            return None

        data = self.repo.workspace.read_file(entry.path)
        blob = Blob(data)
        oid = self.repo.database.hash_object(blob)

        if entry.oid != oid:
            return "modified"

    def compare_tree_to_index(self, item, entry) -> Optional[str]:
        if item is None and entry is None:
            return None

        if item is None:
            return "added"

        if entry is None:
            return "deleted"

        if entry.mode() != item.mode or entry.oid != item.oid:
            return "modified"

    def _is_trackable_file(self, path: Path, stat: os.stat_result) -> bool:
        if self._is_file(stat):
            return not self.repo.index.is_tracked(path)
        
        if not self._is_dir(stat):
            return False
        
        items = self.repo.workspace.list_dir(str(path))
        files = [(k, v) for k, v in items.items() if self._is_file(v)]
        dirs = [(k, v) for k, v in items.items() if self._is_dir(v)]

        for x in (files, dirs):
            for child_path, child_stat in x:
                if self._is_trackable_file(child_path, child_stat):
                    return True

        return False
 
    def _is_file(self, stat_result: os.stat_result) -> bool:
        return stat.S_ISREG(stat_result.st_mode)

    def _is_dir(self, stat_result: os.stat_result) -> bool:
        return stat.S_ISDIR(stat_result.st_mode)
