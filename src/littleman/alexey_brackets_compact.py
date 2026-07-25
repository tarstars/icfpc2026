"""brackets_01 -- brackets_00 repacked. Live 26/26, 7,473,269 -> 3,669,188 (2.04x).

Pure geometry: the three machine rooms are used VERBATIM, only trimmed of
provably empty edges, and then re-placed with shorter pipes.

  * classify  19x20 -> 19x18  (two empty right columns)
  * close     10x32 ->  9x30  (two empty columns, one empty interior row)
  * open      unchanged

brackets_00 put classify and open side by side, which forced ~46 columns,
and then wrapped a 92-cell pipe right around the perimeter. Stacking the
rooms instead (classify / close / open) makes the layout 37x42 = fp 1764
against 2500, and -- the part that was not expected -- cuts avgTicks from
1506 to 1080 locally, because the long pipes shrank from 92 and 45 cells to
89 and 59 with far less wandering. Footprint 29% better, ticks 28% better,
so the score halves.

Room ORDER is what makes it planar. Two pipes have to cross the layout:
close-bottom -> open-top and open-bottom -> close-top. With open in the
middle both wraps are long and they fight for the same corridor rows; with
close in the middle one wrap becomes a two-row hop and only one long pipe
remains, which then owns the east columns (35, 36) and the bottom row.

Ports are unchanged relative to each room, so nearest-pipe resolution
inside the rooms is untouched -- that is why the rooms need no edits. Trims
only ever remove cells beyond the last used column/row, so the walk is
identical apart from being a few ticks shorter.
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
cv.put(22,5,box(cl))                     # close rows 22-30 cols 5-34
cv.put(33,5,box(op))                     # open  rows 33-38 cols 5-26
cv.put(34,30,["+-+","|O|","+-+"])        # O     rows 34-36 cols 30-32
P=[([(4,3),(4,4),(1,4)],'>'),                                   # I -> classify LEFT r1
   ([(19,7),(20,7),(20,3),(24,3),(24,4)],'>'),                  # classify BOT -> close LEFT r2
   ([(10,23),(10,36),(41,36),(41,1),(35,1),(35,4)],'>'),        # classify RIGHT -> open LEFT r2
   ([(31,10),(32,10),(32,15)],'v'),                             # close BOT c5 -> open TOP c10
   ([(31,18),(32,18),(32,28),(35,28),(35,29)],'>'),             # close BOT c13 -> O
   ([(39,21),(40,21),(40,35),(21,35),(21,11)],'v')]             # open BOT -> close TOP c6
for pts,term in P:
    cv.pipe(pts); cv.cells[pts[-1]]=term
t=cv.render()
if __name__ == '__main__':
    sys.stdout.write(t)
