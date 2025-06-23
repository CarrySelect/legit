from collections import defaultdict
import os
import stat
from typing import TextIO, MutableMapping, cast
from pathlib import Path

from legit import index
from legit.blob import Blob
from legit.cmd_base import Base
from legit.commit import Commit
from legit.index import Entry
from legit.repository import Repository
from legit.tree import DatabaseEntry, Tree


LABEL_WIDTH = 12

SHORT_STATUS: MutableMapping[str, str] = {
    "added": "A",
    "modified": "M",
    "deleted": "D",
}

LONG_STATUS: MutableMapping[str, str] = {
    "added": "new file:",
    "deleted": "deleted:",
    "modified": "modified:",
}


class Color:
    SGR_CODES: dict[str, int] = {
        "red": 31,
        "green": 32,
    }

    @staticmethod
    def format(color: str, msg: str) -> str:
        code = Color.SGR_CODES.get(color)
        if code is None:
            return msg
        return f"\033[{code}m{msg}\033[0m"


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
        self.index_changes: MutableMapping[str, str] = {}
        self.workspace_changes: MutableMapping[str, str] = {}
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

    def fmt(self, color: str, msg: str) -> str:
        return Color.format(color, msg) if self.stdout.isatty() else msg

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

    def print_results(self) -> None:
        try:
            fmt = self.args[0]
        except IndexError:
            fmt = None

        if fmt == '--porcelain':
            self.print_porcelain_format()
        else:
            self.print_long_format()

    def print_long_format(self) -> None:
        self.print_changes("Changes to be committed", self.index_changes, 'green')
        self.print_changes("Changes not staged for commit", self.workspace_changes, 'red')
        self.print_changes("Untracked files", {p: '' for p in sorted(self.untracked)}, 'red')

        self.print_commit_status()

    def print_changes(self, message: str, changeset: MutableMapping[str, str], color: str) -> None:
        if not changeset:
            return
        
        self.stdout.write(message + '\n')
        self.stdout.write('\n')

        for path, ty in changeset.items():
            status = LONG_STATUS[ty].ljust(LABEL_WIDTH, ' ') if not ty else ''
            self.stdout.write("\t" + self.fmt(color, f"{status}{path}") + '\n')

        self.stdout.write('\n')

    def print_commit_status(self) -> None:
        if self.index_changes:
            return

        if self.workspace_changes:
            self.stdout.write("no changes added to commit\n")
        elif self.untracked:
            self.stdout.write("nothing added to commit but untracked files present\n")
        else:
            self.stdout.write("nothing to commit, working tree clean\n")



    def print_porcelain_format(self) -> None:
        for path in sorted(self.changed):
            status = self.status_for_path(path)
            self.stdout.write(f"{status} {path}\n")

        for path in sorted(self.untracked):
            self.stdout.write(f"?? {path}\n")

    def status_for_path(self, path: str) -> str:
        left = SHORT_STATUS.get(cast(str, self.index_changes.get(path)), ' ')
        right = SHORT_STATUS.get(cast(str, self.workspace_changes.get(path)), ' ')
        return left + right

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
