import re
from typing import Optional, Union

class Revision:
    class Ref:
        def __init__(self, name: str):
            self.name = name
        def __repr__(self) -> str:
            return f"(Ref name={self.name!r})"

    class Parent:
        def __init__(self, rev: Union['Revision.Ref', 'Revision.Parent', 'Revision.Ancestor']) -> None:
            self.rev = rev
        def __repr__(self) -> str:
            return f"Parent(rev={self.rev!r})"

    class Ancestor:
        def __init__(self, rev: Union['Revision.Ref', 'Revision.Parent', 'Revision.Ancestor'], n: int) -> None:
            self.rev = rev
            self.n = n
        def __repr__(self) -> str:
            return f"(Ancestor(rev={self.rev!r}, n={self.n})"

    INVALID_NAME = re.compile(r"""
          ^\.          |    # starts with a dot
          /\.\.        |    # slash-dot
          \.\.         |    # two dots
          /$           |    # ends with slash
          \.lock$      |    # ends with '.lock'
          @\{          |    # literal '@{'
          [\x00-\x20*:?\[\\^~\x7f]  # control or disallowed chars
        """, re.X)

    PARENT_PATTERN   = re.compile(r'^(.+)\^$')
    ANCESTOR_PATTERN = re.compile(r'^(.+)~(\d+)$')

    REF_ALIASES = {
        "@": "HEAD"
    }

    @classmethod
    def valid_ref(cls, revision: str) -> bool:
        """Return True if the revision string is a valid ref name."""
        return not bool(cls.INVALID_NAME.search(revision))

    @classmethod
    def parse(cls, revision: str) -> Optional[Union[Ref, Parent, Ancestor]]:
        """
        Parse a revision string into one of the nested types:
          - Parent if it ends with '^'
          - Ancestor if it ends with '~<n>'
          - Ref otherwise (if valid)
        Returns None if it doesn’t match any valid pattern.
        """
        # Parent syntax (e.g. "main^")
        m = cls.PARENT_PATTERN.match(revision)
        if m:
            base = m.group(1)
            rev = cls.parse(base)
            return cls.Parent(rev) if rev else None

        # Ancestor syntax (e.g. "main~3")
        m = cls.ANCESTOR_PATTERN.match(revision)
        if m:
            base, num = m.group(1), int(m.group(2))
            rev = cls.parse(base)
            return cls.Ancestor(rev, num) if rev else None

        # Plain ref (e.g. "main" or "@")
        if cls.valid_ref(revision):
            name = cls.REF_ALIASES.get(revision, revision)
            return cls.Ref(name)

        # Invalid
        return None

