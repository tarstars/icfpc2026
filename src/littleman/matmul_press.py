"""Matrix Multiply, geometry-pressed: the *same* rooms as ``matmul_02.man``,
re-placed so nothing but the controller and its relay band pays for the box.

``matmul_02`` is live at 33,286,994,352.  It is 183 wide x 180 tall, so its
footprint -- ``max(183, 180)**2 = 33,489`` -- is paid twice over by sprawl:
only 42.7% of the box is room area and only 5.9% of its cells carry a glyph.

WHAT ACTUALLY FIXES THE BOX
---------------------------
There is exactly one big object: the controller room, 129 rows x 109 cols.
Every pipe leaves it through its *bottom* border at a fixed zone column, so
the relay band is welded 14 rows under it::

    rows  0..128   controller (129 x 109)
    row     129    first pipe row (controller_bottom + 1)
    rows 132..138  the ten VERTICAL_RELAY rooms + I
    row     139    relay output cells        (relay_top + 7)
    row     142    short-ring return runs    (relay_top + 10), cols 24..69

That stack is 143 rows before a single long pipe is drawn, and it is
incompressible without moving a port, so the press is a *height* press and
the floor is near 144.  ``matmul_02`` instead spent 180 rows and 183 cols
draping the A ring, the B ring and the output pipe *below* the band, in a
region 74 columns wider than the controller.  The pressed box is 128 x 145,
footprint 21,025 -- 62.8% of 33,489 -- at identical ticks.

WHAT THIS MODULE MOVES
----------------------
Nothing but the three long pipes.  The controller block, the ten relay
rooms, I, O and the sixteen short pipes are placed by the *same* helpers
(``_compile_controller``, ``_put_short_ring``, ``_put_relay_input``) that
build the live artifact, at the same relative offsets, so every room
interior and every short pipe is byte-identical by construction.

The A ring (334 cells) and the B ring (268 cells) become two *nested*
rectangles standing in the free column strip to the right of the
controller, and the output pipe (106 cells) climbs a lane to their left::

    O: 139,91 -> 140,91 -> 140,112 -> 57,112
    A: 139,85 -> 141,85 -> 141,118 -> 58,118 -> 58,127 -> 144,127 -> 144,22 -> 129,22
    B: 139,77 -> 142,77 -> 142,121 -> 68,121 -> 68,124 -> 143,124 -> 143,72 -> 129,72 -> 129,74

Both the turn order and the nesting are forced, not stylistic.  A pipe must
step *down* out of its relay before it may turn, so the pipe leaving at
column x pins column x from row 139 to its own turn row; since every route
then runs rightwards past the columns to its left, the turn rows must
descend right to left -- output (col 91) at 140, A (85) at 141, B (77) at
142.  A comes home leftwards to ``a_in`` (col 22) and B to ``b_out - 4``
(col 72), so B must return *above* A or its homeward column would sever A's
return run: B on 143, A on 144, and the box ends at row 144.  Row 142 out
to column 69 is the short-ring return run, which is why no return run may
share it.  ``LANE_O`` stays left of ``LANE_A_UP`` for the same reason A's
turn row is below the output's.

CAPACITY IS THE INVARIANT
-------------------------
A holds N*M and B holds M*K values, both up to 16*16 = 256, so each ring
needs at least 256 cells.  Rather than trim to the invariant, the fold
depths ``TA`` and ``TB`` are *solved* so that all three long pipes keep
their ``matmul_02`` length to the cell (334 / 268 / 106).  Capacity, ring
rotation phase and per-value shift cost are therefore unchanged by
construction, not by argument.
"""

from __future__ import annotations

from .canvas import Canvas
from .matmul_ring import _compile_controller, _put_relay_input, _put_short_ring

#: (in_zone, out_zone) for the six K-sized scalar rings, in artifact order.
SHORT_RINGS = (
    ("n_in", "n_out"),
    ("m_in", "m_out"),
    ("k_in", "k_out"),
    ("work_m_in", "work_m_out"),
    ("factor_in", "factor_out"),
    ("sum_in", "sum_out"),
)

#: Long-pipe lengths in ``submissions/matmul/matmul_02.man``; kept exactly.
A_CELLS = 334
B_CELLS = 268
O_CELLS = 106

# Column lanes in the free strip right of the 109-wide controller.
LANE_O = 112  # output climbs here, left of A so it clears A's exit run
LANE_A_UP, LANE_A_DOWN = 118, 127  # outer rectangle
LANE_B_UP, LANE_B_DOWN = 121, 124  # nested inside A


def _fold_row(fixed: int, drops: int, target: int) -> int:
    """Top row of a fold whose two vertical legs make up the slack.

    ``fixed`` counts every horizontal run and stub cell; ``drops`` is the
    sum of the two legs' base rows.  The route is ``fixed + drops - 2*row``
    cells long, so the row that hits ``target`` exactly is solved, not
    guessed.  Raises when no whole row does.
    """
    doubled = fixed + drops - target
    if doubled < 2 or doubled % 2:
        raise ValueError(f"cannot fold {target} cells over {fixed}/{drops}")
    return doubled // 2


def build_matmul_press() -> str:
    """Build the pressed Matrix Multiply machine (144 x 144 bounding box)."""
    controller = _compile_controller()
    canvas = Canvas()
    canvas.put(0, 0, controller.rows)
    bottom = controller.height + 1  # the controller's bottom border row
    zone = controller.zones

    input_x = zone["input"]
    input_top = bottom + 4
    canvas.put(input_top, input_x - 1, ["+-+", "|I|", "+-+"])
    canvas.pipe([(input_top - 1, input_x), (bottom + 1, input_x)])

    relay_top = bottom + 4
    for in_zone, out_zone in SHORT_RINGS:
        _put_short_ring(
            canvas,
            controller_bottom=bottom,
            relay_top=relay_top,
            out_x=zone[out_zone],
            in_x=zone[in_zone],
        )

    # Row map below the band.  Every relay pipe must step *down* out of its
    # room before it may turn, so a pipe leaving at column x pins column x
    # from row 139 to its own turn row: the three turn rows are therefore
    # forced into right-to-left order, output (col 91) first, then A (85),
    # then B (77).  B returns above A because B's homeward column (72) would
    # otherwise sever A's return run.
    out_exit, a_exit, b_exit = bottom + 12, bottom + 13, bottom + 14
    b_ret, a_ret = bottom + 15, bottom + 16

    out_start = _put_relay_input(
        canvas, controller_bottom=bottom, relay_top=relay_top, out_x=zone["output"]
    )
    out_stub = out_exit - out_start[0] + 1
    out_head = out_exit + out_stub + (LANE_O - out_start[1]) - O_CELLS
    canvas.put(out_head - 3, LANE_O - 1, ["+-+", "|O|", "+-+"])
    canvas.pipe(
        [out_start, (out_exit, out_start[1]), (out_exit, LANE_O), (out_head, LANE_O)]
    )

    a_start = _put_relay_input(
        canvas, controller_bottom=bottom, relay_top=relay_top, out_x=zone["a_out"]
    )
    a_in = zone["a_in"]
    a_fixed = (
        (a_exit - a_start[0] + 1)
        + (LANE_A_UP - a_start[1])
        + (LANE_A_DOWN - LANE_A_UP)
        + (LANE_A_DOWN - a_in)
        + (a_ret - bottom - 1)
    )
    a_top = _fold_row(a_fixed, a_exit + a_ret, A_CELLS)
    canvas.pipe(
        [
            a_start,
            (a_exit, a_start[1]),
            (a_exit, LANE_A_UP),
            (a_top, LANE_A_UP),
            (a_top, LANE_A_DOWN),
            (a_ret, LANE_A_DOWN),
            (a_ret, a_in),
            (bottom + 1, a_in),
        ]
    )

    b_start = _put_relay_input(
        canvas, controller_bottom=bottom, relay_top=relay_top, out_x=zone["b_out"]
    )
    b_in, b_return_x = zone["b_in"], zone["b_out"] - 4
    b_fixed = (
        (b_exit - b_start[0] + 1)
        + (LANE_B_UP - b_start[1])
        + (LANE_B_DOWN - LANE_B_UP)
        + (LANE_B_DOWN - b_return_x)
        + (b_ret - bottom - 1)
        + (b_in - b_return_x)
    )
    b_top = _fold_row(b_fixed, b_exit + b_ret, B_CELLS)
    canvas.pipe(
        [
            b_start,
            (b_exit, b_start[1]),
            (b_exit, LANE_B_UP),
            (b_top, LANE_B_UP),
            (b_top, LANE_B_DOWN),
            (b_ret, LANE_B_DOWN),
            (b_ret, b_return_x),
            (bottom + 1, b_return_x),
            (bottom + 1, b_in),
        ]
    )
    canvas.cells[(bottom + 1, b_in)] = "^"

    return canvas.render()
