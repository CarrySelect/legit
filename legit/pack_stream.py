import io
import hashlib
from contextlib import contextmanager
from legit.pack import InvalidPack


class Stream:
    def __init__(self, f):
        self.input = f
        self.digest = hashlib.sha1()
        self.offset = 0
        self.buffer = bytearray()
        self._capture = None

    @contextmanager
    def capture(self):
        self._capture = bytearray()
        yield
        self.digest.update(self._capture)
        self._capture = None

    def verify_checksum(self):
        expected = self.digest.digest()
        actual = self.read_buffered(20)
        if actual != expected:
            raise InvalidPack("Checksum does not match value read from pack")

    def read(self, size: int) -> bytes:
        data = self.read_buffered(size)
        self.update_state(data)
        return data

    def read_nonblock(self, size: int) -> bytes:
        data = self.read_buffered(size, False)
        self.update_state(data)
        return data

    def readbyte(self) -> int:
        b = self.read(1)
        if not b:
            raise EOFError("Unexpected EOF when reading byte")
        return b[0]

    def seek(self, amount: int, whence: int = io.SEEK_SET):
        if amount >= 0:
            return

        data = self._capture[amount:]
        self.buffer = bytearray(data) + self.buffer
        del self._capture[amount:]
        self.offset += amount

    def read_buffered(self, size: int, block: bool = True) -> bytes:
        from_buf = self.buffer[:size]
        needed = size - len(from_buf)
        from_io = self.input.read(needed) if block else self.input.read_nonblock(needed)
        return from_buf + from_io

    def update_state(self, data: bytes):
        if self._capture is None:
            self.digest.update(data)
        self.offset += len(data)
        self._capture = self._capture + data
