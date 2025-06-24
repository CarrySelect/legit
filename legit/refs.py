import re
from pathlib import Path
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

    HEAD = "HEAD"

    def __init__(self, path: Path) -> None:
        self.path: Path = path
        self.refs_path: Path = self.path / "refs"
        self.heads_path: Path = self.refs_path / "heads"

    def read_head(self) -> str:
        head_path = self.path / "HEAD"
        if head_path.exists():
            with open(head_path, "r") as f:
                return f.read().strip()
        raise FileNotFoundError(f"HEAD file not found at {head_path}")

    def update_head(self, oid: str) -> None:
        self._update_ref_file(self.path / Refs.HEAD, oid)

    def create_branch(self, branch_name: str) -> str:
        if INVALID_NAME.search(branch_name):
            raise Refs.InvalidBranch(f"'{branch_name}' is not a valid branch name.")
        
        path = self.heads_path / branch_name
        if path.is_file():
            raise Refs.InvalidBranch(f"A branch named {branch_name} already exists.")

        return self._update_ref_file(path, self.read_head())

    def _update_ref_file(self, path: Path, oid: str) -> str:
        lockfile = Lockfile(path)
        
        try:
            lockfile.hold_for_update()
            lockfile.write(oid.encode("utf-8") + b'\n')
            lockfile.commit()
        except FileNotFoundError:
            path.parent.mkdir(parents=True, exist_ok=True)
            return self._update_ref_file(path, oid)

        return oid


