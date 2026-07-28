"""Assemble a folded pathfinder: fold room 0, anchor its BOTTOM wall where the
original was, and trim the rows that frees at the top.

Anchoring the bottom wall is what makes this cheap: every one of room 0's
eight pipes is a straight vertical run leaving that wall, so none of them
moves, changes length, or needs re-routing.
"""
import pathlib
from littleman import sim, pathfinder_fold as pf

SRC = 'submissions/pathfinder/pathfinder_03.man'


def load():
    t = pathlib.Path(SRC).read_text()
    lines = t.split('\n')
    while lines and not lines[-1].strip():
        lines.pop()
    W = max(len(l) for l in lines)
    return [l.ljust(W) for l in lines], W


def assemble(cut, margin):
    lines, W = load()
    m = sim.Machine.parse('\n'.join(lines) + '\n')
    r0 = m.rooms[0]
    interior = [lines[y][r0.left + 1:r0.right] for y in range(r0.top + 1, r0.bottom)]
    new, info = pf.fold_interior(interior, [cut], margin=margin)
    if info.get('failures'):
        return None, f"route failures: {len(info['failures'])}"
    nh = len(new)
    nw = max(len(l) for l in new)
    new = [l.ljust(nw) for l in new]
    top = r0.bottom - (nh + 1)
    if top < 0:
        return None, "folded room taller than the original"
    left, right = r0.left, r0.left + nw + 1
    newW = max(W, right + 1)
    grid = [list(l.ljust(newW)) for l in lines]
    for y in range(r0.top, r0.bottom + 1):
        for x in range(r0.left, r0.right + 1):
            grid[y][x] = ' '
    for x in range(left, right + 1):
        grid[top][x] = '-'
        grid[r0.bottom][x] = '-'
    for x in (left, right):
        grid[top][x] = '+'
        grid[r0.bottom][x] = '+'
    for i in range(nh):
        y = top + 1 + i
        grid[y][left] = '|'
        grid[y][right] = '|'
        for j, ch in enumerate(new[i]):
            grid[y][left + 1 + j] = ch
    out = [''.join(r).rstrip() for r in grid[top:]]
    return '\n'.join(out) + '\n', None
