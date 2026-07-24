"""Compact rebuild of the Sort systolic pipeline (candidate sort_04).

Same machine as sort_00/sort_01 — 16 compare/store stages in a chain, a
dispatcher, a loader and a gate — with the same token protocol:

* every real value is shifted by SHIFT = 10001 so data tokens are >= 1
  and the sign bit is free for the reset token;
* a stage keeps max(A, B) and forwards min(A, B), so the empty state is
  0 and the chain ends up holding the values in descending order;
* the loader appends 16 HIGH = 2 * SHIFT tokens, which walk the stored
  values out in ascending order, then one RESET = -1 that clears every
  stage's register;
* the gate drops 16 warm-up tokens, decodes n values and eats the RESET.

What changed is only the geometry, which is what the score cares about:
each stage went from a 14x20 room with a 24-cell return track to a 9x9
room, and the three control rooms were rebuilt around test-before-relay
loops (`d` reached before the body relays exactly BP times, so no BP+1
fixups) and computed constants (HIGH = SHIFT + SHIFT rather than its own
7-cell literal).

Stage register discipline, per token, entering `r` heading south:

    A < 0  reset   s 0 M          forward -1, clear the register
    A = 0  warm-up          straight into the compare
    A > 0  data             via `-` into the compare
    compare on d = A - B:
      d < 0  + s              forward the incoming value, keep stored
      d = 0  + s              same
      d > 0  W s + M          forward stored, retain the incoming value

`s` at (4,3) is shared by the reset path (walking east) and the d < 0
arm (walking north): both want to send whatever is in A.
"""

from __future__ import annotations

from .canvas import Canvas

SHIFT = 10001
STAGES = 16

# --- stage ---------------------------------------------------------------
# Interior 7x7. The little man starts at (1,1), off the racetrack, and
# falls into the loop through the (1,2) convergence cell.
STAGE_CELLS = {
    (1, 1): "@",                                    # prologue, off the loop
    (1, 2): "v", (1, 3): "<", (1, 6): "<", (1, 7): "<",
    (2, 2): "r",
    (3, 1): "v", (3, 2): "X", (3, 3): "s", (3, 4): "0", (3, 5): "M",
    (3, 6): "^",
    (4, 1): "-", (4, 2): "-", (4, 3): "+",
    (5, 1): ">", (5, 2): ">", (5, 3): "X", (5, 4): "+", (5, 5): "s",
    (5, 6): "^", (5, 7): "M",
    (6, 3): ">", (6, 4): "W", (6, 5): "s", (6, 6): "+", (6, 7): "^",
}


def _room(height: int, width: int, cells: dict) -> list[str]:
    """Rectangular room from 1-based interior cell placements."""
    rows = [
        list("+" + "-" * width + "+"),
        *[list("|" + " " * width + "|") for _ in range(height)],
        list("+" + "-" * width + "+"),
    ]
    for (r, c), ch in cells.items():
        rows[r][c] = ch
    return ["".join(row) for row in rows]


def build_stage() -> list[str]:
    return _room(6, 7, STAGE_CELLS)


def build_stage_probe() -> str:
    """One stage wired I -> stage -> O, for isolated semantics testing."""
    cv = Canvas()
    cv.put(2, 0, ["+-+", "|I|", "+-+"])          # I: rows 2-4, cols 0-2
    cv.put(0, 5, build_stage())                  # stage: rows 0-8, cols 5-13
    cv.put(5, 16, ["+-+", "|O|", "+-+"])         # O: rows 5-7, cols 16-18
    cv.pipe([(3, 3), (3, 4)])                    # I -> stage left wall row 3
    cv.pipe([(6, 14), (6, 15)])                  # stage right wall row 6 -> O
    return cv.render()


def stage_model(tokens: list[int]) -> list[int]:
    """Reference semantics of one stage, for comparison with the sim."""
    out, b = [], 0
    for a in tokens:
        if a < 0:
            out.append(a)
            b = 0
        else:
            out.append(min(a, b))
            b = max(a, b)
    return out


# --- loader --------------------------------------------------------------
# Reads n, encodes n values (+SHIFT), appends 16 HIGH tokens, then RESET.
# HIGH is computed as SHIFT + SHIFT rather than spending a second literal.
LOADER_CELLS = {
    (1, 1): ">", (1, 2): "@", (1, 3): "r", (1, 4): "b",
    (1, 5): "`", (1, 6): "1", (1, 7): "0", (1, 8): "0", (1, 9): "0",
    (1, 10): "1", (1, 11): "`", (1, 12): "M", (1, 13): "v",
    (2, 2): "v", (2, 13): "<",
    (3, 2): ">", (3, 7): "d",
    (3, 8): "`", (3, 9): "1", (3, 10): "6", (3, 11): "`",
    (3, 12): "b", (3, 13): "W", (3, 14): "M", (3, 15): "+", (3, 16): "v",
    (4, 2): "^", (4, 3): "m", (4, 4): "s", (4, 5): "+", (4, 6): "r",
    (4, 7): "<",
    (5, 10): "v", (5, 16): "<",
    (6, 10): ">", (6, 14): "d", (6, 15): "v",
    (7, 10): "^", (7, 12): "m", (7, 13): "s", (7, 14): "<",
    (8, 1): "^", (8, 12): "s", (8, 13): "N", (8, 14): "1", (8, 15): "<",
}

# --- gate ----------------------------------------------------------------
# Drops 16 warm-up tokens, then decodes and emits until the RESET token's
# sign ends the round. Detecting RESET is why no control pipe carrying n
# is needed, which in turn removes the dispatcher room entirely.
GATE_CELLS = {
    (1, 1): ">", (1, 2): "@",
    (1, 3): "`", (1, 4): "1", (1, 5): "6", (1, 6): "`", (1, 7): "b",
    (1, 8): "`", (1, 9): "1", (1, 10): "0", (1, 11): "0", (1, 12): "0",
    (1, 13): "1", (1, 14): "`", (1, 15): "M", (1, 16): "v",
    (2, 2): "v", (2, 16): "<",
    (3, 2): ">", (3, 6): "d", (3, 7): "v",
    (4, 2): "^", (4, 4): "m", (4, 5): "r", (4, 6): "<",
    (5, 1): "^", (5, 3): "<",
    (6, 1): ">", (6, 2): "r", (6, 3): "X", (6, 4): "v",
    (7, 3): ">", (7, 4): ">", (7, 5): "-", (7, 6): "s", (7, 7): "v",
    (8, 1): "^", (8, 7): "<",
}


def build_loader() -> list[str]:
    return _room(8, 16, LOADER_CELLS)


def build_gate() -> list[str]:
    return _room(8, 16, GATE_CELLS)


def build_loader_probe() -> str:
    cv = Canvas()
    cv.put(0, 0, ["+-+", "|I|", "+-+"])
    cv.put(0, 5, build_loader())
    cv.put(4, 25, ["+-+", "|O|", "+-+"])
    cv.pipe([(1, 3), (1, 4)])
    cv.pipe([(5, 23), (5, 24)])
    return cv.render()


def build_gate_probe() -> str:
    cv = Canvas()
    cv.put(0, 0, ["+-+", "|I|", "+-+"])
    cv.put(0, 5, build_gate())
    cv.put(4, 25, ["+-+", "|O|", "+-+"])
    cv.pipe([(1, 3), (1, 4)])
    cv.pipe([(5, 23), (5, 24)])
    return cv.render()


def loader_model(values: list[int]) -> list[int]:
    return (
        [v + SHIFT for v in values] + [2 * SHIFT] * STAGES + [-1]
    )


def gate_model(values: list[int]) -> list[int]:
    """Gate input is 16 warm-up zeros, the encoded sorted values, RESET."""
    return list(values)


# --- assembly ------------------------------------------------------------
# The stage chain runs as a VERTICAL serpentine (down col 0, up col 1, ...)
# so that stage 0 and stage 15 both surface on the array's top row. That
# puts the loader and the gate in one band above the array, each two cells
# from the stage it talks to; a horizontal serpentine would strand stage 15
# at the bottom-left and force a program-length pipe to reach it.
ROW_PITCH = 10      # 8-row room + the 2 cells a pipe needs between rooms
COL_PITCH = 11      # 9-col room + the same 2-cell pipe gap
ARRAY_TOP = 12


def _stage_origin(index: int) -> tuple[int, int]:
    col = index // 4
    k = index % 4
    row = k if col % 2 == 0 else 3 - k
    return ARRAY_TOP + row * ROW_PITCH, col * COL_PITCH


def build_sort_pipe() -> str:
    cv = Canvas()
    cv.put(0, 0, ["+-+", "|I|", "+-+"])       # I: rows 0-2, cols 0-2
    cv.put(0, 5, build_loader())              # loader: rows 0-9, cols 5-22
    cv.put(0, 25, build_gate())               # gate: rows 0-9, cols 25-42
    cv.put(0, 45, ["+-+", "|O|", "+-+"])      # O: rows 0-2, cols 45-47
    cv.pipe([(1, 3), (1, 4)])                 # I -> loader
    cv.pipe([(1, 43), (1, 44)])               # gate -> O

    origins = [_stage_origin(i) for i in range(STAGES)]
    for top, left in origins:
        cv.put(top, left, build_stage())

    cv.pipe([(10, 6), (11, 6)])               # loader -> stage 0
    cv.pipe([(11, 37), (10, 37)])             # stage 15 -> gate

    for (top, left), (ntop, nleft) in zip(origins, origins[1:]):
        if left == nleft:
            if ntop > top:                    # descending column
                cv.pipe([(top + 8, left + 4), (top + 9, left + 4)])
            else:                             # ascending column
                cv.pipe([(top - 1, left + 4), (top - 2, left + 4)])
        else:                                 # step to the next column
            cv.pipe([(top + 4, left + 9), (top + 4, left + 10)])
    return cv.render()
