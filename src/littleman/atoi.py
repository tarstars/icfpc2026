"""atoi: read n then n ASCII digit bytes, emit the integer. One pump room.

Register budget is two (A, B) plus BP for the digit counter, so the loop
keeps the *pre-scaled, pre-biased* accumulator in B:

    invariant   B = u = 10*acc - 48        (acc = value so far)
    read digit  r      A = c   (c = 48 + d)
    combine     +      A = u + c = 10*acc + d = acc'   (one op!)
    rebuild     M `10` * M `48` N + M      B = 10*acc' - 48

`d = c - 48` never has to be materialised: the -48 rides along inside u.
Round start seeds acc = 0 by building B = -48 from 6*8 (no literal needed).
Loop control: BP = n from `b`; `m` then `a` (BP>0 -> turn to the rebuild
lane, BP==0 -> straight on to `s` and back to the round header).
"""

from .canvas import Canvas

# --- pump room interior: rows 1..4, cols 1..11 (11 wide, 4 tall) ----------
#
# r1 (->)  round header:  r n, BP = n, B = -48
# r2 (<-)  loop head:     r, +, m, a   then exit lane -> s -> back up
# r3 (<-)  rebuild part 1: M, literal 10
# r4 (->)  rebuild part 2: *, M, literal 48, N, +, M, back up to r2

CELLS = {
    # row 1: header (man starts at @ facing right)
    (1, 1): ">", (1, 2): "@", (1, 3): "r", (1, 4): "b",
    (1, 5): "6", (1, 6): "M", (1, 7): "8", (1, 8): "*",
    (1, 9): "N", (1, 10): "M", (1, 11): "v",
    # row 2: loop head + exit lane
    (2, 11): "<", (2, 10): "r", (2, 9): "+", (2, 8): "m", (2, 7): "a",
    (2, 2): "s", (2, 1): "^",
    # row 3: rebuild A = 10 (literal read leftwards -> cells '1','0')
    (3, 7): "<", (3, 6): "M",
    (3, 5): "`", (3, 4): "1", (3, 3): "0", (3, 2): "`",
    (3, 1): "v",
    # row 4: 10*acc, then -48, then park in B; return up column 11
    (4, 1): ">", (4, 2): "*", (4, 3): "M",
    (4, 4): "`", (4, 5): "4", (4, 6): "8", (4, 7): "`",
    (4, 8): "N", (4, 9): "+", (4, 10): "M", (4, 11): "^",
}
W, H = 11, 4


def build_pump() -> list:
    grid = [[" "] * (W + 2) for _ in range(H + 2)]
    for c in range(W + 2):
        grid[0][c] = grid[H + 1][c] = "-"
    for r in range(H + 2):
        grid[r][0] = grid[r][W + 1] = "|"
    for r, c in ((0, 0), (0, W + 1), (H + 1, 0), (H + 1, W + 1)):
        grid[r][c] = "+"
    for (r, c), ch in CELLS.items():
        grid[r][c] = ch
    return ["".join(row) for row in grid]


def build_atoi() -> str:
    cv = Canvas()
    cv.put(0, 0, ["+-+", "|I|", "+-+"])      # I: rows 0-2, cols 0-2
    cv.put(3, 1, build_pump())               # pump: rows 3-8, cols 1-13
    cv.put(9, 0, ["+-+", "|O|", "+-+"])      # O: rows 9-11, cols 0-2
    cv.pipe([(1, 3), (1, 5), (2, 5)])        # I right -> down -> pump top
    cv.pipe([(9, 4), (10, 4), (10, 3)])      # pump bottom -> down -> O right
    return cv.render()


if __name__ == "__main__":  # pragma: no cover
    print(build_atoi(), end="")
