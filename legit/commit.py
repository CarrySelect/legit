from typing import cast
from legit.author import Author


class Commit:
    def __init__(self, parent: str | None, tree: str, author: Author, message: str) -> None:
        self.parent: str | None = parent
        self.tree: str = tree
        self.author: Author = author
        self.message: str = message
        self._oid: str | None = None

    @classmethod
    def parse(cls, data: bytes) -> 'Commit':
        headers: dict[str, str] = {}

        lines = data.decode('utf-8').split('\n')
        idx = 0
        for idx, line in enumerate(lines):
            if not line:
                break
            key, val = line.split(' ', 1)
            headers[key] = val

        message = '\n'.join(lines[idx+1:])

        assert headers['tree'] is not None

        author = Author.parse(headers['author'])
        assert author is not None

        return cls(
            headers.get('parent'),
            headers['tree'],
            author, 
            message,
        )

    @property
    def oid(self) -> str:
        assert self._oid is not None
        return self._oid

    @oid.setter
    def oid(self, value: str) -> None:
        self._oid = value
    
    def title_line(self) -> str:
        return self.message.splitlines()[0]

    def type(self) -> str:
        return "commit"

    def to_bytes(self) -> bytes:
        lines = [
            f"tree {self.tree}",
        ]

        if self.parent is not None:
            lines += [
                f"parent {self.parent}"
            ]

        lines.extend([
            f"author {self.author}",
            f"committer {self.author}",
            "",
            self.message,
        ])

        return b'\n'.join(line.encode('utf-8') for line in lines)
