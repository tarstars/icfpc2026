"""Pathfinder: BFS maze robot with a 16x16 display.

Two things live here:

1. A pure-Python reference (:func:`reference_rounds`) that reproduces the
   expected frames for every public test case.  The tie-break rule (up,
   right, down, left) is a preference over the *move direction taken*, so
   the reference BFSes backwards from the flag and walks forward, always
   stepping to a neighbour whose distance is one less.

2. A generated littleman machine.  The board lives as sixteen 64-bit words
   in a ring pipe (one word per board row, four 16-bit bit-planes packed
   into each word):

       bits  0..15  avail   -- open and not yet reached by the wave
       bits 16..31  slot0   -- cells whose distance-to-flag == 0 (mod 3)
       bits 32..47  slot1   -- ... == 1 (mod 3)
       bits 48..63  slot2   -- ... == 2 (mod 3)

   Bit 15 of every plane is a border wall, so bit 63 is always clear and
   the words stay non-negative; a ``-1`` MARK value closes the ring.

   A BFS wave is one lap of the ring.  Row ``y``'s new cells are

       t = ((a[y]<<1) | (a[y]>>1) | a[y-1] | a[y+1]) & avail[y]

   where ``a`` is the frontier plane.  ``a[y+1]`` needs a lookahead, so the
   lap holds row ``y-1`` back by one element and emits it once row ``y``
   has been read.  Distances mod 3 are enough to walk the path back,
   because the grid is bipartite: a neighbour of a cell at distance ``d``
   is at ``d-1`` or ``d+1``, never ``d``.

   The display keeps its next buffer between frames.  The board is drawn
   once during the setup round; every later frame only rewrites the pixel
   the robot left, the pixel it moved to, and commits with SWAP=1.
"""

from __future__ import annotations

from collections import deque

W = H = 16
COLOR_PATH = 0
COLOR_WALL = 7
COLOR_FLAG = 9
COLOR_ROBOT = 10


# --------------------------------------------------------------- reference


def bfs_distances(board: list[int], target: tuple[int, int]) -> list[int]:
    """Distance from every cell to ``target`` (-1 when unreachable)."""
    dist = [-1] * (W * H)
    tx, ty = target
    dist[ty * W + tx] = 0
    queue = deque([(tx, ty)])
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < W and 0 <= ny < H):
                continue
            if board[ny * W + nx] or dist[ny * W + nx] >= 0:
                continue
            dist[ny * W + nx] = dist[y * W + x] + 1
            queue.append((nx, ny))
    return dist


def render_frame(board, robot, flag) -> list[str]:
    rows = []
    for y in range(H):
        row = []
        for x in range(W):
            value = COLOR_WALL if board[y * W + x] else COLOR_PATH
            if flag is not None and (x, y) == flag:
                value = COLOR_FLAG
            if (x, y) == robot:
                value = COLOR_ROBOT
            row.append("%x" % value)
        rows.append("".join(row))
    return rows


def reference_rounds(rounds) -> list[list[list[str]]]:
    """Frames for every round of one test case, given its ``rounds`` input."""
    setup = [int(v) for v in rounds[0]["in"]]
    board, rx, ry = setup[:256], setup[256], setup[257]
    out = [[render_frame(board, (rx, ry), None)]]
    for rnd in rounds[1:]:
        fx, fy = int(rnd["in"][0]), int(rnd["in"][1])
        dist = bfs_distances(board, (fx, fy))
        frames = []
        cx, cy, d = rx, ry, dist[ry * W + rx]
        while d > 0:
            for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < W and 0 <= ny < H and dist[ny * W + nx] == d - 1:
                    cx, cy, d = nx, ny, d - 1
                    break
            else:  # pragma: no cover - only reachable on a broken board
                raise RuntimeError("no shortest-path successor")
            frames.append(render_frame(board, (cx, cy), (fx, fy) if d else None))
        rx, ry = cx, cy
        out.append(frames)
    return out
