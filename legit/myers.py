from dataclasses import dataclass
from typing import List, Dict, Generator


@dataclass
class Edit:
    """A single edit operation produced by the diff.

    op   – one of 'ins' (insert), 'del' (delete), 'eql' (equal)
    line – the item (line/element) affected
    """
    op: str
    line: str


class Myers:
    """Myers O((N + M) D) diff algorithm for two sequences."""

    def __init__(self, a: list[str], b: list[str]):
        self.a = a
        self.b = b

    @classmethod
    def diff(cls, a: list[str], b: list[str]) -> list[Edit]:
        return cls(a, b)._diff()

    def _diff(self) -> list[Edit]:
        edits: list[Edit] = []

        for prev_x, prev_y, x, y in self._backtrack():
            if x == prev_x:              # insertion
                edits.append(Edit("ins", self.b[prev_y]))
            elif y == prev_y:            # deletion
                edits.append(Edit("del", self.a[prev_x]))
            else:                        # equality (diagonal move)
                edits.append(Edit("eql", self.a[prev_x]))

        edits.reverse()
        return edits

    def _backtrack(self) -> Generator[tuple[int, int, int, int]]:
        """
        Walk the trace produced by `_shortest_edit`, yielding the (prev_x,
        prev_y, x, y) coordinates required to rebuild the edit script.
        """
        trace = self._shortest_edit()
        x, y = len(self.a), len(self.b)

        for d in range(len(trace) - 1, -1, -1):              # reverse order
            v = trace[d]
            k = x - y

            # Choose the predecessor diagonal.
            if k == -d or (k != d and v.get(k - 1, 0) < v.get(k + 1, 0)):
                prev_k = k + 1
            else:
                prev_k = k - 1

            prev_x = v.get(prev_k, 0)
            prev_y = prev_x - prev_k

            # Follow diagonal (no edits) as long as items are equal.
            while x > prev_x and y > prev_y:
                yield x - 1, y - 1, x, y
                x -= 1
                y -= 1

            # Yield the final non-diagonal step for this d-level.
            if d > 0:
                yield prev_x, prev_y, x, y

            x, y = prev_x, prev_y

    def _shortest_edit(self) -> list[dict[int, int]]:
        """
        Core of Myers' algorithm.  Builds a trace of 'furthest x on diagonal k'
        dictionaries, one per edit distance d, until the end of both sequences
        is reached.
        """
        n, m = len(self.a), len(self.b)
        max_d = n + m
        v: dict[int, int] = {1: 0}          # diagonal -> furthest x
        trace: list[dict[int, int]] = []

        for d in range(max_d + 1):
            trace.append(v.copy())

            for k in range(-d, d + 1, 2):
                # Decide whether the next step is down or right.
                if k == -d or (k != d and v.get(k - 1, 0) < v.get(k + 1, 0)):
                    x = v.get(k + 1, 0)            # down (insertion)
                else:
                    x = v.get(k - 1, 0) + 1        # right (deletion)

                y = x - k

                # Follow diagonal — matching elements — as far as possible.
                while x < n and y < m and self.a[x] == self.b[y]:
                    x += 1
                    y += 1

                v[k] = x  # record furthest x for this diagonal

                if x >= n and y >= m:
                    return trace    # full path found

        return trace  # fall-back (shouldn't happen)

