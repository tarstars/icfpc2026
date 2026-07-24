"""Shrinking-ring machine for reverse-a-list.

One pump room + one relay room form a ring (pump-out -> relay -> pump-in).
Load phase: read n, push n values into the ring. Emit phase, per cycle:
walk a delay corridor (so every in-flight value has parked in the ring-in
pipe before `q` counts them), then

    q           BP = j (ring size; 0 when a round is done)
    a           j = 0 -> straight to the input lane (blocks on next n)
    m, d        j = 1 -> straight down to a direct take
    m, loop     else relay j-1 values, exit, take

The take consumes the target (emit to output, no re-send), so the ring
shrinks and successive cycles emit v_n, v_{n-1}, ..., v_1.

Corridor safety: corridor length (~58 ticks) must exceed the worst-case
in-flight time L_out + relay lap + L_in; tested in the unit tests.
"""

from .canvas import Canvas

# interior rows 1-12, cols 1-17.  Attachments (rel):
#   input  TOP    col4      ring-out BOTTOM col9
#   ring-in BOTTOM col15    output  BOTTOM col4


def build_pump() -> list:
    """Assemble the pump room grid from the layout spec below.

    Built programmatically because several cells are position-critical;
    a table of (row, col, char) is less error-prone than ASCII art.
    """
    w, h = 17, 12  # interior
    grid = [[" "] * (w + 2) for _ in range(h + 2)]
    for c in range(w + 2):
        grid[0][c] = grid[h + 1][c] = "-"
    for r in range(h + 2):
        grid[r][0] = grid[r][w + 1] = "|"
    for r, c in ((0, 0), (0, w + 1), (h + 1, 0), (h + 1, w + 1)):
        grid[r][c] = "+"

    cells = {
        # r1: entry + load loop top
        (1, 1): ">", (1, 2): "@", (1, 3): "r", (1, 4): "b", (1, 5): "m",
        (1, 6): ">", (1, 7): "r", (1, 8): "s", (1, 9): "v",
        # r2: load loop bottom
        (2, 6): "^", (2, 8): "m", (2, 9): "d",
        # r3-r6: delay corridor
        (3, 9): "<", (3, 2): "v",
        (4, 2): ">", (4, 3): ">", (4, 17): "v",
        (5, 17): "<", (5, 2): "v",
        (6, 2): ">", (6, 17): "v",
        # r7: q / empty-ring branch; straight-left lane is the input lane
        (7, 17): "<", (7, 15): "q", (7, 14): "a", (7, 1): "^",
        # col14 descent: j-1 counter and j==1 branch
        (8, 14): "m",
        (9, 14): "d", (9, 13): "m", (9, 7): "v",
        # r10-r11: skip loop (relays BP+1 values)
        (10, 7): ">", (10, 8): "r", (10, 9): "s", (10, 10): "v",
        (11, 7): "^", (11, 9): "m", (11, 10): "d",
        # r12: take row (direct-take merge from col14, loop exit at col10)
        (12, 14): "<", (12, 10): "<", (12, 9): "r", (12, 4): "s",
        (12, 3): "^",
    }
    for (r, c), ch in cells.items():
        grid[r][c] = ch
    return ["".join(row) for row in grid]


RELAY = [
    "+---+",
    "| @v|",
    "|>sv|",
    "|^r<|",
    "+---+",
]


def build_reverse() -> str:
    cv = Canvas()
    cv.put(0, 0, ["+-+", "|I|", "+-+"])            # I: rows 0-2
    cv.put(3, 4, build_pump())                      # pump: rows 3-16, cols 4-22
    cv.put(16, 0, ["+-+", "|O|", "+-+"])            # O: rows 16-18
    cv.put(19, 15, RELAY)                           # relay: rows 19-23, cols 15-19

    cv.pipe([(1, 3), (1, 8), (2, 8)])               # I -> pump top col4(rel)
    cv.pipe([(17, 8), (18, 8), (18, 3)])            # pump bottom col4 -> O
    cv.pipe([(17, 13), (22, 13), (22, 14)])         # ring-out: pump bottom col9 -> relay left
    cv.pipe(                                        # ring-in: relay right -> snake -> pump bottom col16
        [(21, 20), (21, 27), (19, 27), (19, 21), (18, 21), (18, 20), (17, 20)]
    )
    return cv.render()
