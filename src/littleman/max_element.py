"""Streaming max: single room, running max in hand B, no storage.

    r n, b          BP = n
    r v1, M         candidate max in B
    loop (enter via the return row, whose `m` decrements first):
        m, d        BP exhausted -> exit
        r, -, X     sign of (value - max)
          > 0 / = 0 lane: +, M   (adopt value; = case rewrites same value)
          < 0 lane:       +      (reconstruct, discard)
    W, s, H         emit max and halt (single round)
"""

from .canvas import Canvas


def build_pump() -> list:
    w, h = 11, 6
    grid = [[" "] * (w + 2) for _ in range(h + 2)]
    for c in range(w + 2):
        grid[0][c] = grid[h + 1][c] = "-"
    for r in range(h + 2):
        grid[r][0] = grid[r][w + 1] = "|"
    for r, c in ((0, 0), (0, w + 1), (h + 1, 0), (h + 1, w + 1)):
        grid[r][c] = "+"
    cells = {
        # r1: prologue (BP = n; the return row's m makes it n-1 per lap)
        (1, 1): ">", (1, 2): "@", (1, 3): "r", (1, 4): "b",
        (1, 5): "r", (1, 6): "M", (1, 11): "v",
        # r2: value < max lane (just reconstruct)
        (2, 5): ">", (2, 6): "+", (2, 10): "v",
        # r3: compare
        (3, 2): ">", (3, 3): "r", (3, 4): "-", (3, 5): "X", (3, 6): "v",
        # r4: value >= max lane (adopt into B)
        (4, 5): ">", (4, 6): ">", (4, 7): "+", (4, 8): "M", (4, 9): "v",
        # r5: return row: counter, loop-or-exit branch
        (5, 11): "<", (5, 10): "<", (5, 9): "<", (5, 8): "m", (5, 2): "d",
        (5, 1): "v",
        # r6: emit and halt
        (6, 1): ">", (6, 2): "W", (6, 3): "s", (6, 4): "H",
    }
    for (r, c), ch in cells.items():
        grid[r][c] = ch
    return ["".join(row) for row in grid]


def build_max_element() -> str:
    cv = Canvas()
    cv.put(0, 0, ["+-+", "|I|", "+-+"])     # I: rows 0-2, cols 0-2
    cv.put(3, 1, build_pump())              # pump: rows 3-10, cols 1-13
    cv.put(11, 0, ["+-+", "|O|", "+-+"])    # O: rows 11-13, cols 0-2
    cv.pipe([(1, 3), (1, 5), (2, 5)])       # I right -> bend down -> pump top
    cv.pipe([(11, 4), (12, 4), (12, 3)])    # pump bottom -> bend -> O right
    return cv.render()
