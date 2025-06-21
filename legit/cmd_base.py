from pathlib import Path
from typing import MutableMapping, TextIO

class Base:
    def __init__(
        self,
        _dir: Path,
        env: MutableMapping[str, str],
        args: list[str],
        stdin: TextIO,
        stdout: TextIO,
        stderr: TextIO,
    ):
        self.dir: Path = _dir
        self.env: MutableMapping[str, str] = env
        self.args: list[str] = args
        self.stdin: TextIO = stdin
        self.stdout: TextIO = stdout
        self.stderr: TextIO = stderr
        self.status: int | None = None

    def _print(self, string: str) -> None:
        self.stdout.write(string + '\n')

    def exit(self, status: int = 0) -> None:
        self.status = status
        raise ExitSignal(self.status)

    def execute(self) -> int:
        try:
            self.run()
            self.status = 0
        except ExitSignal as e:
            self.status = e.status 
        assert self.status is not None
        return self.status

    def expanded_path(self, path: str) -> Path:
        return (self.dir / path).absolute()

    def run(self) -> None:
        """Subclasses must override this."""
        raise NotImplementedError(f"{self.__class__.__name__}.run() not implemented")


class ExitSignal(Exception):
    """Internal exception to short-circuit out of `run()` with a status."""
    def __init__(self, status: int = 0) -> None:
        super().__init__(f"Exit with status {status}")
        self.status: int | None = status


