"""Brackets: packed-stack machine over three rooms.

State: S = bracket stack packed base-3 with digits {1,2,3} (top at the
least significant end), p = count of processed chars. S fits 64 bits for
depth 32 (3^32 ~ 1.9e15). [S, p] circulates OPEN <-> CLOSE; the station
addressed by the current char transforms it, the other relays it.
OPEN's prologue seeds [0, 0]; the relay protocol self-heals whichever
station needs the state first.

CLASSIFY resolves each char c with a subtract chain (c-40, -1, -50, -2,
-30 == 0 -> ( ) [ ] {, else }) and sends one token to each station:
  '(' (1,0)  '[' (2,0)  '{' (3,0)  ')' (0,1)  ']' (0,2)  '}' (0,3)
  end of string (0,4), then CLASSIFY halts.
Station token 0 relays [S,p]. OPEN token t: S -> 3S+t (M r W + + +),
p -> p+1. CLOSE token u: S==0 -> emit p+1, halt; else (S-u)/3 in one
division: remainder != 0 -> emit p+1 (wrong closer), halt; quotient is
the popped stack. CLOSE token 4 (finish): emit 0 if S==0 else p+1, halt.
"""

from .canvas import Canvas


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


def build_classify() -> list:
    """In: input (LEFT row1). Out: to-OPEN (RIGHT row10), to-CLOSE (BOTTOM col2)."""
    cells = {
        (1, 1): ">", (1, 2): "@", (1, 3): "r", (1, 4): "b", (1, 5): "v",
        (1, 7): "<", (1, 13): "<",
        (2, 1): ">", (2, 5): ">", (2, 6): "d",
        (2, 7): "0", (2, 8): "s", (2, 9): "`", (2, 10): "4", (2, 11): "`",
        (2, 14): "v",
        (3, 6): "m",
        (4, 6): "r",
        (5, 6): "<", (5, 2): "v",
        # L0: c-40 == 0 -> '('
        (6, 2): ">", (6, 3): "M", (6, 4): "`", (6, 5): "4", (6, 6): "0",
        (6, 7): "`", (6, 8): "W", (6, 9): "-", (6, 10): "X",
        (6, 11): "1", (6, 12): "s", (6, 13): "0", (6, 14): "v",
        (7, 10): "<", (7, 2): "v",
        # L1: -1 -> ')'
        (8, 2): ">", (8, 3): "M", (8, 4): "1", (8, 6): "W", (8, 8): "-",
        (8, 10): "X",
        (8, 11): "0", (8, 12): "s", (8, 13): "1", (8, 14): "v",
        (9, 10): "<", (9, 2): "v",
        # L2: -50 -> '['
        (10, 2): ">", (10, 3): "M", (10, 4): "`", (10, 5): "5", (10, 6): "0",
        (10, 7): "`", (10, 8): "W", (10, 9): "-", (10, 10): "X",
        (10, 11): "2", (10, 12): "s", (10, 13): "0", (10, 14): "v",
        (11, 10): "<", (11, 2): "v",
        # L3: -2 -> ']'
        (12, 2): ">", (12, 3): "M", (12, 4): "2", (12, 6): "W", (12, 8): "-",
        (12, 10): "X",
        (12, 11): "0", (12, 12): "s", (12, 13): "2", (12, 14): "v",
        (13, 10): "<", (13, 2): "v",
        # L4: -30 -> '{'; fall-through '}'
        (14, 2): ">", (14, 3): "M", (14, 4): "`", (14, 5): "3", (14, 6): "0",
        (14, 7): "`", (14, 8): "W", (14, 9): "-", (14, 10): "X",
        (14, 11): "3", (14, 12): "s", (14, 13): "0", (14, 14): "v",
        # '}': 3 to CLOSE (low-left), 0 to OPEN (mid-right), climb col16 home
        (15, 10): "<", (15, 9): "3", (15, 8): "s", (15, 7): "0", (15, 6): "v",
        (16, 6): ">", (16, 15): "s", (16, 16): "^", (1, 16): "<",
        # common tail: closer-token in A to CLOSE, climb home col1
        (17, 14): "<", (17, 4): "s", (17, 1): "^",
    }
    return _room(18, 17, cells)


def build_open() -> list:
    """In: cmd (LEFT row1), state (TOP col10). Out: state (single).
    Prologue seeds the state loop with [S=0, p=0]."""
    cells = {
        # prologue (walked once): seed state loop with [S=0, p=0]
        (1, 1): "@", (1, 2): "s", (1, 3): "s", (1, 4): "v",
        # loop top: dispatch; token 0 relays S, p
        (2, 1): ">", (2, 4): ">", (2, 5): "r", (2, 6): "X",
        (2, 7): "r", (2, 8): "s", (2, 9): "r", (2, 10): "s", (2, 20): "v",
        # token t: S -> 3S+t, p -> p+1
        (3, 6): ">", (3, 7): "M", (3, 8): "r", (3, 9): "W", (3, 10): "+",
        (3, 11): "+", (3, 12): "+", (3, 13): "s", (3, 14): "r", (3, 15): "M",
        (3, 16): "1", (3, 17): "+", (3, 18): "s", (3, 19): "v",
        (4, 20): "<", (4, 19): "<", (4, 1): "^",
    }
    return _room(20, 4, cells)


def build_close() -> list:
    """In: cmd (LEFT row2), state (TOP col6).
    Out: state (BOTTOM col5), output (BOTTOM col13)."""
    cells = {
        # closer u: recover (+4), stash u, read S; S==0 -> emit p+1, halt
        (1, 16): ">", (1, 17): "+", (1, 18): "M", (1, 19): "r", (1, 20): "X",
        (1, 21): "r", (1, 22): "M", (1, 23): "1", (1, 24): "+", (1, 25): "s",
        (1, 26): "H",
        # entry + dispatch + passive relay
        (2, 1): ">", (2, 2): "@", (2, 3): "r", (2, 4): "X",
        (2, 5): "r", (2, 6): "s", (2, 7): "r", (2, 8): "s", (2, 30): "v",
        # token>0: 4-check; ==4 -> finish
        (3, 4): ">", (3, 10): "M", (3, 11): "`", (3, 12): "4", (3, 13): "`",
        (3, 14): "W", (3, 15): "-", (3, 16): "X",
        (3, 17): "r", (3, 18): "X", (3, 21): "s", (3, 22): "H",
        (4, 18): ">", (4, 21): ">", (4, 22): "r", (4, 23): "M", (4, 24): "1",
        (4, 25): "+", (4, 26): "s", (4, 27): "H",
        # offend (wrong closer type): emit p+1, halt
        (5, 11): ">", (5, 12): "r", (5, 13): "M", (5, 14): "1", (5, 15): "+",
        (5, 16): "s", (5, 17): "H",
        # closer main: (S-u)/3, remainder != 0 -> offend, else pass S', p+1
        (6, 20): "<", (6, 19): "-", (6, 18): "M", (6, 17): "`", (6, 16): "3",
        (6, 15): "`", (6, 14): "W", (6, 13): "/", (6, 12): "W", (6, 11): "X",
        (6, 10): "W", (6, 9): "s", (6, 8): "r", (6, 7): "M", (6, 6): "1",
        (6, 5): "+", (6, 4): "s", (6, 2): "v",
        # home
        (8, 30): "<", (8, 2): "<", (8, 1): "^",
    }
    return _room(30, 8, cells)


def build_brackets() -> str:
    cv = Canvas()
    cv.put(0, 0, ["+-+", "|I|", "+-+"])       # I: rows 0-2
    cv.put(3, 4, build_classify())            # rows 3-20, cols 4-23
    cv.put(2, 26, build_open())               # rows 2-6, cols 26-47
    cv.put(25, 8, build_close())              # rows 25-34, cols 8-39
    cv.put(35, 17, ["+-+", "|O|", "+-+"])     # O: rows 35-37

    cv.pipe([(3, 1), (4, 1), (4, 3)])                     # I -> classify LEFT row1
    cv.pipe([(13, 24), (13, 25), (4, 25)])                # classify RIGHT row10 -> OPEN cmd (LEFT row2)
    cv.cells[(4, 25)] = ">"                               # terminal arrowhead doubles as the bend
    cv.pipe([(22, 6), (27, 6), (27, 7)])                  # classify -> CLOSE cmd (LEFT row2)
    cv.pipe([(8, 42), (23, 42), (23, 14), (24, 14)])      # OPEN state -> CLOSE state-in (TOP col6)
    cv.pipe([(35, 13), (38, 13), (38, 49), (0, 49), (0, 36), (1, 36)])  # CLOSE -> OPEN state-in (TOP col10)
    cv.pipe([(35, 21), (36, 21), (36, 20)])               # CLOSE output -> O
    return cv.render()
