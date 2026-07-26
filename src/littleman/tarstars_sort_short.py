"""Eighteen-square geometry for the tight shrinking-ring Sort machine.

``sort_07`` already reduced the pump's hot path, but its 19-column box
retained two geometry-only costs:

* an unused column between the two right-edge return arrows in the pump;
* a one-column offset between the pump and the unchanged relay.

This variant removes the unused pump column and shifts the relay left.  The
short pump-to-relay pipe needs a literal corner on its last cell (``v>``);
``Canvas.pipe`` cannot infer a turn directly into an adjacent room wall, so
the generator writes that terminal arrow explicitly.  The long return is
folded one cell farther left to preserve its exact 17-cell capacity.
"""

from __future__ import annotations

from .canvas import Canvas
from .sort_fast import RELAY, _room

TARSTARS_PUMP_INTERIOR = [
    ">@rMbm>rsv ",
    "      ^ md ",
    "^         <",
    "  v-W1MbW< ",
    "  >     v  ",
    " v  Mrsm<  ",
    "v amsW<    ",
    "Wa v  +    ",
    "v<>>r-Xv   ",
    "s     ++   ",
    "vsWdms<<   ",
    ">rbM1W- a ^",
]


def build_tarstars_sort_short() -> str:
    """Build the 18×18, capacity-preserving successor to ``sort_07``."""

    canvas = Canvas()
    canvas.put(0, 0, ["+-+", "|I|", "+-+"])
    canvas.put(0, 5, _room(TARSTARS_PUMP_INTERIOR))
    canvas.put(14, 0, ["+-+", "|O|", "+-+"])
    canvas.put(14, 12, RELAY)

    canvas.pipe([(1, 3), (1, 4)])
    canvas.pipe([(14, 8), (15, 8), (15, 3)])

    # Two cells are sufficient, but the final cell must turn east into the
    # shifted relay rather than continue south.
    canvas.pipe([(14, 11), (15, 11)])
    canvas.put(15, 11, [">"])

    # Shifting the relay removes one cell at the right; extending the lower
    # fold to column four keeps the capacity at the proven 17-cell minimum.
    canvas.pipe([(16, 11), (17, 11), (17, 4), (16, 4), (16, 10), (14, 10)])
    return canvas.render()
