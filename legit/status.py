import os
import stat
from pathlib import Path
from typing import (
    MutableMapping,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from legit.repository import Repository
else:
    Repository = None

from legit.tree import DatabaseEntry
from legit.commit import Commit
from legit.tree import Tree
from legit.blob import Blob
from legit.index import Entry


class Status:
    def __init__(self, repo: Repository) -> None:
        self.repo = repo
        self.stats: MutableMapping[Path, os.stat_result] = {}
        self.index_changes: MutableMapping[str, str] = {}
        self.workspace_changes: MutableMapping[str, str] = {}
        self.changed: set[str] = set()
        self.untracked: set[str] = set()
        self.head_tree: MutableMapping[Path, DatabaseEntry] = {}

        self.scan_workspace()
        self.load_head_tree()
        self.check_index_entries()
        self.collect_deleted_head_files()

    def collect_deleted_head_files(self) -> None:
        for path in self.head_tree.keys():
            if not self.repo.index.is_tracked_file(path):
                self.record_change(path, self.index_changes, "deleted")

    def load_head_tree(self) -> None:
        try:
            head_oid = self.repo.refs.read_head()
        except FileNotFoundError:
            head_oid = None
            return

        assert head_oid is not None
        commit = self.repo.database.load(head_oid)
        assert isinstance(commit, Commit)
        self.read_tree(commit.tree)

    def read_tree(self, tree_oid: str, pathname: str ='') -> None:
        tree = self.repo.database.load(tree_oid)
        assert isinstance(tree, Tree)

        for name, entry in tree.entries.items():
            path = Path(pathname) / name
            assert isinstance(entry, DatabaseEntry)
            if entry.is_tree():
                self.read_tree(entry.oid, str(path))
            else:
                self.head_tree[path] = entry

    def check_index_entries(self) -> None:
        for name, entry in self.repo.index.entries.items():
            self.check_index_against_workspace(entry)
            self.check_index_against_head_tree(entry)

    def check_index_against_workspace(self, entry: Entry) -> None:
        """
        Compares an index entry with the corresponding file in the workspace
        to detect unstaged changes (modified, deleted).
        """
        # Attempt to get the file's status from our scan of the workspace.
        stat_result = self.stats.get(entry.path, None)
    
        # If we have no stats for this path, the file has been deleted from the disk.
        if stat_result is None:
            self.record_change(entry.path, self.workspace_changes, "deleted")
            return
    
        # If the file's metadata (mode, size) doesn't match the index, it's modified.
        if not entry.stat_match(stat_result):
            self.record_change(entry.path, self.workspace_changes, "modified")
            return
    
        # For performance, if timestamps match, we assume the content is unchanged.
        if entry.times_match(stat_result):
            return
    
        # If timestamps differ, we must hash the file's content to be sure.
        data = self.repo.workspace.read_file(entry.path)
        blob = Blob(data)
        oid = self.repo.database.hash_object(blob)
    
        if entry.oid == oid:
            # The content is identical, so we just update the index with the new
            # timestamp to avoid re-hashing next time.
            self.repo.index.update_entry_stat(entry, stat_result)
        else:
            # The content has changed.
            self.record_change(entry.path, self.workspace_changes, "modified")

    def check_index_against_head_tree(self, entry: Entry) -> None:
        item = self.head_tree.get(entry.path, None)
        if item is not None:
            if entry.mode() != item.mode or entry.oid != item.oid:
                self.record_change(entry.path, self.index_changes, "modified")
        else:
            self.record_change(entry.path, self.index_changes, "added")

    def record_change(self, path: Path, structure: MutableMapping[str, str], ty: str) -> None:
        self.changed.add(str(path))
        structure[str(path)] = ty

    def scan_workspace(self, prefix: str = '') -> None:
        for path, stat in self.repo.workspace.list_dir(prefix).items():
            if self.repo.index.is_tracked(path):
                if self._is_dir(stat):
                    self.scan_workspace(str(path))
                elif self._is_file(stat):
                    self.stats[path] = stat
            elif self._is_trackable_file(path, stat):
                if self._is_dir(stat):
                    self.untracked.add(f"{path}{os.sep}")
                else:
                    self.untracked.add(str(path))

    def detect_workspace_changes(self) -> None:
        for path, entry in self.repo.index.entries.items():
            self.check_index_entry(entry)

    def check_index_entry(self, entry: Entry) -> None:
        stat = self.stats.get(entry.path, None)
        if stat is None:
            self.record_change(entry.path, self.workspace_changes, "deleted")
            return

        if not entry.stat_match(stat):
            self.record_change(entry.path, self.workspace_changes, "modified")
            return
        
        if entry.times_match(stat):
            return
        
        data = self.repo.workspace.read_file(entry.path)
        blob = Blob(data)
        oid = self.repo.database.hash_object(blob)

        if entry.oid == oid:
            self.repo.index.update_entry_stat(entry, stat)
        else:
            self.record_change(entry.path, self.workspace_changes, "modified")

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
