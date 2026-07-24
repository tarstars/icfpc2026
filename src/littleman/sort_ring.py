"""Shrinking-ring selection sort (candidate sort_02).

Same skeleton as reverse.py's machine: pump + relay ring, delay corridor,
q-counted ring size, empty-ring fallthrough to the blocking input lane.
The middle section is a min-scan instead of take-by-position:

    q, a        BP = j; 0 -> input lane
    m, r, M     BP = j-1 comparisons; candidate min in B
    a           j == 1 -> bypass scan, emit candidate
    scan loop   r, -, X on sign of (value - min):
                  >= 0: +, s   (requeue value, keep min)
                  <  0: +, W, s (requeue old min, keep value)
                m, d until BP = 0
    W, s        emit min to output; ring shrank by one

B survives r/s/m/d, so the candidate min rides in the off hand through
the whole scan. Values may be negative; the comparison is a subtraction
sign test, never a sign test on raw data.
"""

from .canvas import Canvas


def build_pump() -> list:
    w, h = 17, 13  # interior
    grid = [[" "] * (w + 2) for _ in range(h + 2)]
    for c in range(w + 2):
        grid[0][c] = grid[h + 1][c] = "-"
    for r in range(h + 2):
        grid[r][0] = grid[r][w + 1] = "|"
    for r, c in ((0, 0), (0, w + 1), (h + 1, 0), (h + 1, w + 1)):
        grid[r][c] = "+"

    cells = {
        # r1-r2: entry + load loop
        (1, 1): ">", (1, 2): "@", (1, 3): "r", (1, 4): "b", (1, 5): "m",
        (1, 6): ">", (1, 7): "r", (1, 8): "s", (1, 9): "v",
        (2, 6): "^", (2, 8): "m", (2, 9): "d",
        # r3-r6: delay corridor ((4,15) doubles as the emit-climb rejoin)
        (3, 9): "<", (3, 2): "v",
        (4, 2): ">", (4, 15): ">", (4, 17): "v",
        (5, 17): "<", (5, 2): "v",
        (6, 2): ">", (6, 17): "v",
        # r7: ring-size probe and empty-ring branch
        (7, 17): "<", (7, 15): "q", (7, 14): "a", (7, 1): "^",
        # r8: candidate pickup, j==1 bypass at (8,7)
        (8, 14): "<", (8, 13): "m", (8, 12): "r", (8, 11): "M",
        (8, 7): "a", (8, 1): "v",
        # r9-r12: min-scan loop
        (9, 10): ">", (9, 11): "+", (9, 12): "W", (9, 13): "s", (9, 14): "v",
        (10, 7): ">", (10, 8): "r", (10, 9): "-", (10, 10): "X", (10, 11): "v",
        (11, 10): ">", (11, 11): ">", (11, 12): "+", (11, 13): "s", (11, 14): "v",
        (12, 14): "<", (12, 11): "m", (12, 7): "d", (12, 1): "v",
        # r13: emit lane and climb back to the corridor
        (13, 1): ">", (13, 2): "W", (13, 3): "s", (13, 15): "^",
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


def build_sort_ring() -> str:
    cv = Canvas()
    cv.put(0, 0, ["+-+", "|I|", "+-+"])             # I: rows 0-2
    cv.put(3, 4, build_pump())                       # pump: rows 3-17, cols 4-22
    cv.put(17, 0, ["+-+", "|O|", "+-+"])             # O: rows 17-19
    cv.put(19, 15, RELAY)                            # relay: rows 19-23, cols 15-19

    cv.pipe([(1, 3), (1, 8), (2, 8)])                # I -> pump top col4(rel)
    cv.pipe([(18, 7), (19, 7), (19, 3)])             # pump bottom col3 -> O
    cv.pipe([(18, 13), (22, 13), (22, 14)])          # ring-out -> relay left
    cv.pipe([(21, 20), (21, 26), (19, 26), (19, 20), (18, 20)])  # relay -> pump
    return cv.render()
