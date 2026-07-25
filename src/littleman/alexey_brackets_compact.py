"""brackets_02 -- brackets_00 repacked. Live 26/26, 7,473,269 -> 3,494,864 (2.14x).

Pure geometry: the three machine rooms are used VERBATIM, trimmed only of
provably empty edges, then re-placed with much shorter pipes.

  * classify  19x20 -> 19x18  (two empty right columns)
  * close     10x32 ->  9x30  (two empty columns, one empty interior row)
  * open      unchanged
  * layout    50x39 (fp 2500) -> 37x41 (fp 1681)

Trims only remove cells beyond the last used column/row, so each walk is
identical apart from being a few ticks shorter, and every port keeps its
offset relative to its own room -- which is why nearest-pipe resolution
inside the rooms needed no re-derivation.

ROOM ORDER is what makes the routing planar. Two pipes must cross the whole
layout: close-bottom -> open-top and open-bottom -> close-top. With open in
the middle (as brackets_00 had it) both wraps are long and cannot be routed
past each other -- every attempt had one pipe's vertical run cutting the
other's horizontal. Putting CLOSE in the middle turns one wrap into a
two-row hop and leaves a single long pipe, which then owns the east columns
(35, 36) and the bottom row uncontested. brackets_00's 92-cell perimeter
wrap becomes 88 much straighter cells and its 45-cell one becomes 16, which
is why avgTicks fell 1506 -> 1079 as well.

Last row squeezed out by noticing that pipe 2 (classify -> close, columns
3-7) and pipe 6 (the long wrap, columns 11-35) run in disjoint column
ranges and can therefore SHARE gap row 20.

WHY THE ROOMS THEMSELVES CANNOT SHRINK FURTHER (measured, not assumed).
Interiors are 75%/67%/75% visited and no fully dead row or column remains.
The remaining space is the five comparison blocks in `classify`, which each
occupy two rows -- one for the block, one for the mismatch return. They
cannot be serpentined into one row each, because `X` always sends the MATCH
case straight ahead: a westbound block's match arm would run west, while its
`s` must reach the OPEN port on the east wall, and at low columns that cell
resolves to the CLOSE port instead. Routing the arm around to a shared send
cell does work geometrically but roughly doubles the per-character walk
(~39 ticks becomes ~75), so it loses more on ticks than it gains on
footprint. The present arm layout -- send to OPEN immediately after X, then
drop down the east lane -- is tick-optimal, and that is what pins the room
at one block per two rows.
"""

import sys; sys.path.insert(0, 'src')
from littleman.canvas import Canvas
from littleman.sim import Machine
from littleman.judge import footprint
src=open('submissions/brackets/brackets_00.man').read().rstrip('\n').split('\n')
W=max(len(l) for l in src); g=[l.ljust(W) for l in src]
def inner(r0,r1,c0,c1): return [g[r][c0+1:c1] for r in range(r0+1,r1)]
classify=[row[:16] for row in inner(3,21,4,23)]
op=inner(2,7,26,47)
cl=inner(25,34,8,39); cl=[row[:27]+row[29:] for row in cl]; cl=cl[:6]+cl[7:]
def box(i):
    w=len(i[0]); return ['+'+'-'*w+'+']+['|'+r+'|' for r in i]+['+'+'-'*w+'+']
cv=Canvas()
cv.put(3,0,["+-+","|I|","+-+"])          # I     rows 3-5   cols 0-2
cv.put(0,5,box(classify))                # class rows 0-18  cols 5-22
cv.put(21,5,box(cl))                     # close rows 21-29 cols 5-34
cv.put(32,5,box(op))                     # open  rows 32-37 cols 5-26
cv.put(33,30,["+-+","|O|","+-+"])        # O     rows 33-35 cols 30-32
P=[([(4,3),(4,4),(1,4)],'>'),                                   # I -> classify LEFT r1
   ([(19,7),(20,7),(20,3),(23,3),(23,4)],'>'),                  # classify BOT -> close LEFT r2
   ([(10,23),(10,36),(40,36),(40,1),(34,1),(34,4)],'>'),        # classify RIGHT -> open LEFT r2
   ([(30,10),(31,10),(31,15)],'v'),                             # close BOT c5 -> open TOP c10
   ([(30,18),(31,18),(31,28),(34,28),(34,29)],'>'),             # close BOT c13 -> O
   ([(38,21),(39,21),(39,35),(20,35),(20,11)],'v')]             # open BOT -> close TOP c6 (shares row 20 with pipe 2)
for pts,term in P:
    cv.pipe(pts); cv.cells[pts[-1]]=term
t=cv.render()
if __name__ == '__main__':
    sys.stdout.write(t)
