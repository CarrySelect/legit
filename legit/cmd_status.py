import os
import stat
from typing import Any, TextIO, MutableMapping
from pathlib import Path

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
        self.untracked: set[str] = set()
        self.stats: MutableMapping[Path, os.stat_result] = {}
        self.changed: set[str] = set()

    def run(self) -> None:
        self.repo.index.load()

        self.scan_workspace()
        self.detect_workspace_changes()

        for f in sorted(self.changed):
            self.stdout.write(f" M {f}\n")

        for f in sorted(self.untracked):
            self.stdout.write(f"?? {f}\n")

        self.exit(0)

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
        stat = self.stats[entry.path]
        if not entry.stat_match(stat):
            self.changed.add(str(entry.path))

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
