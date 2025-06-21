from pathlib import Path
from legit.lockfile import Lockfile

class Refs:
    class LockDenied(Exception):
        pass

    def __init__(self, path: Path) -> None:
        self.path: Path = path

    def read_head(self) -> str:
        head_path = self.path / "HEAD"
        if head_path.exists():
            with open(head_path, "r") as f:
                return f.read().strip()
        raise FileNotFoundError(f"HEAD file not found at {head_path}")

    def update_head(self, oid: str) -> None:
        head_path = Path(self.path) / "HEAD"
        lockfile = Lockfile(head_path)
        lockfile.hold_for_update()
        lockfile.write(oid.encode('utf-8'))
        lockfile.write(b"\n")

        lockfile.commit()




