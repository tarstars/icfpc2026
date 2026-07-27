"""Step 4: shift the middle room one column left, then fold the return pipe.

R2 spans cols 5-33 and is what pins the width; the return pipe has to climb
east of it at col 34.  Moving R2 to cols 4-32 frees col 33 for the climb.

Every pipe that touches R2 has to keep its attachment point RELATIVE to R2,
because R2 has two incoming and two outgoing pipes and the nearest-pipe rule
resolves on those cells.  R1 has a single outgoing pipe, so that one's source
may move freely.
"""

import sys

from littleman.alexey_piperoute import Router, RouteError
from littleman.sim import Machine

from lab import HERE, check, save

TEXT = (HERE / "step1.man").read_text()
SHIFT = int(sys.argv[1]) if len(sys.argv) > 1 else 1
TARGET14 = int(sys.argv[2]) if len(sys.argv) > 2 else 13

lines = TEXT.rstrip("\n").split("\n")
W = max(len(x) for x in lines)
grid = [list(x.ljust(W)) for x in lines]

m = Machine.parse(TEXT)
R2 = next(r for r in m.rooms if (r.top, r.left) == (10, 5))
OUT = next(r for r in m.rooms if getattr(r, "kind", None) == "output")
oblock = [[grid[r][c] for c in range(OUT.left, OUT.right + 1)]
          for r in range(OUT.top, OUT.bottom + 1)]
block = [[grid[r][c] for c in range(R2.left, R2.right + 1)]
         for r in range(R2.top, R2.bottom + 1)]

# lift every pipe that touches R2 FIRST -- one of them terminates on a cell
# the moved room will occupy, so erasing after the move deletes a wall
for p in m.pipes:
    if p.source is R2 or p.dest is R2:
        for (r, c) in p.cells:
            grid[r][c] = " "

# then lift the room and put it back SHIFT columns left
for r in range(R2.top, R2.bottom + 1):
    for c in range(R2.left, R2.right + 1):
        grid[r][c] = " "
for i, row in enumerate(block):
    for j, ch in enumerate(row):
        grid[R2.top + i][R2.left - SHIFT + j] = ch
for r in range(OUT.top, OUT.bottom + 1):
    for c in range(OUT.left, OUT.right + 1):
        grid[r][c] = " "
for i, row in enumerate(oblock):
    for j, ch in enumerate(row):
        grid[OUT.top + i][OUT.left - SHIFT + j] = ch

text = "\n".join("".join(row).rstrip() for row in grid) + "\n"

# re-lay them, each keeping its attachment offset inside R2.  The two short
# jogs are placed by hand: route_safe refuses any arrowhead next to a room,
# but an arrowhead there is only a phantom start if it points AWAY from that
# room, and these point along the wall or into it.
# the two roof pipes are jogged on DIFFERENT rows so they cannot collide:
# R1->R2 runs west along row 9, R2->R1 runs east along row 8.
EXPLICIT = [
    ([(8, 11)] + [(9, c) for c in range(11, 10 - SHIFT, -1)], (1, 0), "R1->R2"),
    ([(9, 9 - SHIFT)] + [(8, c) for c in range(9 - SHIFT, 10)], (-1, 0), "R2->R1"),
    ([(9, 30 - SHIFT), (8, 30 - SHIFT)], (-1, 0), "R2->O"),
]
ROUTED = [
    ((23, 4), (12, 4 - SHIFT), (0, 1), (0, -1), TARGET14, "R3->R2"),
]

for start, end, into, out, target, label in ROUTED:
    rt = Router(text)
    try:
        cells = rt.route_safe(start, end, into=into, target=target, out=out)
    except RouteError as exc:
        print(f"{label}: FAILED {exc}")
        raise SystemExit(1)
    text = rt.apply(cells, into=into)
    print(f"{label}: {len(cells)} cells {cells[0]} -> {cells[-1]}")

for cells, into, label in EXPLICIT:
    rt = Router(text)
    text = rt.apply(cells, into=into)
    print(f"{label}: {len(cells)} cells {cells[0]} -> {cells[-1]} (hand-placed)")

fp, passed, score = check(text, f"step4 (shift {SHIFT}, R3->R2 target {TARGET14})",
                          want_pipes=6)
if passed == 9:
    (HERE / f"shift{SHIFT}.man").write_text(text)
