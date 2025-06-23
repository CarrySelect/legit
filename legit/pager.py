import os
import shlex
import subprocess
import sys
from typing import MutableMapping, TextIO

class Pager:
    PAGER_CMD = "less"
    PAGER_ENV = { "LESS": "FRX", "LV": "-c" }

    def __init__(
        self,
        env: MutableMapping[str, str] = {},
        stdout: TextIO | None = None,
        stderr: TextIO | None = None,
    ) -> None:
        self.pager: Pager | None = None

        # Merge into a fresh copy of the current environment:
        pager_env = os.environ.copy()
        pager_env.update(self.PAGER_ENV)
        if env:
            pager_env.update(env)

        # Pick the pager command
        cmd = pager_env.get("GIT_PAGER") or pager_env.get("PAGER") or self.PAGER_CMD
        args = shlex.split(cmd)

        # Create a pipe: parent writes to `writer`, child reads from `reader`
        reader_fd, writer_fd = os.pipe()

        # Wrap the write‐end as a file object for convenience
        #   open in binary mode so we can write either bytes or str.encode()
        self.input: TextIO = os.fdopen(writer_fd, 'w', buffering=0)

        # Spawn the pager, hooking its stdin to the read‐end of our pipe
        self._proc: subprocess.Popen[bytes] | None = subprocess.Popen(
            args,
            stdin=reader_fd,
            stdout=stdout or sys.stdout,
            stderr=stderr or sys.stderr,
            env=pager_env,
            close_fds=True  # close other fds in the child
        )

        # We don't need the read‐end in the parent
        os.close(reader_fd)

    def wait(self) -> None:
        """Block until the pager exits."""
        if self._proc:
            self._proc.wait()
            self._proc = None


