"""Hello World: emit 11 fixed bytes and halt.

There is no input, so the whole program is a straight walk over constants.
The naive form spends a 5-cell literal on every value (`` `104` `` + `s`,
67 cells).  Instead the running value lives in B and each step adds a
DELTA:

    `104` M s          A = 104, B = 104, emit
    <d> [N] + M s      A = d (negated when the delta is down),
                       A += B, B = A, emit

Deltas between consecutive bytes of "hello world" are single digits in
8 of 10 cases, and a bare digit is one cell against five for a literal,
so this costs 56 cells.  Two consecutive `l`s cost a single `s`, since
`M` leaves A untouched.

Score is max(width,height)^2 x ticks, so the serpentine width is swept
for the smallest bounding box rather than fixed by hand.
"""

from .canvas import Canvas

TEXT = "hello world"


def _lit(n: int) -> str:
    """A numeric literal: bare digit if it fits, else backtick-quoted."""
    return str(n) if 0 <= n <= 9 else "`%d`" % n


def tokens() -> list[str]:
    """Instruction tokens in the order the little man walks over them.

    Each token occupies consecutive cells and is never split across a row.
    """
    out = [_lit(ord(TEXT[0])), "M", "s"]
    for prev, cur in zip(TEXT, TEXT[1:]):
        delta = ord(cur) - ord(prev)
        if delta == 0:
            out.append("s")          # B already holds it; A is untouched
            continue
        step = [_lit(abs(delta))]
        if delta < 0:
            step.append("N")         # A = -|d|, so the add walks downward
        out += step + ["+", "M", "s"]
    # nothing reads B after the final emit, so its `M` is dead weight
    out.pop(len(out) - 1 - out[::-1].index("M"))
    out.append("H")
    return out


def build_room(width: int) -> list[str]:
    """Lay the token stream as a serpentine inside a width x rows room.

    Row 1 starts at `@` (the man spawns facing east); every later row is
    entered by a turn cell and reverses direction.  Returns the room
    including its walls.
    """
    toks = tokens()
    rows: list[list[tuple[int, str]]] = []
    idx = 0
    while idx < len(toks):
        east = len(rows) % 2 == 0
        # payload columns in the order the man treads them
        slots = list(range(2, width)) if east else list(range(width - 1, 1, -1))
        placed: list[tuple[int, str]] = []
        at = 0
        while idx < len(toks) and at < len(slots):
            tok = toks[idx]
            if len(tok) > len(slots) - at:
                break                # keep the token whole; pad the row out
            for off, ch in enumerate(tok):
                placed.append((slots[at + off], ch))
            at += len(tok)
            idx += 1
        if not placed:               # no token fits: the row would not advance
            raise ValueError(
                "width %d is too narrow for token %r" % (width, toks[idx]))
        rows.append(placed)
    return _render_room(rows, width)


def _render_room(rows: list[list[tuple[int, str]]], width: int) -> list[str]:
    height = len(rows)
    grid = [[" "] * (width + 2) for _ in range(height + 2)]
    for c in range(width + 2):
        grid[0][c] = grid[height + 1][c] = "-"
    for r in range(height + 2):
        grid[r][0] = grid[r][width + 1] = "|"
    for r, c in ((0, 0), (0, width + 1), (height + 1, 0), (height + 1, width + 1)):
        grid[r][c] = "+"
    for i, placed in enumerate(rows):
        r = i + 1
        east = i % 2 == 0
        if i == 0:
            grid[r][1] = "@"
        else:
            grid[r][1 if east else width] = ">" if east else "<"
        for c, ch in placed:
            grid[r][c] = ch
        if i + 1 < len(rows):        # turn cell into the next row
            grid[r][width if east else 1] = "v"
    return ["".join(row) for row in grid]


def build_with_width(width: int) -> str:
    """Room plus the single outgoing pipe down to the O port."""
    room = build_room(width)
    height = len(room)
    cv = Canvas()
    cv.put(0, 0, room)
    cv.put(height + 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(height, 4), (height + 2, 4), (height + 2, 3)])
    return cv.render()


def build_hello_world() -> str:
    """Sweep the serpentine width for the smallest bounding box."""
    best = None
    for width in range(7, 25):       # 7 is the narrowest row a 5-cell literal fits
        text = build_with_width(width)
        lines = [x for x in text.split("\n") if x]
        dim = max(len(lines), max(len(x) for x in lines))
        if best is None or dim < best[0]:
            best = (dim, width, text)
    return best[2]
