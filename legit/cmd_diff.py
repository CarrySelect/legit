from pathlib import Path
from legit.cmd_base import Base
from legit.index import Entry, Index
from legit.status import Status
from legit.repository import Repository
from legit.blob import Blob


class Target:
    NULL_PATH = "/dev/null"

    def __init__(self, path: Path, oid: str, mode: str | None) -> None:
        self.path: Path = path
        self.oid: str = oid
        self.mode: str | None = mode

    def diff_path(self):
        return self.path if self.mode is not None else Target.NULL_PATH


class Diff(Base):
    NULL_OID = '0' * 40

    def run(self) -> None:
        self.repo: Repository = Repository(self.dir / ".git")
        self.repo.index.load()
        self.status_state: Status = self.repo.status()

        for path, state in self.status_state.workspace_changes.items():
            if state == 'modified':
                self.print_diff(self.from_index(Path(path)), self.from_file(Path(path)))
            elif state == 'deleted':
                self.print_diff(self.from_index(Path(path)), self.from_nothing(Path(path)))

        self.exit(0)

    def from_index(self, path: Path) -> 'Target':
        entry = self.repo.index.entry_for_path(path)
        return Target(path, entry.oid, oct(entry.mode())[2:])

    def from_file(self, path: Path) -> 'Target':
        blob = Blob(self.repo.workspace.read_file(path))
        oid = self.repo.database.hash_object(blob)
        mode = Entry.mode_for_stat(self.status_state.stats[path])
        return Target(path, oid, oct(mode)[2:])

    def from_nothing(self, path: Path) -> 'Target':
        return Target(path, Diff.NULL_OID, None)

    def print_diff(self, a: Target, b: Target) -> None:
        if a.oid == b.oid:
            return

        a.path = Path("a") / a.path
        b.path = Path("b") / b.path
        
        self.stdout.write(f"diff --git {a.path} {b.path}" + '\n')
        self.print_diff_mode(a, b)
        self.print_diff_content(a, b)

    def print_diff_mode(self, a: Target, b: Target) -> None:
        if b.mode is None:
            self.stdout.write(f"deleted file mode {a.mode}" + '\n')
        elif a.mode != b.mode:
            self.stdout.write(f"old mode {a.mode}" + '\n')
            self.stdout.write(f"new mode {b.mode}" + '\n')

    def print_diff_content(self, a: Target, b: Target) -> None:
        if a.oid == b.oid:
            return

        oid_range = f"index {self._short(a.oid)}..{self._short(b.oid)}"
        if a.mode == b.mode:
            oid_range += f" {a.mode}" 

        self.stdout.write(oid_range + '\n')
        self.stdout.write(f"--- {a.diff_path()}" + '\n')
        self.stdout.write(f"+++ {b.diff_path()}" + '\n')

    def diff_file_deleted(self, path: Path) -> None:
        entry = self.repo.index.entry_for_path(path)
        a_oid = entry.oid
        a_mode = oct(entry.mode())[2:]

        b_oid = Diff.NULL_OID
        b_mode = None

        a = Target(path, a_oid, a_mode)
        b = Target(path, b_oid, b_mode)

        self.print_diff(a, b)

    def diff_file_modified(self, path: Path) -> None:
        entry = self.repo.index.entry_for_path(path)
        a_oid = entry.oid
        a_mode = oct(entry.mode())[2:]

        blob = Blob(self.repo.workspace.read_file(path))
        b_oid = self.repo.database.hash_object(blob)
        b_mode = oct(entry.mode_for_stat(self.status_state.stats[path]))[2:]

        a = Target(path, a_oid, a_mode)
        b = Target(path, b_oid, b_mode)
        
        self.print_diff(a, b)

    def _short(self, oid: str) -> str:
        return self.repo.database.short_oid(oid)
