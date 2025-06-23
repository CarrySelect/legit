from legit.myers import Edit, Line
from dataclasses import dataclass, field
from typing import Literal


HUNK_CONTEXT = 3

@dataclass
class Hunk:
    """Represents a single 'hunk' or block of changes in a diff."""
    a_start: int
    b_start: int
    edits: list[Edit] = field(default_factory=list)

    def header(self) -> str:
        """Generates the '@@ -x,y +w,z @@' header for the hunk."""
        a_offset = ",".join(map(str, self._offsets_for('a_line', self.a_start)))
        b_offset = ",".join(map(str, self._offsets_for('b_line', self.b_start)))
        return f"@@ -{a_offset} +{b_offset} @@"

    def __str__(self) -> str:
        """Creates a string representation of the entire hunk including the header."""
        SYMBOLS = {'eql': ' ', 'ins': '+', 'del': '-'}
        lines = [self.header()]
        for edit in self.edits:
            line = edit.a_line or edit.b_line
            # An edit should always have at least one line
            if line:
                lines.append(f"{SYMBOLS[edit.ty]}{line.text}")
        return "\n".join(lines)

    def _offsets_for(self, line_type: Literal['a_line', 'b_line'], default: int) -> tuple[int, int]:
        """
        Calculates the start line and line count for one side of the diff.
        
        `line_type` must be 'a_line' or 'b_line'.
        """
        # Get all lines of the specified type, filtering out None
        lines = [
            line for edit in self.edits 
            if (line := getattr(edit, line_type)) is not None
        ]

        start = lines[0].number if lines else default
        return start, len(lines)


def _build_hunk(self, edits: list[Edit], offset: int) -> int:
    """
    Helper function to populate a hunk with edits and determine its end.
    This is the equivalent of the Ruby Hunk.build method.
    """
    # Set a countdown to grab HUNK_CONTEXT lines after the last change
    counter = -1

    while counter != 0:
        if offset >= 0 and counter > 0:
            self.edits.append(edits[offset])

        offset += 1
        if offset >= len(edits):
            break

        # Look ahead to see if there's a change within the context window
        lookahead_offset = offset + HUNK_CONTEXT
        edit_type_ahead = None
        if lookahead_offset < len(edits) and edits[lookahead_offset]:
            edit_type_ahead = edits[lookahead_offset].ty

        if edit_type_ahead in ('ins', 'del'):
            # If a change is found, reset the counter to grab more context
            counter = 2 * HUNK_CONTEXT + 1
        else:
            counter -= 1

    return offset


def filter(edits: list[Edit]) -> list['Hunk']:
    hunks = []
    offset = 0

    while True:
        # Skip past any initial equal lines
        while offset < len(edits) and edits[offset].ty == 'eql':
            offset += 1

        if offset >= len(edits):
            return hunks

        # Backtrack to include leading context
        offset -= HUNK_CONTEXT + 1

        # Determine start line numbers for the hunk
        if offset < 0:
            a_start, b_start = 1, 1
        else:
            # An edit must have at least one of a_line or b_line
            line_ref: Line | None = edits[offset].a_line or edits[offset].b_line
            assert line_ref is not None
            a_start = line_ref.number if edits[offset].a_line else (line_ref.number + 1)
            b_start = line_ref.number if edits[offset].b_line else (line_ref.number + 1)
            
        hunk = Hunk(a_start, b_start)
        hunks.append(hunk)

        offset = _build_hunk(hunk, edits, offset)


