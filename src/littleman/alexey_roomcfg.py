"""Extract a room's control-flow graph by walking it the way the man does.

A room is not a list of rows, it is a program. Reading it row by row tells
you nothing; walking it from `@` tells you everything -- but a single walk
only follows one arm of each branch, which is how a fold quietly loses half
a room (that is exactly how block 1 of `memory` was nearly mangled).

This traces *every* arm. A state is `(row, col, direction)`; branches fork
it. The result is the set of reachable states, the instruction executed at
each, and the successor map -- enough to re-lay the room somewhere else and
check that the new layout runs the same program.

Branch semantics (all turn relative to the direction of travel):

    d   backpack > 0        -> clockwise, else straight
    x   backpack even/odd   -> clockwise, else straight
    X   sign(A)             -> +1 clockwise, -1 counter, 0 straight
    a   sign(A)             -> as X but tests the accumulator differently

`X` and `a` are three-way, `d` and `x` two-way. Every one of them is
*handed*, which is why a room containing any of them may never be mirrored.
"""

DIRS = {">": (0, 1), "<": (0, -1), "v": (1, 0), "^": (-1, 0)}
CW = {(0, 1): (1, 0), (1, 0): (0, -1), (0, -1): (-1, 0), (-1, 0): (0, 1)}
CCW = {v: k for k, v in CW.items()}
TWO_WAY = set("dx")
THREE_WAY = set("Xa")
BRANCHES = TWO_WAY | THREE_WAY


class Cfg:
    def __init__(self, states, instr, succ, start):
        self.states = states      # set of (row, col, dir)
        self.instr = instr        # (row, col) -> character executed there
        self.succ = succ          # state -> list of successor states
        self.start = start

    @property
    def cells(self):
        return set(self.instr)

    def branch_cells(self):
        return {c for c, ch in self.instr.items() if ch in BRANCHES}

    def linear(self):
        """True when no state has more than one successor."""
        return all(len(v) <= 1 for v in self.succ.values())


def trace(grid, room, start=None, limit=100000):
    """Walk every arm. `grid` is a list of equal-length strings."""
    if start is None:
        found = [(y, x)
                 for y in range(room.top + 1, room.bottom)
                 for x in range(room.left + 1, room.right)
                 if grid[y][x] == "@"]
        if not found:
            raise ValueError("room has no man")
        start = (found[0][0], found[0][1], (0, 1))

    states, instr, succ = set(), {}, {}
    stack = [start]
    while stack and len(states) < limit:
        st = stack.pop()
        if st in states:
            continue
        states.add(st)
        y, x, d = st
        ny, nx = y + d[0], x + d[1]
        if not (room.top < ny < room.bottom and room.left < nx < room.right):
            succ[st] = []                       # walks into a wall: halt here
            continue
        ch = grid[ny][nx]
        outs = []
        if ch in DIRS:
            outs = [(ny, nx, DIRS[ch])]
        elif ch in TWO_WAY:
            instr[(ny, nx)] = ch
            outs = [(ny, nx, d), (ny, nx, CW[d])]
        elif ch in THREE_WAY:
            instr[(ny, nx)] = ch
            outs = [(ny, nx, d), (ny, nx, CW[d]), (ny, nx, CCW[d])]
        else:
            if ch not in " @":
                instr[(ny, nx)] = ch
            outs = [(ny, nx, d)]
        succ[st] = outs
        stack.extend(outs)
    return Cfg(states, instr, succ, start)


def summary(grid, room):
    cfg = trace(grid, room)
    body = [ch for ch in cfg.instr.values()]
    return {
        "instructions": len(cfg.instr),
        "branches": sorted(cfg.branch_cells()),
        "branch_kinds": sorted({cfg.instr[c] for c in cfg.branch_cells()}),
        "linear": cfg.linear(),
        "distinct_chars": sorted(set(body)),
    }
