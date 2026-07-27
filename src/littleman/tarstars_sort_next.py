"""Lane-swapped pass transition for the 18-square Sort machine.

The count test after each emitted minimum formerly climbed column eight.
Moving it to column seven shortens both the transition and the following
handler by one cell.  Column seven was also the equality arm of the scan,
so that arm is moved through column eight and duplicated on row nine.
The equality arm retains its old non-final length; its final output joins
the original west-side output path.
"""

from __future__ import annotations

from .canvas import Canvas
from .sort_fast import RELAY, _room

TARSTARS_NEXT_PUMP_INTERIOR = [
    ">@rMbm>rsv ",
    "      ^ md ",
    "^         <",
    "  v-W1MbW< ",
    "  >    v   ",
    " v Mrsm<   ",
    "v amsW<    ",
    "Wa v  +    ",
    "v<>>r-X v  ",
    "s^d ms+ <  ",
    "vsWdms<    ",
    ">rbM1W-a  ^",
]


def build_tarstars_sort_next() -> str:
    """Build the 18×18 lane-swapped successor to ``tarstars_sort_08``."""

    canvas = Canvas()
    canvas.put(0, 0, ["+-+", "|I|", "+-+"])
    canvas.put(0, 5, _room(TARSTARS_NEXT_PUMP_INTERIOR))
    canvas.put(14, 0, ["+-+", "|O|", "+-+"])
    canvas.put(14, 12, RELAY)

    canvas.pipe([(1, 3), (1, 4)])
    canvas.pipe([(14, 8), (15, 8), (15, 3)])
    canvas.pipe([(14, 11), (15, 11)])
    canvas.put(15, 11, [">"])
    canvas.pipe([(16, 11), (17, 11), (17, 4), (16, 4), (16, 10), (14, 10)])
    return canvas.render()
