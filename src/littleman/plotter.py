"""Plotter: Bresenham line on a 32x24 LM-75 display.

Architecture: one Bresenham WORKER (state ring) emits a per-pixel token
stream to a driver chain around the display.

Driver token protocol (chain ADDRDRV -> DATADRV -> SWAPDRV):
  v >= 1 : plot pixel at addr = v-1  (worker emits addr+1; one X splits
           plot(down) / end(up), no addr=0 ambiguity)
  v == -1: end of round -> commit frame

Layout: drivers stacked on the left, display on the right. Forward chain
runs straight down the stack; each driver's display pipe fans right
(ADDR curves up to the display top, DATA straight into the left, SWAP
curves down to the bottom). Each driver forwards its token
UNCONDITIONALLY before the X branch, so lanes carry no sends and the man
parks on r between values.

Wall roles:
  ADDRDRV: IN left, ADDR right, FWD bottom.
  DATADRV: IN top,  DATA right, FWD bottom.
  SWAPDRV: IN top,  SWAP right.
"""

from .canvas import Canvas


def _room(w, h, cells):
    grid = [[" "] * (w + 2) for _ in range(h + 2)]
    for c in range(w + 2):
        grid[0][c] = grid[h + 1][c] = "-"
    for r in range(h + 2):
        grid[r][0] = grid[r][w + 1] = "|"
    for r, c in ((0, 0), (0, w + 1), (h + 1, 0), (h + 1, w + 1)):
        grid[r][c] = "+"
    for (r, c), ch in cells.items():
        grid[r][c] = ch
    return ["".join(row) for row in grid]


def build_addrdrv() -> list:
    # interior 11x3. IN left(row2), ADDR right(row3), FWD bottom(col4).
    cells = {
        (1, 1): "v", (1, 5): "<", (1, 11): "<",        # end + return corridor
        (2, 1): ">", (2, 2): "@", (2, 3): "r", (2, 4): "s", (2, 5): "X",
        (2, 11): "^",
        (3, 5): ">", (3, 6): "M", (3, 7): "1", (3, 8): "W", (3, 9): "-",
        (3, 10): "s", (3, 11): "^",                    # decode addr, ADDR send(right)
    }
    return _room(11, 3, cells)


def build_datadrv() -> list:
    # interior 11x3. IN top(col3), DATA right(row3), FWD bottom(col4).
    cells = {
        (1, 1): "v", (1, 5): "<", (1, 11): "<",
        (2, 1): ">", (2, 2): "@", (2, 3): "r", (2, 4): "s", (2, 5): "X",
        (2, 11): "^",
        (3, 5): ">", (3, 6): "`", (3, 7): "1", (3, 8): "5", (3, 9): "`",
        (3, 10): "s", (3, 11): "^",                    # load 15, DATA send(right)
    }
    return _room(11, 3, cells)


def build_swapdrv() -> list:
    # interior 9x3. IN left(row2), SWAP out top(col2).
    cells = {
        (1, 1): "v", (1, 2): "s", (1, 3): "0", (1, 4): "<",   # end: 0 -> SWAP
        (2, 1): ">", (2, 2): "@", (2, 3): "r", (2, 4): "X",
        (3, 1): "^", (3, 4): "<",                             # discard: back via row3
    }
    return _room(9, 3, cells)
