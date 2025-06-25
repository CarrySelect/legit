import re
from pathlib import Path
from sys import path_hooks
from typing import Any, Optional
from legit.lockfile import Lockfile


INVALID_NAME = re.compile(r'''
      ^\.
    | /\.
    | \.\.
    | /$
    | \.lock$
    | @\{
    | [\x00-\x20*:?\[\\\^~\x7f]
''', re.VERBOSE)


class Refs:
    class LockDenied(Exception):
        pass
    class InvalidBranch(Exception):
        pass

    class Ref:
        def __init__(self, oid: str) -> None:
            self.oid: str = oid

        def read_oid(self) -> str:
            return self.oid

    class SymRef:
        def __init__(self, refs: 'Refs', path: str) -> None:
            self.path: str = path
            self.refs: Refs = refs

        def read_oid(self) -> Optional[str]:
            return self.refs.read_ref(self.path)

        def is_head(self) -> bool:
            return self.path == Refs.HEAD

    HEAD = "HEAD"
    SYMREF = re.compile(r"^ref: (.+)$")

    def __init__(self, path: Path) -> None:
        self.path: Path = path
        self.refs_path: Path = self.path / "refs"
        self.heads_path: Path = self.refs_path / "heads"

    def current_ref(self, source: str = "HEAD") -> 'Refs.SymRef':
        ref = self.read_oid_or_symref(self.path / source)

        if isinstance(ref, Refs.SymRef):
            return self.current_ref(ref.path)

        return Refs.SymRef(self, source)

    def set_head(self, revision: str, oid: str) -> None:
        head = self.path / Refs.HEAD
        path = self.heads_path / revision

        if path.is_file():
            relative = path.relative_to(self.path)
            self._update_ref_file(head, f"ref: {relative}")
        else:
            self._update_ref_file(head, oid)

    def read_oid_or_symref(self, path: Path) -> Optional['Refs.Ref | Refs.SymRef']:
        try:
            data = path.read_text().strip()
        except FileNotFoundError:
            return None
        m = Refs.SYMREF.match(data)
        return Refs.SymRef(self, m.group(1)) if m else Refs.Ref(data)

    def read_symref(self, path: Path) -> Optional[str]:
        ref = self.read_oid_or_symref(Path(path))
        match ref:
            case c if isinstance(c, Refs.Ref):
                assert isinstance(ref, Refs.Ref)
                return ref.oid
            case c if isinstance(c, Refs.SymRef):
                assert isinstance(ref, Refs.SymRef)
                return self.read_symref(self.path / ref.path)
            case c if c is None:
                return None

    def read_head(self) -> Optional[str]:
        return self.read_symref(self.path / Refs.HEAD)

    def update_head(self, oid: str) -> None:
        self.update_symref(self.path / Refs.HEAD, oid)

    def update_symref(self, path: Path, oid: str) -> None:
        lockfile = Lockfile(path)
        lockfile.hold_for_update()

        ref = self.read_oid_or_symref(path)
        if not isinstance(ref, Refs.SymRef):
            self.write_lockfile(lockfile, oid)
            return

        try:
            self.update_symref(self.path / ref.path, oid)
        finally:
            lockfile.rollback()

    def write_lockfile(self, lockfile: Lockfile, oid: str) -> None:
        lockfile.write(oid.encode('utf-8') + b'\n')
        lockfile.commit()

    def create_branch(self, branch_name: str, start_oid: str) -> str:
        if INVALID_NAME.search(branch_name):
            raise Refs.InvalidBranch(f"'{branch_name}' is not a valid branch name.")
        
        path = self.heads_path / branch_name
        if path.is_file():
            raise Refs.InvalidBranch(f"A branch named {branch_name} already exists.")

        return self._update_ref_file(path, start_oid)

    def _update_ref_file(self, path: Path, oid: str) -> str:
        lockfile = Lockfile(path)
        
        try:
            lockfile.hold_for_update()
            self.write_lockfile(lockfile, oid)
        except FileNotFoundError:
            path.parent.mkdir(parents=True, exist_ok=True)
            return self._update_ref_file(path, oid)

        return oid

    def read_ref(self, name: str) -> Optional[str]:
        path = self.path_for_name(name)
        return self.read_symref(path) if path is not None else None

    def path_for_name(self, name: str) -> Optional[Path]:
        prefixes = (self.path, self.refs_path, self.heads_path)
        for prefix in prefixes:
            candidate = prefix / name
            if candidate.is_file():
                return candidate
        return None

    def read_ref_file(self, path: Path) -> Optional[str]:
        try:
            return path.read_text().strip()
        except FileNotFoundError:
            return None
        
