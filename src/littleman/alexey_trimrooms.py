"""Shrink every room to its content: drop empty edge rows and columns.

Complements `alexey_squeeze`, which can only delete a line that is blank
across the WHOLE program. This one works per room: it moves each wall inward
past the room's own empty edge rows/columns and extends any pipe that was
attached to the wall so it reaches the new one. The LM-75 display is skipped
-- its blank interior is the drawing surface, not waste.

ON ITS OWN IT CHANGES NOTHING. Measured on plotter: seven rooms shrank (five
lost 8 empty left columns each, one lost 62, one lost 2 bottom rows -- 104
edge lines in all), and the footprint stayed at 148,225 because a narrower
room still sits inside the same bounding box. Submitted as plotter_03: live
20/20 at 16,907,343,915 against plotter_02's 16,905,772,730, i.e. 0.01%
WORSE -- the pipe extensions cost 7 ticks. plotter_02 remains the best.

Its value is as a first step. Freeing a room's edges opens space that rooms
can then be MOVED into, and on plotter it opens a lot: after the trim, the
band of rows 62-322 (occupied by the three big rooms, which end at column 80)
has columns 81-137 completely free -- 57 wide by 261 tall. The six trimmed
rooms are now at most 34 wide and total 52 rows. Moving them into that band
would free rows 5-58 and 330-339 and take the height from 385 to about 320:
footprint 148,225 -> ~102,400, about 1.45x. That step needs roughly twelve
pipes re-routed, so it is a separate piece of work.
"""

import sys; sys.path.insert(0, 'src')
from littleman.sim import Machine
from littleman.judge import footprint

def lead(seq):
    n=0
    for x in seq:
        if x: n+=1
        else: break
    return n

def trim_rooms(text):
    lines=text.rstrip('\n').split('\n'); W=max(len(l) for l in lines)
    g=[list(l.ljust(W)) for l in lines]
    m=Machine.parse(text)
    plan=[]
    for rm in m.rooms:
        h=rm.bottom-rm.top-1; w=rm.right-rm.left-1
        if h<1 or w<1: continue
        if '=' in ''.join(g[rm.top][rm.left:rm.right+1]): continue     # LM-75 display: blank interior is the canvas
        inner=[''.join(g[r][rm.left+1:rm.right]) for r in range(rm.top+1,rm.bottom)]
        er=[not row.strip() for row in inner]
        ec=[all(row[j]==' ' for row in inner) for j in range(w)]
        T,B,L,R=lead(er),lead(er[::-1]),lead(ec),lead(ec[::-1])
        if T or B or L or R: plan.append((rm,T,B,L,R))
    # pipe endpoints, so we can extend the ones whose wall moves
    ends=[]
    for p in m.pipes:
        ends.append((p.cells[-1], p.cells[-2] if len(p.cells)>1 else None, 'in'))
        ends.append((p.cells[0],  p.cells[1]  if len(p.cells)>1 else None, 'out'))
    for rm,T,B,L,R in plan:
        t2,b2,l2,r2 = rm.top+T, rm.bottom-B, rm.left+L, rm.right-R
        for r in range(rm.top,rm.bottom+1):                            # erase old border
            for c in (rm.left,rm.right):
                if g[r][c] in '+|-': g[r][c]=' '
        for c in range(rm.left,rm.right+1):
            for r in (rm.top,rm.bottom):
                if g[r][c] in '+|-': g[r][c]=' '
        for r in range(t2,b2+1):                                       # draw new border
            g[r][l2]='|'; g[r][r2]='|'
        for c in range(l2,r2+1):
            g[t2][c]='-'; g[b2][c]='-'
        for c,r in ((l2,t2),(r2,t2),(l2,b2),(r2,b2)): g[r][c]='+'
        for (cell,nxt,kind) in ends:                                   # extend pipes to the new wall
            y,x=cell
            if L and x==rm.left-1 and rm.top<y<rm.bottom:
                for cc in range(rm.left,l2): g[y][cc]= '>' if kind=='in' else '<'
            if R and x==rm.right+1 and rm.top<y<rm.bottom:
                for cc in range(r2+1,rm.right+1): g[y][cc]= '<' if kind=='in' else '>'
            if T and y==rm.top-1 and rm.left<x<rm.right:
                for rr in range(rm.top,t2): g[rr][x]= 'v' if kind=='in' else '^'
            if B and y==rm.bottom+1 and rm.left<x<rm.right:
                for rr in range(b2+1,rm.bottom+1): g[rr][x]= '^' if kind=='in' else 'v'
    return '\n'.join(''.join(r).rstrip() for r in g)+'\n', len(plan)

if __name__=='__main__':
    src='submissions/plotter/plotter_02.man'
    t=open(src).read()
    out,n=trim_rooms(t)
    sys.stderr.write(f'rooms trimmed: {n}  fp {footprint(t)} -> {footprint(out)}\n')
    sys.stdout.write(out)

