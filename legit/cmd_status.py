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
from legit.status import Status
from legit.cmd_color import Color


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


class StatusCmd(Base):
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
        self.repo = Repository(self.dir / ".git")
        self.status_state: Status | None = None

    def run(self) -> None:
        self.repo.index.load_for_update()
        self.status_state = self.repo.status()
        self.repo.index.write_updates()
    
        self.print_results()

        self.exit(0)

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
        assert self.status_state is not None
        self.print_changes("Changes to be committed", self.status_state.index_changes, 'green')
        self.print_changes("Changes not staged for commit", self.status_state.workspace_changes, 'red')
        self.print_changes("Untracked files", {p: '' for p in sorted(self.status_state.untracked)}, 'red')

        self.print_commit_status()

    def print_changes(self, message: str, changeset: MutableMapping[str, str], color: str) -> None:
        if not changeset:
            return
        
        self.stdout.write(message + '\n')
        self.stdout.write('\n')

        for path, ty in changeset.items():
            status = LONG_STATUS[ty].ljust(LABEL_WIDTH, ' ') if ty else ''
            self.stdout.write("\t" + self.fmt(color, f"{status}{path}") + '\n')

        self.stdout.write('\n')

    def print_commit_status(self) -> None:
        assert self.status_state is not None
        if self.status_state.index_changes:
            return

        if self.status_state.workspace_changes:
            self.stdout.write("no changes added to commit\n")
        elif self.status_state.untracked:
            self.stdout.write("nothing added to commit but untracked files present\n")
        else:
            self.stdout.write("nothing to commit, working tree clean\n")

    def print_porcelain_format(self) -> None:
        assert self.status_state is not None
        for path in sorted(self.status_state.changed):
            status = self.status_for_path(path)
            self.stdout.write(f"{status} {path}\n")

        for path in sorted(self.status_state.untracked):
            self.stdout.write(f"?? {path}\n")

    def status_for_path(self, path: str) -> str:
        assert self.status_state is not None
        left = SHORT_STATUS.get(cast(str, self.status_state.index_changes.get(path)), ' ')
        right = SHORT_STATUS.get(cast(str, self.status_state.workspace_changes.get(path)), ' ')
        return left + right

    def fmt(self, color: str, msg: str) -> str:
        return Color.format(color, msg) if self.stdout.isatty() else msg


