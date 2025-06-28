from __future__ import annotations
from dataclasses import dataclass, field
from itertools import zip_longest
from typing import List, Optional
from legit.myers import Edit, Line


HUNK_CONTEXT = 3

@dataclass
class Hunk:
    a_starts: List[int]
    b_start: Optional[int]
    edits: List[Edit] = field(default_factory=list)

    @staticmethod
    def filter(edits: List[Edit]) -> List[Hunk]:
        hunks: List[Hunk] = []
        offset = 0

        while True:
            while offset < len(edits) and edits[offset].ty == 'eql':
                offset += 1

            if offset >= len(edits):
                return hunks

            offset -= HUNK_CONTEXT + 1

            a_starts = [line.number for line in edits[offset].a_lines] if offset >= 0 else []
            
            b_line = edits[offset].b_line if offset >= 0 else None
            b_start = b_line.number if b_line else None

            hunk = Hunk(a_starts=a_starts, b_start=b_start, edits=[])
            hunks.append(hunk)

            offset = Hunk._build(hunks[-1], edits, offset)
    
    @staticmethod
    def _build(hunk: Hunk, edits: List[Edit], offset: int) -> int:
        counter = -1

        while counter != 0:
            if offset >= 0 and counter > 0:
                hunk.edits.append(edits[offset])
            
            offset += 1
            if offset >= len(edits):
                break

            lookahead_index = offset + HUNK_CONTEXT
            edit_type_ahead = None
            if lookahead_index < len(edits):
                lookahead_edit = edits[lookahead_index]
                if lookahead_edit:
                    edit_type_ahead = lookahead_edit.ty
            
            if edit_type_ahead in ('ins', 'del'):
                counter = 2 * HUNK_CONTEXT + 1
            else:
                counter -= 1
        
        return offset

    def header(self) -> str:
        list_of_a_lines = [e.a_lines for e in self.edits]
        transposed_a_lines = list(zip_longest(*list_of_a_lines))

        offsets = [
            self._format("-", lines, self.a_starts[i]) 
            for i, lines in enumerate(transposed_a_lines)
        ]

        b_lines = [e.b_line for e in self.edits]
        offsets.append(self._format("+", b_lines, self.b_start))
        
        sep = "@" * len(offsets)

        return " ".join([sep, *offsets, sep])

    def _format(self, sign: str, lines: List[Optional[Line]], start: Optional[int]) -> str:
        compact_lines = [line for line in lines if line is not None]

        line_start = compact_lines[0].number if compact_lines else start
        final_start = line_start if line_start is not None else 0
        
        return f"{sign}{final_start},{len(compact_lines)}"


