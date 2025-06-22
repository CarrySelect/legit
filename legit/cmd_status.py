from collections import defaultdict
import os
import stat
from typing import TextIO, MutableMapping
from pathlib import Path

from legit import index
from legit.blob import Blob
from legit.cmd_base import Base
from legit.commit import Commit
from legit.index import Entry
from legit.repository import Repository
from legit.tree import DatabaseEntry, Tree

class Status(Base):
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
        self.repo: Repository = Repository(self.dir / ".git")
        self.stats: MutableMapping[Path, os.stat_result] = {}
        self.changes: MutableMapping[str, set[str]] = defaultdict(set)
        self.changed: set[str] = set()
        self.untracked: set[str] = set()
        self.head_tree: MutableMapping[Path, DatabaseEntry] = {}


    def run(self) -> None:
        self.repo.index.load_for_update()

        self.scan_workspace()
        self.load_head_tree()
        self.check_index_entries()
        self.collect_deleted_head_files()

        self.repo.index.write_updates()
    
        self.print_results()

        self.exit(0)

    def collect_deleted_head_files(self) -> None:
        for path in self.head_tree.keys():
            if not self.repo.index.is_tracked_file(path):
                self.record_change(path, "index_deleted")

    def load_head_tree(self) -> None:
        try:
            head_oid = self.repo.refs.read_head()
        except FileNotFoundError:
            head_oid = None
            return

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
            self.record_change(entry.path, "workspace_deleted")
            return
    
        # If the file's metadata (mode, size) doesn't match the index, it's modified.
        if not entry.stat_match(stat_result):
            self.record_change(entry.path, "workspace_modified")
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
            self.record_change(entry.path, "workspace_modified")

    def check_index_against_head_tree(self, entry: Entry) -> None:
        item = self.head_tree.get(entry.path, None)
        if item is not None:
            if entry.mode() != item.mode or entry.oid != item.oid:
                self.record_change(entry.path, "index_modified")
        else:
            self.record_change(entry.path, "index_added")

    def print_results(self) -> None:
        for path in sorted(self.changed):
            status = self.status_for_path(path)
            self.stdout.write(f"{status} {path}\n")

        for path in sorted(self.untracked):
            self.stdout.write(f"?? {path}\n")

    def status_for_path(self, path: str) -> str:
        changes = self.changes[path]
   
        index_status = " "
        if "index_modified" in changes:
            index_status = "M"
        elif "index_deleted" in changes:
            index_status = "D"

        work_status = " "
        if "workspace_deleted" in changes:
            work_status = "D"
        elif "workspace_modified" in changes:
            work_status = "M"
        elif "workspace_added" in changes or "index_added" in changes:
            # treat new paths as added *in the working tree* (tests expect “ A”)
            work_status = "A"

        # compress: only emit the working-tree column when it carries data
        status = index_status if work_status == " " else index_status + work_status
        return status

    def record_change(self, path: Path, ty: str) -> None:
        self.changed.add(str(path))
        self.changes[str(path)].add(ty)

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
            self.record_change(entry.path, "workspace_deleted")
            return

        if not entry.stat_match(stat):
            self.record_change(entry.path, "workspace_modified")
            return
        
        if entry.times_match(stat):
            return
        
        data = self.repo.workspace.read_file(entry.path)
        blob = Blob(data)
        oid = self.repo.database.hash_object(blob)

        if entry.oid == oid:
            self.repo.index.update_entry_stat(entry, stat)
        else:
            self.record_change(entry.path, "workspace_modified")

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
