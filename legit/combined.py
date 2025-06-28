from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Generator, Iterable
from legit.diff import Edit


SYMBOLS = {
    "del": "-",
    "add": "+",
    "eq": " ",
}


class Combined:
    @dataclass
    class Row:
        edits: List[Optional[Edit]]

        def __str__(self) -> str:
            symbols = "".join([
                SYMBOLS.get(edit.ty if edit else None, " ")
                for edit in self.edits
            ])

            del_edit = next((e for e in self.edits if e and e.ty == 'del'), None)

            if del_edit:
                line = del_edit.a_line
            else:
                first_edit = self.edits[0] if self.edits else None
                line = first_edit.b_line if first_edit else None

            line_text = line.text if line else ""
            return f"{symbols}{line_text}"

        @property
        def ty(self) -> str:
            types = [edit.ty for edit in self.edits if edit]
            return "ins" if "ins" in types else types[0]

        @property
        def a_lines(self):
            return [e.a_line for e in self.edits if e]

        @property
        def b_line(self):
            return self.edits[0].b_line if self.edits and self.edits[0] else None

    def __init__(self, diffs: List[List[Edit]]):
        self._diffs = diffs
        self._offsets: List[int] = []

    def __iter__(self) -> Generator[Combined.Row, None, None]:
        self._offsets = [0] * len(self._diffs)

        while True:
            for i, diff in enumerate(self._diffs):
                yield from self._consume_deletions(diff, i)

            if self._is_complete():
                return

            edits = [diff[offset] for offset, diff in self._offset_diffs()]

            self._offsets = [offset + 1 for offset in self._offsets]

            yield self.Row(edits)

    def _is_complete(self) -> bool: 
        return all(offset == len(diff) for offset, diff in self._offset_diffs())

    def _offset_diffs(self) -> Iterable[tuple[int, List[Edit]]]: 
        return zip(self._offsets, self._diffs)

    def _consume_deletions(self, diff: List[Edit], i: int) -> Generator[Combined.Row, None, None]:
        while self._offsets[i] < len(diff) and diff[self._offsets[i]].ty == 'del':
            edits: List[Optional[Edit]] = [None] * len(self._diffs)
            
            edits[i] = diff[self._offsets[i]]
            
            self._offsets[i] += 1

            yield self.Row(edits)
