"""Two-cell hot-loop successor to the accepted 18-square Sort machine.

The accepted shrinking-ring pump reads every list value through a repeated
input loop whose return path takes eight ticks.  ``chatgpt2_sort_01`` replaces
the repeated ``r`` with ``U`` and moves the return arrow one cell east:

    accepted:  r -> s -> v -> d -> m -> ... -> ^ -> r
    candidate: U -> s -> v -> d -> m -> ^ -> U

``U`` receives the next input value and turns away from the input pipe, which
points the man directly toward the existing ring send.  The initial length
prefix still uses the unchanged ordinary ``r``.  Room placement, every pipe,
all capacities, and the 18x18 box are unchanged.
"""
from __future__ import annotations

from .canvas import Canvas
from .sort_fast import RELAY, _room


PUMP_INTERIOR = [
    ">@rMbm>Usv ",
    "       ^md ",
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


def build_chatgpt2_sort_01() -> str:
    """Build the exact 18x18 U-load-loop candidate."""

    canvas = Canvas()
    canvas.put(0, 0, ["+-+", "|I|", "+-+"])
    canvas.put(0, 5, _room(PUMP_INTERIOR))
    canvas.put(14, 0, ["+-+", "|O|", "+-+"])
    canvas.put(14, 12, RELAY)

    canvas.pipe([(1, 3), (1, 4)])
    canvas.pipe([(14, 8), (15, 8), (15, 3)])

    # Preserve the accepted two-cell pump-to-relay pipe exactly.
    canvas.pipe([(14, 11), (15, 11)])
    canvas.put(15, 11, [">"])

    # Preserve the accepted 17-cell storage/capacity pipe exactly.
    canvas.pipe([(16, 11), (17, 11), (17, 4), (16, 4), (16, 10), (14, 10)])
    return canvas.render()


if __name__ == "__main__":
    print(build_chatgpt2_sort_01(), end="")
