"""Snake, geometry-pressed: the *same* rooms as :mod:`littleman.snake`,
re-placed so the bounding box is near-square instead of a tall column.

``snake_00.man`` is live at 8,838,759,329.  It stacks six stations in one
vertical column, so its box is 107x223 and its footprint is
``max(107, 223)**2 = 49,729`` -- paid for entirely by the height.  Nothing
about the *rooms* is wrong; only the placement is.  This module imports
snake.py's builders verbatim (never re-derives them) and lays the same
rooms out in three bands:

    band 1 | IN                 | DRAW
           |                    | (display block below DRAW)
    band 2 | TICKA
    band 3 | TICKB              | TICKC

Ring order is unchanged: IN -> TICKA -> TICKB -> TICKC -> DRAW ->
TOKENSPLIT -> IN.

WHAT MAY MOVE AND WHAT MAY NOT
------------------------------
Room internals are byte-identical (the builders are imported, not copied).
Pipe *routing* is free, but two bindings are load-bearing:

* ``IN`` is the only room with two incoming pipes (the ``I`` word stream on
  the top wall, the ring return on the bottom wall).  ``r`` binds to the
  nearest incoming pipe *end*, so both ends keep their snake_00 offsets
  relative to IN's origin -- ``(-1, +4)`` and ``(+65, +40)`` -- which makes
  every distance, and therefore every binding, identical.
* ``TOKENSPLIT`` is the only room with two outgoing pipes (the token pipe
  out of the top wall, the ring out of the bottom wall).  Both live inside
  :func:`littleman.snake.place_display_block`, which is called unchanged,
  so the driver race tuning (ADDRDRV lap 46 > DATADRV lap 40) and the DATA
  delay detour survive untouched.

Every other station has exactly one incoming and one outgoing pipe, so its
``s``/``r`` cannot be mis-bound and its ports are free to move.  The whole
machine uses only ``s`` and ``r`` (no ``S``/``R``/``U``/``q``), so
``Machine._turn_away`` -- the one place where *which wall* a pipe lands on
changes behaviour -- never runs.

RING CAPACITY
-------------
snake.py's design note: "Ring capacity must exceed the packet length (else
the cycle deadlocks with every man blocked on send). L can reach ~50 ...
so budget >= 70 cells of pipe."  The worst instantaneous ring load is the
mode-9 dead sweep, which emits ``L + 1`` display tokens *and* the packet:
about ``2 * 60`` values.  :data:`MIN_RING_CELLS` therefore demands a good
deal more than the docstring's 70, and :func:`ring_capacity` is asserted
by :func:`build_pressed_snake` on every build.
"""

from __future__ import annotations

from .canvas import Canvas
from .sim import Machine
from .snake import (
    build_draw,
    build_in,
    build_ticka,
    build_tickb,
    build_tickc,
    place_display_block,
)

# --- placement -------------------------------------------------------------
# (row, col) of each room's top-left corner.  Sizes, for reference:
#   IN 65x76   TICKA 35x92   TICKB 41x98   TICKC 13x47   DRAW 19x72
#   display block 26x64, bounding box rows R-9..R+16, cols C..C+63.
I_R, I_C = 0, 6            # the input room, 3x3, above IN's top port
IN_R, IN_C = 6, 3          # rows 6..70,   cols 3..78
DRAW_R, DRAW_C = 6, 84     # rows 6..24,   cols 84..155
DISP_R, DISP_C = 39, 84    # block box rows 30..55, cols 84..147
TICKA_R, TICKA_C = 75, 3   # rows 75..109, cols 3..94
TICKB_R, TICKB_C = 113, 3  # rows 113..153, cols 3..100
TICKC_R, TICKC_C = 113, 106  # rows 113..125, cols 106..152

# IN's two incoming ports, as offsets from IN's top-left, exactly as in
# snake_00 (there: origin (6, 8), ends (5, 12) and (71, 48)).
IN_WORD_PORT = (-1, 4)
IN_RING_PORT = (65, 40)

MIN_RING_CELLS = 160


def ring_capacity(text: str) -> int:
    """Total cell count of the six ring pipes (everything but the word
    stream and the display block's internal token/ADDR/DATA/SWAP pipes)."""
    machine = Machine.parse(text)
    stations = {
        id(room)
        for room in machine.rooms
        if room.kind == "room" and (room.bottom - room.top) > 4
    }
    tokensplit = _tokensplit(machine)
    stations.add(id(tokensplit))
    return sum(
        len(pipe.cells)
        for pipe in machine.pipes
        if id(pipe.source) in stations and id(pipe.dest) in stations
    )


def build_pressed_snake() -> str:
    """The pressed Snake machine.  Deterministic: no randomness anywhere."""
    cv = Canvas()

    # --- rooms (imported verbatim; internals are byte-identical) ----------
    cv.put(I_R, I_C, ["+-+", "|I|", "+-+"])
    cv.put(IN_R, IN_C, build_in())
    cv.put(DRAW_R, DRAW_C, build_draw())
    place_display_block(cv, DISP_R, DISP_C)
    cv.put(TICKA_R, TICKA_C, build_ticka())
    cv.put(TICKB_R, TICKB_C, build_tickb())
    cv.put(TICKC_R, TICKC_C, build_tickc())

    # --- word stream: I -> IN top wall, same offset as snake_00 -----------
    word_end = (IN_R + IN_WORD_PORT[0], IN_C + IN_WORD_PORT[1])
    cv.pipe([(I_R + 3, word_end[1]), word_end])

    # --- ring --------------------------------------------------------------
    # IN -> TICKA: straight down the band-1/band-2 gap, well left of the
    # ring return's run along row 71 (which starts at col 43).
    cv.pipe([(71, 20), (74, 20)])
    # TICKA -> TICKB: straight down the band-2/band-3 gap.
    cv.pipe([(110, 20), (112, 20)])
    # TICKB -> TICKC: across the band-3 lane.
    cv.pipe([(115, 101), (115, 105)])
    # TICKC -> DRAW: up the far-right lane, right of the display block
    # (which ends at col 147), into DRAW's bottom wall.
    cv.pipe([(112, 150), (25, 150)])
    # DRAW -> TOKENSPLIT: down the DRAW/display gap row, then down the
    # inter-column lane into TOKENSPLIT's left wall at row DISP_R + 2.
    cv.pipe([(25, 90), (28, 90), (28, 82), (DISP_R + 2, 82), (DISP_R + 2, 83)])
    # TOKENSPLIT -> IN: out of the bottom wall at col DISP_C + 7, below the
    # display block, up the inter-column lane, then along the row under IN.
    ring_end = (IN_R + IN_RING_PORT[0], IN_C + IN_RING_PORT[1])
    cv.pipe([(DISP_R + 7, DISP_C + 7), (58, DISP_C + 7), (58, 80),
             (ring_end[0], 80), ring_end])
    cv.cells[ring_end] = "^"                 # terminal bend into IN

    text = cv.render()
    assert ring_capacity(text) >= MIN_RING_CELLS, ring_capacity(text)
    return text


def _tokensplit(machine: Machine):
    """The 7x16 TOKENSPLIT room: the only room with two outgoing pipes."""
    counts: dict[int, int] = {}
    for pipe in machine.pipes:
        counts[id(pipe.source)] = counts.get(id(pipe.source), 0) + 1
    return next(
        room
        for room in machine.rooms
        if room.kind == "room" and counts.get(id(room), 0) == 2
    )
