from pathlib import Path
from legit.cmd_base import Base
from legit.index import Entry, Index
from legit.status import Status
from legit.repository import Repository
from legit.blob import Blob
from legit.diff import diff, diff_hunks


class Target:
    NULL_PATH = "/dev/null"

    def __init__(self, path: Path, oid: str, mode: str | None, data: str) -> None:
        self.path: Path = path
        self.oid: str = oid
        self.mode: str | None = mode
        self.data: str = data

    def diff_path(self):
        return self.path if self.mode is not None else Target.NULL_PATH


class Diff(Base):
    NULL_OID = '0' * 40

    def run(self) -> None:
        self.repo: Repository = Repository(self.dir / ".git")
        self.repo.index.load()
        self.status_state: Status = self.repo.status() 
        
        if len(self.args) > 0 and self.args[0] == '--cached':
            self.diff_head_index()
        else:
            self.diff_index_workspace()
        
        self.exit(0)

    def diff_head_index(self) -> None:
        for path, state in self.status_state.index_changes.items():
            if state == 'modified':
                self.print_diff(self.from_head(Path(path)), self.from_index(Path(path)))
            elif state == 'added':
                self.print_diff(self.from_nothing(Path(path)), self.from_index(Path(path)))
            elif state == 'deleted':
                self.print_diff(self.from_head(Path(path)), self.from_nothing(Path(path)))

    def diff_index_workspace(self) -> None:
        for path, state in self.status_state.workspace_changes.items():
            if state == 'modified':
                self.print_diff(self.from_index(Path(path)), self.from_file(Path(path)))
            elif state == 'deleted':
                self.print_diff(self.from_index(Path(path)), self.from_nothing(Path(path)))
    
    def from_head(self, path: Path) -> 'Target':
        entry = self.status_state.head_tree[path]
        blob = self.repo.database.load(entry.oid)
        assert isinstance(blob, Blob)
        return Target(path, entry.oid, oct(entry.mode)[2:], blob.data)

    def from_index(self, path: Path) -> 'Target':
        entry = self.repo.index.entry_for_path(path)
        blob = self.repo.database.load(entry.oid)
        assert isinstance(blob, Blob)
        return Target(path, entry.oid, oct(entry.mode())[2:], blob.data)

    def from_file(self, path: Path) -> 'Target':
        blob = Blob(self.repo.workspace.read_file(path))
        oid = self.repo.database.hash_object(blob)
        mode = Entry.mode_for_stat(self.status_state.stats[path])
        return Target(path, oid, oct(mode)[2:], blob.data)

    def from_nothing(self, path: Path) -> 'Target':
        return Target(path, Diff.NULL_OID, None, '')

    def print_diff(self, a: Target, b: Target) -> None:
        if a.oid == b.oid:
            return

        a.path = Path("a") / a.path
        b.path = Path("b") / b.path
        
        self.stdout.write(f"diff --git {a.path} {b.path}" + '\n')
        self.print_diff_mode(a, b)
        self.print_diff_content(a, b)

    def print_diff_mode(self, a: Target, b: Target) -> None:
        if a.mode is None:
            self.stdout.write(f"new file mode {b.mode}" + '\n')
        elif b.mode is None:
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
    
        hunks = diff_hunks(a.data, b.data)
        for hunk in hunks:
            self.stdout.write(str(hunk))

    def _short(self, oid: str) -> str:
        return self.repo.database.short_oid(oid)
