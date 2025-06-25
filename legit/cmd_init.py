from pathlib import Path
from legit.cmd_base import Base
from typing import MutableMapping, TextIO

class Init(Base):
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

    def run(self) -> None:
        if self.args:
            root_path = Path(self.args[0]).absolute()
        else:
            root_path = Path(self.dir).absolute()
            
        git_path: Path = root_path / ".git"

        for d in ("objects", "refs"):
            try:
                (git_path / d).mkdir(parents=True, exist_ok=True)
            except PermissionError as e:
                self.stderr.write(f"fatal: {e.strerror}")
                self.exit(1)

        self.println(f"Initialized empty Legit repository in {git_path}")
