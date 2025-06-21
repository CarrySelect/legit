import os
from collections.abc import Iterator
from pathlib import Path

class Workspace:
    class MissingFile(Exception):
        pass
    class NoPermission(Exception):
        pass

    IGNORE: list[str] = [".", "..", ".git", "__pycache__", "env", ".pytest_cache", ".mypy_cache"]

    def __init__(self, path: Path) -> None:
        self.path: Path = path

    def list_files(self, path: Path) -> Iterator[Path]:
        if path.is_dir():
            for f in path.iterdir():
                if f.name not in Workspace.IGNORE:
                    yield from self.list_files(f)
        elif path.exists():
            yield path.relative_to(self.path)
        else:
            raise Workspace.MissingFile(f"pathspec \"{path.relative_to(self.path)}\" did not match any files")


    def read_file(self, path: Path) -> str:
        try:
            with open(self.path / path) as f:
                return f.read()
        except PermissionError:
            raise Workspace.NoPermission(f"open(\"{path.name}\"): Permission denied")

    def stat_file(self, path: Path) -> os.stat_result:
        try:
            return (self.path / path).stat()
        except PermissionError:
            raise Workspace.NoPermission(f"stat(\"{path.name}\"): Permission denied")

