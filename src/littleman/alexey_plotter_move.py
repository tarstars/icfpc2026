"""plotter_04: relocate the top block into the free band. Live 20/20, 1.80x.

    plotter_02  fp 148,225  ticks 114,065  16,905,772,730
    plotter_04  fp 106,276  ticks  88,146   9,367,793,668

Builds on plotter_03 (rooms trimmed to their content, which on its own was a
no-op). The trim is what makes this possible: it freed columns 81-137 across
rows 62-322, a 57x261 empty band beside the three big rooms.

WHY IT IS ONE EDIT AND NOT TWELVE. The five small rooms plus I form a linear
chain -- I -> A -> B -> C -> D -> E -> BIG1 -- joined by 2- and 3-cell pipes.
Every one of those pipes is INTERNAL to the block; exactly one pipe leaves
it, E's bottom port into BIG1's top port at column 17. So the block can be
translated rigidly (+62 rows, +69 columns) with its internal plumbing intact,
and only that single connection re-drawn.

The re-route is long -- rows 59-61 are blocked at columns 46-69 by another
pipe, so the connection cannot cut straight across and has to climb the free
corridor at column 82, run west along row 1 and come back down column 17.
That should have cost ticks. It did not: straight runs are written with
segment glyphs ('|', '-') rather than arrowheads, so `alexey_squeeze` can
still see through them, and it then deleted 59 rows and 25 columns -- which
shortened not only this pipe but every other pipe crossing them. Net ticks
FELL 114,065 -> 88,146.

That is the lesson worth keeping: after moving anything, re-run the squeeze,
and draw straight pipe runs as segments so the squeeze is not blinded.
"""

import sys; sys.path.insert(0, 'src')
from littleman.sim import Machine
from littleman.judge import footprint
from littleman.alexey_squeeze import squeeze
src=open('submissions/plotter/plotter_03.man').read()
lines=src.rstrip('\n').split('\n'); W=max(len(l) for l in lines)
g=[list(l.ljust(W)) for l in lines]
H=len(g)
# widen the canvas a little for the new corridor
for row in g: row.extend(' '*4)
W+=4
DR,DC=62,69                       # block rows 0-58 cols 15-48  ->  rows 62-120 cols 84-117
block=[(r,c) for r in range(0,59) for c in range(0,W) if g[r][c]!=' ']
moved={}
for r,c in block:
    moved[(r+DR,c+DC)]=g[r][c]; g[r][c]=' '
for (r,c),ch in moved.items(): g[r][c]=ch
# the single crossing pipe E->BIG1 used to be (59,17),(60,17),(61,17); rebuild it
for r in (59,60,61):
    if g[r][17] in 'v|': g[r][17]=' '
def put(r,c,ch): g[r][c]=ch
# straight runs use segment glyphs '|' / '-' so the squeeze can still see
# through them; arrowheads only where the pipe turns or enters a room.
port=(59+DR, 17+DC)               # E's bottom port cell, now at (121,86)
put(port[0],port[1],'v')
put(port[0]+1,port[1],'<')
for c in range(port[1]-1,82,-1): put(port[0]+1,c,'-')
put(port[0]+1,82,'^')
for r in range(port[0],1,-1): put(r,82,'|')
put(1,82,'<')
for c in range(81,17,-1): put(1,c,'-')
put(1,17,'v')
for r in range(2,61): put(r,17,'|')
put(61,17,'v')
out='\n'.join(''.join(r).rstrip() for r in g)+'\n'
sq,nr,nc=squeeze(out)
sys.stderr.write(f'fp {footprint(out)} -> {footprint(sq)} after dropping {nr}r/{nc}c\n')
sys.stdout.write(sq)
