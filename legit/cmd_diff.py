from pathlib import Path
from legit.cmd_base import Base
from legit.index import Entry, Index
from legit.myers import Edit
from legit.status import Status
from legit.repository import Repository
from legit.blob import Blob
from legit.hunk import Hunk
from legit.diff import diff, diff_hunks
from legit.cmd_color import SGR_CODES, Color
from legit.print_diff import PrintDiffMixin

class Diff(PrintDiffMixin, Base):
    NULL_OID = '0' * 40

    def run(self) -> None:
        self.patch = True

        self.define_print_diff_options()

        if any(x in self.args for x in ("--cached", "--staged")):
            self.cached = True
        else:
            self.cached = False

        self.repo: Repository = Repository(self.dir / ".git")
        self.repo.index.load()
        self.status_state: Status = self.repo.status() 
        
        self.setup_pager()

        if self.cached:
            self.diff_head_index()
        else:
            self.diff_index_workspace()
        
        self.exit(0)
    
    def diff_head_index(self) -> None:
        if not self.patch:
            return

        for path, state in self.status_state.index_changes.items():
            if state == 'modified':
                self.print_diff(self.from_head(Path(path)), self.from_index(Path(path)))
            elif state == 'added':
                self.print_diff(self.from_nothing(Path(path)), self.from_index(Path(path)))
            elif state == 'deleted':
                self.print_diff(self.from_head(Path(path)), self.from_nothing(Path(path)))

    def diff_index_workspace(self) -> None:
        if not self.patch:
            return

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
        assert entry is not None
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




