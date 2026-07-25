"""Collapse the two-rows-per-instruction staircase that plotter's big rooms use.

`plotter`'s three tall rooms spend **two rows on every instruction**:

    row A:   .....v(p) ................. <(q)     west leg, carries nothing
    row B:   .....>(p) INSTR ........... v(q)     east leg, ONE instruction

The man falls into the west leg at column `q`, walks west to `p`, drops into
the east leg, walks east executing whatever is there, and drops out at `q`
again. Fifteen instructions, thirty rows.

Two consecutive east legs can share one row whenever their instruction
columns increase across the join -- the west leg between them was only ever
a carriage return. Merging them deletes both the west leg and the second
east leg.

**Columns must not move.** These rooms decide which pipe an `r` or `s` talks
to by column: every inbound pipe lands on the room's top wall and every
outbound one leaves through the bottom, so the row term of the Manhattan
distance cancels and the zone is column-only. Rows are therefore free and
columns are frozen -- which is exactly what makes this fold legal. Check that
precondition on any room before folding it:

    all(p.cells[-1][0] == room.top - 1 for p in inbound)
    all(p.cells[0][0]  == room.bottom + 1 for p in outbound)

**Vertical fall-throughs survive.** Branches in these rooms are compiled as
long empty columns -- the man turns down and falls many rows to the next
glyph in that column. Deleting whole leg pairs preserves them, because the
deleted rows are blank at every column a fall uses. The merge refuses any
pair that would break this.

The room keeps its outer size; freed rows pile up blank at the bottom of the
interior. Pulling the bottom wall up over them, and moving what is below the
room up to match, is a separate step -- see `alexey_piperoute`.
"""

from .sim import Machine


class FoldError(Exception):
    pass


def room_rows(grid, room):
    """Interior rows as lists of (col, char), top to bottom."""
    return [[(x, grid[y][x]) for x in range(room.left + 1, room.right)
             if grid[y][x] != " "]
            for y in range(room.top + 1, room.bottom)]


def classify(cells):
    """'west' for a bare carriage return, 'east' for a leg that does work."""
    if len(cells) == 2 and cells[0][1] == "v" and cells[1][1] == "<":
        return "west"
    if len(cells) >= 2 and cells[0][1] == ">" and cells[-1][1] == "v":
        return "east"
    return None


def _instrs(cells):
    return [(x, ch) for x, ch in cells[1:-1]]


def merge_once(rows):
    """Merge the first mergeable (east, west, east) triple. None if none."""
    for i in range(len(rows) - 2):
        b1, a2, b2 = rows[i], rows[i + 1], rows[i + 2]
        if classify(b1) != "east" or classify(a2) != "west" or classify(b2) != "east":
            continue
        exit1 = b1[-1][0]
        if a2[1][0] != exit1:          # the west leg must catch b1's drop
            continue
        if a2[0][0] != b2[0][0]:       # ...and hand over at b2's entry column
            continue
        i1, i2 = _instrs(b1), _instrs(b2)
        if not i2:
            continue
        if i1 and max(x for x, _ in i1) >= min(x for x, _ in i2):
            continue                   # columns would not increase across the join
        exit2 = b2[-1][0]
        if i2 and max(x for x, _ in i2) >= exit2:
            continue
        merged = [b1[0]] + i1 + i2 + [(exit2, "v")]
        cols = [x for x, _ in merged]
        if len(set(cols)) != len(cols) or cols != sorted(cols):
            continue
        return rows[:i] + [merged] + rows[i + 3:]
    return None


def fold_room(text: str, room_index: int):
    """Collapse one room's staircase. Returns (new_text, rows_freed)."""
    lines = text.rstrip("\n").split("\n")
    width = max(len(line) for line in lines)
    grid = [list(line.ljust(width)) for line in lines]
    machine = Machine.parse(text)
    room = machine.rooms[room_index]

    rows = room_rows(grid, room)
    original = len(rows)
    while True:
        nxt = merge_once(rows)
        if nxt is None:
            break
        rows = nxt
    freed = original - len(rows)

    for y in range(room.top + 1, room.bottom):
        for x in range(room.left + 1, room.right):
            grid[y][x] = " "
    for k, cells in enumerate(rows):
        y = room.top + 1 + k
        for x, ch in cells:
            grid[y][x] = ch
    return "\n".join("".join(r).rstrip() for r in grid) + "\n", freed


def ports_are_single_walled(machine, room):
    """True when the room's pipes all land on the top wall and leave through
    the bottom (or vice versa) -- the precondition that frees the rows."""
    inbound = [p for p in machine.pipes if p.dest is room]
    outbound = [p for p in machine.pipes if p.source is room]
    if not inbound or not outbound:
        return False
    return (all(p.cells[-1][0] in (room.top - 1, room.bottom + 1) for p in inbound)
            and all(p.cells[0][0] in (room.top - 1, room.bottom + 1) for p in outbound)
            and len({p.cells[-1][0] for p in inbound}) == 1
            and len({p.cells[0][0] for p in outbound}) == 1)
