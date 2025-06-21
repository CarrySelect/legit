from legit.author import Author


class Commit:
    def __init__(self, parent: str, tree: str, author: Author, message: str) -> None:
        self.parent: str | None = parent
        self.tree: str = tree
        self.author: Author = author
        self.message: str = message
        self._oid: str | None = None

    @property
    def oid(self) -> str:
        assert self._oid is not None
        return self._oid

    @oid.setter
    def oid(self, value: str) -> None:
        self._oid = value

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
