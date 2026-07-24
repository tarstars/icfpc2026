"""Compact shrinking-ring selection sort (candidate sort_03).

Same machine as sort_ring.py (pump + relay ring, q-counted ring size,
min-scan, delay corridor), repacked for footprint. Changes vs sort_02:

- The input room feeds the pump's LEFT wall at the entry row, removing
  the three rows above the pump.
- The scan block is shifted five columns left; climb col 10, descent 11.
- The delay corridor is three rows (3 east / 4 west / 5 east) with the
  load path joining row 3 eastbound at col 9 and the emit climb
  rejoining at (3,10) with a straight-through '>'.
- The relay shrinks to a 4x6 room (2x4 interior loop, r before first s).
- The ring-return pipe is folded into a 21-cell serpentine under the
  pump instead of a wide loop, keeping capacity >= 16 (n <= 16) without
  widening the bounding box.

Bounding box 18 wide x 19 tall -> footprint 361 (sort_02: 729).

Timing invariants (why the corridor is 3 rows):
- After the load loop the walk to `q` is ~27 ticks; the last loaded
  value is inside the ring-return pipe after ~19 (out pipe 2 cells,
  relay wait <= 8 + 3, then it enters the 21-cell return pipe).
- After the last requeue in a scan pass the walk to `q` is ~55 ticks
  via emit + climb + corridor; worst transit is ~35.
"""

from .canvas import Canvas

PUMP_INTERIOR = [
    ">@rbm>rsv  ",  # r1: entry + load loop
    "     ^ md  ",  # r2: load-loop return / exit
    "        >>v",  # r3: corridor east; (3,9) load join, (3,10) climb rejoin
    " v        <",  # r4: corridor west
    " >        v",  # r5: corridor east
    "^       aq<",  # r6: probe: q, a, empty-ring fallthrough to col 1
    "va   Mrm<  ",  # r7: pickup (candidate min -> B), j==1 bypass at (7,2)
    "    >+Wsv  ",  # r8: scan north branch: new min, requeue old
    " >r-Xv     ",  # r9: scan test: r, -, X on sign(value - min)
    "    >>+sv  ",  # r10: scan south branch: requeue value (X straight joins)
    "vd   m  <  ",  # r11: scan m/d loop; d exits west to emit
    ">Ws      ^ ",  # r12: emit min to output, climb back at col 10
]

RELAY = [
    "+----+",
    "|>s@v|",
    "|^r <|",
    "+----+",
]


def _room(interior: list[str]) -> list[str]:
    w = len(interior[0])
    top = "+" + "-" * w + "+"
    return [top] + ["|" + row + "|" for row in interior] + [top]


def build_sort_ring2() -> str:
    cv = Canvas()
    cv.put(0, 0, ["+-+", "|I|", "+-+"])      # I: rows 0-2, cols 0-2
    cv.put(0, 5, _room(PUMP_INTERIOR))       # pump: rows 0-13, cols 5-17
    cv.put(14, 0, ["+-+", "|O|", "+-+"])     # O: rows 14-16, cols 0-2
    cv.put(14, 12, RELAY)                    # relay: rows 14-17, cols 12-17

    cv.pipe([(1, 3), (1, 4)])                # I -> pump left wall, entry row
    cv.pipe([(14, 8), (15, 8), (15, 3)])     # pump bottom col 8 -> O
    cv.pipe([(14, 11), (15, 11)])            # ring out -> relay left wall
    cv.cells[(15, 11)] = ">"                 # terminal bend into (15,12)
    # ring return: relay left wall -> 21-cell serpentine -> pump bottom
    cv.pipe([(16, 11), (16, 10), (18, 10), (18, 3), (17, 3), (17, 9), (14, 9)])
    return cv.render()
