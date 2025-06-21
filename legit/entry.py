import os
import stat
from pathlib import Path

class Entry:
    REGULAR_MODE = "100644"
    EXECUTABLE_MODE = "100755"
    DIRECTORY_MODE = "40000"

    def __init__(self, name: Path, oid: str, stat: os.stat_result) -> None:
        self.name: Path = name
        self.oid: str = oid
        self.stat: os.stat_result = stat

    def mode(self) -> str:
        exec_perms: int = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        is_executable: bool = bool(self.stat.st_mode & exec_perms)
        return Entry.EXECUTABLE_MODE if is_executable else Entry.REGULAR_MODE

    def parent_directories(self) -> list[Path]:
        return [p for p in self.name.parents[::-1] if p.name != '.']
