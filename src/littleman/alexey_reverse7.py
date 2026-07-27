"""13x13 double-extraction ring machine for reverse-a-list (reverse_07).

Same program as `alexey_reverse6` -- the pump interior and the relay are
byte-identical -- re-packed into a 13x13 box (fp 169 against 196).  Local
score 53,594 against reverse_06's 62,769; 1.17x, all of it footprint.

Found by moving one room at a time and judging after each move, not by
designing the final layout.  The steps are preserved in
`experiments/alexey-reverse06/` (step0..step6, each with its `.man`):

1. **Output flush.**  Its pipe bends into O's right wall instead of dropping
   into O's roof, so O climbs two rows.
2. **Relay down two rows** (rows 2-7).  This is the move that mattered, for a
   reason that was not visible from the outside: the ring-in used to leave
   the relay's RIGHT wall, which is why a gap column between the relay and
   the pump looked mandatory.  With two free rows above it, the ring-in
   leaves through the relay's ROOF instead and runs east along row 0.
3. **Input up one row**, ring-out re-terminated on the relay's floor.
4. **Ring-out out of the last row** -> 14x13.
5. **Pump one column left** -> the relay sits FLUSH against it, no gap
   column, 13x13.
6. **Ring-out serpentined** through the free block: 13 cells instead of 11,
   which restores the ring capacity the shorter route lost AND is 0.6%
   faster, because pipe cells are parking space as well as delay.

Ring capacity is 19 cells (13 + 6) against a peak occupancy of 16 measured
on three consecutive n=16 rounds -- the frame is at most 17 values and the
pump always holds one, so 16 is the structural bound.

Pipe resolution (pump floor row 9: ring-out at col 6, output at col 10):
the loop's `s` at (5,6) is 3 from the ring and 7 from the output; the three
printing `s` at (4,9), (5,11) and (7,10) are all nearer the output.  One
incoming pipe, so every `r`/`U` takes the ring and `U` turns south.
"""

from .alexey_reverse6 import PUMP_INTERIOR, RELAY_INTERIOR, _room
from .canvas import Canvas

PUMP = (1, 4)  # 9x8 room: rows 1-8, cols 4-12
RELAY = (2, 0)  # 4x6 room: rows 2-7, cols 0-3, flush against the pump
IN_ROOM = (10, 0)
OUT_ROOM = (9, 7)


def build_reverse7() -> str:
    canvas = Canvas()
    canvas.put(*PUMP, _room(PUMP_INTERIOR))
    canvas.put(*RELAY, _room(RELAY_INTERIOR))
    canvas.put(*IN_ROOM, ["+-+", "|I|", "+-+"])
    canvas.put(*OUT_ROOM, ["+-+", "|O|", "+-+"])

    # ring-in: out of the relay's roof, east along row 0, down the pump's roof.
    canvas.pipe([(1, 3), (0, 3), (0, 7)])
    canvas.cells[(0, 7)] = "v"

    # ring-out: pump floor -> serpentine through the free block -> relay floor
    # at (8,3).  The input's terminal (8,1) sorts first in reading order, which
    # is what gives input priority at the relay's `R`.
    canvas.pipe([(9, 6), (12, 6), (12, 4), (10, 4), (10, 5), (9, 5), (9, 3), (8, 3)])

    # output: pump floor, then bend west into O's right wall.
    canvas.pipe([(9, 10), (10, 10)])
    canvas.cells[(10, 10)] = "<"

    # input: I roof -> relay floor.
    canvas.pipe([(9, 1), (8, 1)])
    return canvas.render()
