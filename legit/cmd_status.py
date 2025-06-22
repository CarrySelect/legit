from collections import defaultdict
import os
import stat
from typing import TextIO, MutableMapping
from pathlib import Path

from legit.blob import Blob
from legit.cmd_base import Base
from legit.index import Entry
from legit.repository import Repository

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


    def run(self) -> None:
        self.repo.index.load()

        self.repo.index.load_for_update()

        self.scan_workspace()
        self.detect_workspace_changes()

        self.repo.index.write_updates()
    
        self.print_results()

        self.exit(0)

    def print_results(self) -> None:
        for path in sorted(self.changed):
            status = self.status_for_path(path)
            self.stdout.write(f"{status} {path}\n")

        for path in sorted(self.untracked):
            self.stdout.write(f"?? {path}\n")

    def status_for_path(self, path: str) -> str:
        changes = self.changes[path]
    
        status = "  "
        status = " D" if "workspace_deleted" in changes else status
        status = " M" if "workspace_modified" in changes else status

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
