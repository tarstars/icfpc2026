"""brackets_03: same three rooms as brackets_02, faster state ring.

brackets_02 costs ~102 ticks per input character.  The critical cycle is
not the little men, it is the STATE ring: OPEN sends [S,p] to CLOSE over a
58-cell pipe and CLOSE sends it back over a 7-cell one, so ~65 of those 102
ticks are a value crawling through pipe cells.

The rooms are reused verbatim (they are already 67-75% dense); only the
placement and the pipe routes change, so every `s`/`r` keeps resolving to
the same pipe.
"""

from pathlib import Path

from .canvas import Canvas

_SRC = Path(__file__).resolve().parents[2] / "submissions" / "brackets"


def _rooms():
    """classify / close / open interiors, trimmed exactly as brackets_02."""
    src = (_SRC / "brackets_00.man").read_text().rstrip("\n").split("\n")
    w = max(len(line) for line in src)
    g = [line.ljust(w) for line in src]

    def inner(r0, r1, c0, c1):
        return [g[r][c0 + 1 : c1] for r in range(r0 + 1, r1)]

    classify = [row[:16] for row in inner(3, 21, 4, 23)]
    op = inner(2, 7, 26, 47)
    cl = inner(25, 34, 8, 39)
    cl = [row[:27] + row[29:] for row in cl]
    # rows 7+ and column 28 of CLOSE only carried the old relay turn-around,
    # which CLOSE_PATCH reroutes through row 5, so they can go.
    cl = [row[:27] for row in cl[:6]]
    return classify, _patch(cl, CLOSE_PATCH), _patch(op, OPEN_PATCH)


# Both stations walked to the far east wall and back along the bottom row
# before starting the next character.  The relay arms turn around early
# instead, through columns that the other arms leave empty.
CLOSE_PATCH = {(2, 9): "v", (5, 9): "<", (5, 1): "^", (6, 1): "^", (6, 2): "<"}
# OPEN also folds the push arm back along row 4 instead of running out to
# column 19 and walking the whole width home; the relay returns along row 1.
OPEN_PATCH = {
    (2, 11): "^", (1, 11): "<", (4, 4): "^",
    (3, 14): "v", (3, 15): " ", (3, 16): " ", (3, 17): " ", (3, 18): " ",
    (3, 19): " ", (2, 20): " ",
    (4, 14): "<", (4, 13): "r", (4, 12): "M", (4, 11): "1", (4, 10): "+",
    (4, 9): "s",
}
# cells the reroutes deliberately replace (old turn-arounds, now dead)
OVERWRITE = {(6, 2), (3, 14), (3, 15), (3, 16), (3, 17), (3, 18), (3, 19), (2, 20)}


def _patch(interior, cells):
    rows = [list(r) for r in interior]
    for (r, c), ch in cells.items():
        assert rows[r - 1][c - 1] == " " or (r, c) in OVERWRITE, (r, c)
        rows[r - 1][c - 1] = ch
    return ["".join(r) for r in rows]


def build_classify_fast() -> list:
    """Constant-time classifier: 14x9 interior, ~24-33 ticks per character.

    t = c >> 5 is 1/2/3 for ()/[]/{}.  opener/closer comes from the low two
    bits held in the backpack, which `b ] x` test without touching A, so the
    token t survives the branch.  End of input is `q` (pipe is empty), which
    frees the backpack from counting.  Ports: CLOSE-out LEFT row4,
    OPEN-out RIGHT row4, input BOTTOM.
    """
    cells = {
        # epilogue: send 0 to OPEN, 4 to CLOSE, halt
        (1, 12): "<", (1, 10): "s", (1, 5): "4", (1, 4): "s", (1, 1): "H",
        # '(' arm (bit0 == 0): t -> OPEN, 0 -> CLOSE
        (2, 11): "<", (2, 10): "s", (2, 7): "0", (2, 4): "s", (2, 1): "v",
        # loop head; `d` goes straight into the epilogue when the pipe is dry
        (3, 1): ">", (3, 2): "q", (3, 3): "d", (3, 4): "0", (3, 12): "^",
        # body: read c, stash bits, A = c >> 5 = t, branch on bit0
        (4, 3): ">", (4, 4): "r", (4, 5): "b", (4, 6): "M", (4, 7): "5",
        (4, 8): "W", (4, 9): "}", (4, 11): "x",
        (5, 11): "]",
        # bit1 == 1 -> '[' '{' opener arm (west); bit1 == 0 -> closer (east)
        (6, 11): "x", (6, 10): "s", (6, 7): "0", (6, 4): "s", (6, 1): "^",
        (6, 12): "M", (6, 13): "0", (6, 14): "v",
        # closer arm: 0 -> OPEN, t -> CLOSE
        (7, 14): "<", (7, 10): "s", (7, 9): "W", (7, 4): "s", (7, 1): "^",
        # prologue: swallow n, then loop in from the west lane
        (8, 1): "@", (8, 2): "r", (8, 3): "v",
        (9, 3): "<", (9, 1): "^",
    }
    return _room(14, 9, cells)


def build_close_fast() -> list:
    """CLOSE interior with the closer detour folded: 50 -> 38 ticks/lap.

    Same 27x6 box, ports and relay arm as brackets_03; only the act paths
    moved.  Closer: X(cmd) drops to row3 (B=t, A=t-4), X rises to row2
    (restore t, read S), X drops into the row4 westward work row:
    (S-t) divmod 3 via floored '/', X on the remainder; a match sends S'
    and p+1 to the state ring and climbs home at col1.  Mismatch rises at
    col10 to the row1 arm (p+1 -> O, halt).  End (t=4) runs east on row3:
    balanced sends 0; unclosed drops to the row5 arm.  Empty stack
    continues east on row2.  Cells (3,9),(4,9),(4,1) are shared with the
    relay descent/climb and are side-effect-free for it (A, B dead).
    """
    cells = {
        # mismatch arm: p+1 -> O, halt
        (1, 10): ">", (1, 11): "r", (1, 12): "M", (1, 13): "1", (1, 14): "+",
        (1, 16): "s", (1, 17): "H",
        # relay arm (byte-identical to brackets_03)
        (2, 1): ">", (2, 2): "@", (2, 3): "r", (2, 4): "X", (2, 5): "r",
        (2, 6): "s", (2, 7): "r", (2, 8): "s", (2, 9): "v",
        # closer: restore t, read S; straight-on = empty stack (p+1 -> O)
        (2, 13): ">", (2, 14): "+", (2, 15): "M", (2, 16): "r", (2, 17): "X",
        (2, 18): "r", (2, 19): "M", (2, 20): "1", (2, 21): "+", (2, 22): "s",
        (2, 23): "H",
        # act entry: B=t, A=t-4; closers turn up, end (t=4) goes straight
        (3, 4): ">", (3, 9): "M", (3, 10): "4", (3, 11): "W", (3, 12): "-",
        (3, 13): "X", (3, 14): "r", (3, 15): "X", (3, 18): "s", (3, 19): "H",
        # match work row (westward): pop, verify, resend state, go home
        (4, 1): "^", (4, 3): "s", (4, 4): "+", (4, 5): "1", (4, 6): "M",
        (4, 7): "r", (4, 8): "s", (4, 9): "W", (4, 10): "X", (4, 11): "W",
        (4, 12): "/", (4, 13): "W", (4, 14): "3", (4, 15): "M", (4, 16): "-",
        (4, 17): "<",
        # relay return (unchanged) + end-unclosed arm (p+1 -> O)
        (5, 1): "^", (5, 9): "<", (5, 15): ">", (5, 16): "r", (5, 17): "M",
        (5, 18): "1", (5, 19): "+", (5, 20): "s", (5, 21): "H",
    }
    return _room(27, 6, cells)


def _room(w, h, cells):
    grid = [[" "] * (w + 2) for _ in range(h + 2)]
    for c in range(w + 2):
        grid[0][c] = grid[h + 1][c] = "-"
    for r in range(h + 2):
        grid[r][0] = grid[r][w + 1] = "|"
    for r, c in ((0, 0), (0, w + 1), (h + 1, 0), (h + 1, w + 1)):
        grid[r][c] = "+"
    for (r, c), ch in cells.items():
        grid[r][c] = ch
    return ["".join(row) for row in grid]


def _box(interior):
    w = len(interior[0])
    return ["+" + "-" * w + "+"] + ["|" + r + "|" for r in interior] + ["+" + "-" * w + "+"]


PIPES_02 = [
    ([(4, 3), (4, 4), (1, 4)], ">"),
    ([(19, 7), (20, 7), (20, 3), (23, 3), (23, 4)], ">"),
    ([(10, 23), (10, 36), (40, 36), (40, 1), (34, 1), (34, 4)], ">"),
    ([(30, 10), (31, 10), (31, 15)], "v"),
    ([(30, 18), (31, 18), (31, 28), (34, 28), (34, 29)], ">"),
    ([(38, 21), (39, 21), (39, 35), (20, 35), (20, 11)], "v"),
]

ROOMS_02 = [(3, 0, "I"), (0, 5, "classify"), (21, 5, "close"), (32, 5, "open"), (33, 30, "O")]


# brackets_03: OPEN sits directly above CLOSE so the state ring is 4 cells.
# Port moves (interiors untouched, only where pipes touch the walls):
#   close state-out  bottom col5 -> top col4 ; close output bottom col13 -> top col25
#   open  state-in   top col10   -> bottom col8 ; open state-out -> bottom col10
#   classify cmd-out bottom col2 -> left row17
ROOMS_03 = [(24, 25, "I"), (20, 5, "classify"), (10, 5, "close"), (2, 1, "open"), (5, 29, "O")]

PIPES_03 = [
    ([(25, 24), (25, 23)], "<"),                    # I -> classify RIGHT
    ([(37, 4), (37, 3), (12, 3), (12, 4)], ">"),    # classify LEFT r17 -> close cmd LEFT r2
    ([(30, 23), (30, 36), (0, 36), (0, 0), (4, 0)], ">"),  # classify RIGHT r10 -> open cmd
    ([(9, 9), (8, 9)], "^"),                        # close TOP c4 -> open BOTTOM c8 (state)
    ([(8, 11), (9, 11)], "v"),                      # open BOTTOM c10 -> close TOP c6 (state)
    ([(9, 30), (8, 30)], "^"),                      # close TOP c25 -> O
]


def build(rooms=None, pipes=None) -> str:
    classify, cl, op = _rooms()
    art = {"I": ["+-+", "|I|", "+-+"], "O": ["+-+", "|O|", "+-+"],
           "classify": _box(classify), "close": _box(cl), "open": _box(op),
           "fastclassify": build_classify_fast(),
           "fastclose": build_close_fast()}
    cv = Canvas()
    for r, c, name in rooms or ROOMS_02:
        cv.put(r, c, art[name])
    for pts, term in pipes or PIPES_02:
        cv.pipe(pts)
        cv.cells[pts[-1]] = term
    return cv.render()


# brackets_04: brackets_03 with the arithmetic classifier.
ROOMS_04 = [(25, 23, "I"), (19, 5, "fastclassify"), (10, 5, "close"),
            (2, 1, "open"), (5, 29, "O")]

PIPES_04 = [
    ([(26, 22), (26, 21)], "<"),                          # I -> classify RIGHT r7
    ([(23, 4), (23, 3), (12, 3), (12, 4)], ">"),          # classify LEFT r4 -> close cmd
    ([(23, 21), (23, 35), (0, 35), (0, 5), (1, 5)], "v"),  # classify RIGHT r4 -> open cmd TOP
    ([(9, 9), (8, 9)], "^"),                              # close TOP c4 -> open BOTTOM c8
    ([(8, 11), (9, 11)], "v"),                            # open BOTTOM c10 -> close TOP c6
    ([(9, 30), (8, 30)], "^"),                            # close TOP c25 -> O
]


# brackets_05 art set: brackets_04 layout with the folded CLOSE room.
ROOMS_05 = [(25, 23, "I"), (19, 5, "fastclassify"), (10, 5, "fastclose"),
            (2, 1, "open"), (5, 29, "O")]


if __name__ == "__main__":
    print(build(ROOMS_05, PIPES_04), end="")
