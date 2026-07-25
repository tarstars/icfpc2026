"""15x15 geometric compaction of the corridor-free Reverse machine.

The room programs are byte-identical to ``reverse_01``.  Three layout changes
remove the last row and column:

* move the pump and relay one column left;
* move the relay one row up, leaving one cell for the pump-to-relay pipe;
* route the 17-cell return FIFO around the relay's upper-left corner instead
  of below it.

The return pipe still has capacity 17 for the documented ``n <= 16`` bound.
Its terminal arrow is patched upward because the last routed segment is
horizontal.
"""

from .alexey_reverse2 import PUMP_INTERIOR, RELAY, _room
from .canvas import Canvas


def build_reverse3() -> str:
    canvas = Canvas()
    canvas.put(0, 0, ["+-+", "|I|", "+-+"])
    canvas.put(3, 0, ["+-+", "|O|", "+-+"])
    canvas.put(0, 4, _room(PUMP_INTERIOR))
    canvas.put(11, 8, RELAY)

    # Both one-cell side pipes point directly between room walls.
    canvas.cells[(1, 3)] = ">"
    canvas.cells[(4, 3)] = "<"

    # A one-cell bottom pipe connects the pump to the relay.
    canvas.cells[(10, 11)] = "v"

    # The return pipe exits the relay's left wall, wraps above it, and enters
    # the pump bottom. Its 17 cells retain the proven capacity invariant.
    canvas.pipe([(13, 7), (13, 0), (10, 0), (10, 6)])
    canvas.cells[(10, 6)] = "^"
    return canvas.render()
