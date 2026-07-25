"""Palette: commit 16 uniform 8x8 frames, colour 0..15, then halt.

One room, one man, two pipes into the display (DATA -> left wall,
SWAP -> bottom wall).  No ADDR pipe is needed: the display cursor starts
at 0 and auto-increments (mod 64) on every DATA write, so streaming 64
values per frame lands exactly back on cell 0.

Register discipline
  A  holds the current colour k while the inner ring runs ('s' sends A).
  B  parks k across the BP reload ('W' swap), then holds k+1 in the tail.
  BP is the inner pixel countdown (65 passes -> 64 sends).

Program shape (one closed walk):

  HEAD  row 16, leftward:  `65` -> A, b (BP=65), W (A=k, B=65), '^'
  RING  rows 14/15, 6 cells: > m d / < s ^   (d turns while BP>0)
  TAIL  row 14 rightward:  M(B=k) 1 + (A=k+1) M(B=k+1) 1 s(SWAP<-1)
                           `16` -> A
        row 15 leftward:   & (A = 16 & (k+1))  X
                           A>0 -> up into H ; A==0 -> back to HEAD

Geometry (canvas 18x18, footprint 18^2):
  display rows 0..9   cols 1..10   (8x8 interior)
  DATA pipe  room top wall col 4  -> up, left along row 10, up col 0,
             right into display left wall at (5,1)
  SWAP pipe  room top wall col 14 -> up, left along row 10, up col 6,
             into display bottom wall at (9,6)
  room  rows 12..17  cols 1..17    (interior rows 13..16, cols 2..16)
"""

from __future__ import annotations

from .canvas import Canvas

# --- canvas geometry -------------------------------------------------
DISP_TOP, DISP_LEFT = 0, 1
DISP_BOT, DISP_RIGHT = 9, 10
ROOM_TOP, ROOM_LEFT = 12, 1
ROOM_BOT, ROOM_RIGHT = 17, 17

DATA_PORT_COL = 4   # room top wall column the DATA pipe leaves from
SWAP_PORT_COL = 14  # room top wall column the SWAP pipe leaves from
DATA_ATTACH_ROW = 5  # display left-wall row the DATA pipe enters
SWAP_ATTACH_COL = 6  # display bottom-wall column the SWAP pipe enters

# --- room interior program (absolute canvas coords) ------------------
# row 13: spawn lane + halt cell
# row 14: ring top  (cols 2..4) + tail part 1 (cols 5..16)
# row 15: ring base (cols 2..4) + tail part 2 (cols 5..16)
# row 16: head      (cols 2..9)
CELLS: dict[tuple[int, int], str] = {}


def _row(row: int, start_col: int, glyphs: str) -> None:
    for i, ch in enumerate(glyphs):
        if ch != "_":
            CELLS[(row, start_col + i)] = ch


#            col: 2         6         10        14
_row(13, 2, "@......v....H..")
_row(14, 2, ">mdM1+M.1s`16`v")
_row(15, 2, "^s<....v....X&<")
_row(16, 2, "^Wb`56`<_______")


def build_room() -> dict[tuple[int, int], str]:
    """Room walls plus the interior program, keyed by canvas coords."""
    cells: dict[tuple[int, int], str] = {}
    for c in range(ROOM_LEFT, ROOM_RIGHT + 1):
        cells[(ROOM_TOP, c)] = "-"
        cells[(ROOM_BOT, c)] = "-"
    for r in range(ROOM_TOP, ROOM_BOT + 1):
        cells[(r, ROOM_LEFT)] = "|"
        cells[(r, ROOM_RIGHT)] = "|"
    for r, c in (
        (ROOM_TOP, ROOM_LEFT), (ROOM_TOP, ROOM_RIGHT),
        (ROOM_BOT, ROOM_LEFT), (ROOM_BOT, ROOM_RIGHT),
    ):
        cells[(r, c)] = "+"
    cells.update(CELLS)
    return cells


def build_display() -> dict[tuple[int, int], str]:
    cells: dict[tuple[int, int], str] = {}
    for c in range(DISP_LEFT + 1, DISP_RIGHT):
        cells[(DISP_TOP, c)] = "="
        cells[(DISP_BOT, c)] = "="
    for r in range(DISP_TOP + 1, DISP_BOT):
        cells[(r, DISP_LEFT)] = ":"
        cells[(r, DISP_RIGHT)] = ":"
    for r, c in (
        (DISP_TOP, DISP_LEFT), (DISP_TOP, DISP_RIGHT),
        (DISP_BOT, DISP_LEFT), (DISP_BOT, DISP_RIGHT),
    ):
        cells[(r, c)] = "+"
    return cells


def build() -> str:
    canvas = Canvas()
    canvas.cells.update(build_display())
    canvas.cells.update(build_room())
    # DATA: room top wall -> up -> left along row 10 -> up col 0 -> right
    canvas.pipe([
        (ROOM_TOP - 1, DATA_PORT_COL), (10, DATA_PORT_COL), (10, 0),
        (DATA_ATTACH_ROW, 0),
    ])
    canvas.cells[(DATA_ATTACH_ROW, 0)] = ">"
    # SWAP: room top wall -> up -> left along row 10 -> up into display base
    canvas.pipe([
        (ROOM_TOP - 1, SWAP_PORT_COL), (10, SWAP_PORT_COL),
        (10, SWAP_ATTACH_COL),
    ])
    canvas.cells[(10, SWAP_ATTACH_COL)] = "^"
    return canvas.render()
