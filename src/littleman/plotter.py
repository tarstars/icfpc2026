# BROKEN SKETCH - do not trust. Rewrite from claude/plotter-plan.md
# (room maps here predate the v2 architecture and have known bugs).
"""Plotter: Bresenham on a 32x24 LM-75.

Reformulation: run Bresenham on addr = 32*y + x. Steps are addr += SX
(+-1) and/or addr += SYW (+-32); the iteration count N = max(dx, -dy)
is known up front, so both pumps just count down BP - no handshakes.
Err is stored doubled (E = 2*err): tests are E-dy >= 0 / dx-E >= 0 and
updates add 2dy/2dx via two + ops.

Chain:  I -> S1..S5 (stream rooms) -> E-pump -> A-pump -> DISPATCH
        DISPATCH -> PLOT (-> display ADDR+DATA) / SWAP room (-> bottom)

Stream protocol out of S5 (all per round):
  [N, N, E0, dy, dx, SX, SYW, addr]
E-pump keeps [dy, dx, E] circulating in its loop, BP = N; per pixel it
sends delta = c1 + 2*c2 in {1,2,3} to the A-pump. A-pump keeps
[SX, SYW, addr] in its loop, BP = N; plots addr after each update, and
after the last pixel sends -1, which DISPATCH routes to the SWAP room
(commit frame with 0: rounds don't persist).
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


def _row(cells, r, c0, s):
    for i, ch in enumerate(s):
        if ch != " ":
            cells[(r, c0 + i)] = ch


def build_s1() -> list:
    """[x0,y0,x1,y1] -> [y0, x0, x0, y0, y1, x1]."""
    cells = {}
    _row(cells, 1, 1, ">@rMrsWssWsrMv")
    _row(cells, 2, 1, "^         sWr<")
    return _room(14, 2, cells)


def build_s2() -> list:
    """-> [x0, y0, y1, x1, addr] with addr = 32*y0 + x0 held in B."""
    cells = {}
    _row(cells, 1, 1, ">@rM`32`*Mr+Mv")
    _row(cells, 2, 1, "^ sWsrsrsrsr <")
    return _room(14, 2, cells)


def build_s3() -> list:
    """-> [y0, y1, dx, SX, addr]."""
    cells = {}
    _row(cells, 1, 7, ">Ns1Ns  v")  # x1-x0 < 0: dx=-(d), SX=-1
    _row(cells, 2, 1, ">@rMrsrsr-X")
    _row(cells, 2, 12, "v")
    _row(cells, 3, 11, ">>s1s v")  # >=0: dx=d, SX=+1
    _row(cells, 4, 1, "^             rs<")  # tail: addr through; merge
    cells[(4, 15)] = "<"
    cells[(4, 14)] = "r"
    cells[(4, 13)] = "s"
    for c in (14, 15):
        pass
    return _room(17, 4, cells)


def build_s4() -> list:
    """-> [dy, dx, dy, dx, SX, SYW, addr]."""
    cells = {}
    _row(cells, 1, 7, ">MsrsWsWsrs`32`Nsrs  v")  # y1-y0 < 0: dy as-is, SYW=-32
    _row(cells, 2, 1, ">@rMr-Xv")
    _row(cells, 3, 7, ">>NMsrsWsWsrs`32`srs v")  # >=0: dy=-(d), SYW=+32
    _row(cells, 4, 1, "^")
    cells[(4, 28)] = "<"
    cells[(4, 27)] = "<"
    return _room(28, 4, cells)


def build_s5() -> list:
    """-> [N, N, E0, dy, dx, SX, SYW, addr]."""
    cells = {}
    _row(cells, 1, 7, ">WNssWM+s   v")  # e0 < 0: N = -dy
    _row(cells, 2, 1, ">@rMr+Xv")
    _row(cells, 3, 7, ">>W-NssWM+s v")  # e0 >= 0: N = dx
    _row(cells, 4, 1, "^    srsrsrsrsr<")
    cells[(4, 19)] = "<"
    return _room(19, 4, cells)


def build_epump() -> list:
    """BP=N iterations; loop [dy,dx,E]; sends delta to A-pump.

    in: from-S5 (LEFT row1), loop-in (RIGHT row1)
    out: to-A (BOTTOM col2), loop-out (RIGHT row8 area)
    """
    cells = {}
    # init: r(N) b, fwd N, seed loop [dy,dx,E0], fwd SX,SYW,addr
    _row(cells, 1, 1, ">@rbrsrMrsrsWsrsrsrs v")
    # iteration entry: a-branch on BP; flush lane straight
    _row(cells, 2, 1, "^  v")
    _row(cells, 2, 21, "<")
    _row(cells, 3, 1, "   >a")  # BP>0 -> ccw(right->up)?? no: iterate lane
    # -- iteration rows are built below --
    return _room(24, 10, cells)


def build_plotter() -> str:
    raise NotImplementedError
