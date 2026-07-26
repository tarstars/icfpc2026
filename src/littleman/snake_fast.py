"""Snake, lap-reduced.  Same stations and geometry as :mod:`snake_press`,
but fewer ring laps per game tick.

WHERE THE TICKS GO (measured on ``snake_01.man``)
------------------------------------------------
Per tick round the machine costs ~1752 ticks and grows only ~13 ticks per
body cell, so the body is *not* the cost: the fixed protocol overhead is.
The packet does FOUR full ring laps per tick round, because five of the
twelve modes act on a station that has already emitted the mode word by
the time it learns the verdict:

    lap 1  IN(1) -> TICKA(2)            bounds check only
    lap 2  TICKA(3) -> TICKB(6)         apply move; scan
    lap 3  TICKB(7) -> TICKC(8) -> DRAW(11)
    lap 4  DRAW(12) -> IN(1)

A lap costs ~440 ticks and 73% of the walking is over *blank* cells (the
rooms are 92-98 columns wide and every corridor ends with a full-width
walk back to the entry).

WHAT THIS MODULE CHANGES
------------------------
1. TICKA merges modes 2 and 3 into one pass.  The reason they were split
   is that the mode word is emitted before ROW/COL are known; the fix is
   to stop signalling "out of bounds" with a mode at all.  TICKA applies
   the move and, when a coordinate leaves 0..15, emits -1 in its place
   (row 16 and col 16 are rewritten; -1 already is negative).  TICKB then
   detects the dead tick with two plain sign tests on the values it is
   relaying anyway -- no extra pass, no BP hand-off.
2. TICKB act6 gains those two sign tests plus a shared flush corridor
   that relays the rest of the packet and sets BP=1, which is exactly the
   collision verdict act7 already knows how to draw.

Mode 3 and TICKA's act3 become unreachable; they are left in place so the
dispatch chain and every other corridor stay byte-identical to the proven
build.  Net: two laps per tick round instead of four.
"""

from __future__ import annotations

from .canvas import Canvas
from .snake import Box, build_in, place_display_block

# --- placement (inherited from snake_press; TICKA/TICKB keep their size) ----
I_R, I_C = 0, 6
IN_R, IN_C = 6, 3
DRAW_R, DRAW_C = 6, 84
DISP_R, DISP_C = 39, 84
TICKA_R, TICKA_C = 75, 3
TICKB_R, TICKB_C = 113, 3
TICKC_R, TICKC_C = 113, 106
IN_WORD_PORT = (-1, 4)
IN_RING_PORT = (65, 40)
MIN_RING_CELLS = 160


def build_ticka_fast() -> list[str]:
    """TICKA with modes 2 and 3 merged (acts {2, 4, 5}).

    act2 now emits mode 6 directly and writes the *moved* head:

        [2, DR, ROW, DC, COL, FC, body, -1]
          -> [6, DR, ROW+DR, DC, COL+DC, FC, body, -1]

    with ROW+DR replaced by -1 when it is 16 (-1 needs no rewrite), and
    likewise for COL+DC.  ``M`16`W-X`` leaves A = v-16 and B = 16, so the
    in-range branch restores v with a single ``+``.
    """
    b = Box()
    # dispatch chain (unchanged): m-1 (rel), m-2, m-3, m-4, m-5
    b.put(2, 1, ">@rM1W-X")
    b.put(5, 8, ">M1W-X")
    b.put(10, 13, ">M1W-X")
    b.put(16, 18, ">M1W-X")
    b.put(21, 23, ">M1W-X")
    b.put(2, 9, "1s")
    b.put(2, 90, "v")
    for i, ch in enumerate("M5+s"):
        b.put(22 + i, 28, ch)
    b.put(27, 28, "<")
    b.put(27, 90, "<")
    b.put(27, 2, "v")
    b.put(28, 2, ">")
    b.put(28, 3, "5b>rsv")
    b.put(29, 5, "^ md")
    b.put(30, 8, ">^")
    b.put(29, 9, ">rsX")
    b.put(30, 12, "<")
    b.put(28, 12, ">")
    b.put(28, 90, "v")
    # ---- act2 (merged 2+3): row 5, branch rows 4 and 6 -------------------
    b.put(5, 14, "6s")                       # emit mode 6
    b.put(5, 16, "rsM")                      # DR: relay, B = DR
    b.put(5, 19, "r+")                       # A = ROW + DR
    b.put(5, 21, "M`16`W-X")                 # X at (5,28): ==0 -> row 16
    b.put(4, 28, ">+s")                      # in range: A = nrow, emit
    b.put(4, 33, "v")
    b.put(5, 29, "1Ns")                      # out of range: emit -1
    b.put(5, 33, ">")                        # merge
    b.put(5, 34, "rsM")                      # DC: relay, B = DC
    b.put(5, 37, "r+")                       # A = COL + DC
    b.put(5, 39, "M`16`W-X")                 # X at (5,46)
    b.put(4, 46, ">+s")
    b.put(4, 50, "v")
    b.put(5, 47, "1Ns")
    b.put(5, 50, ">")                        # merge
    b.put(5, 51, "rs")                       # FC
    b.put(5, 53, ">rsX")                     # body loop rows 5-6
    b.put(6, 53, "^  <")
    b.put(4, 56, ">")                        # MARK exit
    b.put(4, 78, "v")
    # ---- act3 (mode 3): retired, kept byte-identical ---------------------
    b.put(10, 19, "d")
    b.put(10, 20, "6srsMr+srsMr+srs")
    b.put(10, 36, ">rsX")
    b.put(11, 36, "^  <")
    b.put(9, 39, ">")
    b.put(9, 82, "v")
    b.put(11, 19, ">9s4b>rsv")
    b.put(12, 24, "^ md")
    b.put(13, 27, ">")
    b.put(13, 28, ">rsX")
    b.put(14, 28, "^  <")
    b.put(12, 31, ">")
    b.put(12, 84, "v")
    # ---- act4 (fruit) and act5 (init): unchanged -------------------------
    b.put(16, 24, "`10`s1srM`16`*Mr+M1+M3b>rsv")
    b.put(17, 47, "^ md")
    b.put(18, 50, ">rWsM")
    b.put(18, 55, ">rsX")
    b.put(19, 55, "^  <")
    b.put(17, 58, ">Ws9s")
    b.put(17, 86, "v")
    b.put(21, 29, "`10`s1s0srsM`16`*M1srs+M1+M0sWsM1NsWs`10`sr")
    b.put(21, 88, "v")
    # home row 33
    b.put(33, 1, "^")
    for c in (78, 80, 82, 84, 86, 88, 90):
        b.put(33, c, "<")
    return b.room()


def build_tickb_fast() -> list[str]:
    """TICKB with two out-of-bounds sign tests inserted into act6.

    TICKA now hands over ROW = -1 (or COL = -1) for a tick that leaves the
    board, so act6 tests the sign of each coordinate as it relays it.  A
    negative one turns the man north into a shared flush corridor (row 4)
    that relays the rest of the packet and sets BP = 1 -- act7's existing
    collision verdict, which emits mode 9 and lets DRAW sweep the body red.
    """
    b = Box()
    b.put(2, 1, ">@rM1W-X")
    b.put(5, 8, ">M2W-X")
    b.put(8, 13, ">M3W-X")
    b.put(20, 18, ">M1W-X")
    b.put(2, 9, "1Ms")
    b.put(2, 92, "v")
    b.put(5, 14, "3Ms")
    b.put(5, 94, "v")
    for i, ch in enumerate("M7+Ms"):
        b.put(21 + i, 23, ch)
    b.put(26, 23, "<")
    b.put(26, 3, "v")
    b.put(33, 3, "<")
    b.put(33, 92, "<")
    b.put(33, 94, "<")
    b.put(33, 2, "v")
    b.put(34, 2, ">")
    b.put(34, 3, "5b>rsv")
    b.put(35, 5, "^ md")
    b.put(36, 8, ">^")
    b.put(35, 9, ">rsX")
    b.put(36, 12, "<")
    b.put(34, 12, ">WM9W-M1W-X")
    b.put(34, 23, "rsrs")
    b.put(34, 92, "v")
    b.put(32, 22, ">")
    b.put(32, 96, "v")
    b.put(39, 96, "<")
    b.put(36, 22, ">")
    b.put(36, 94, "v")
    b.put(39, 94, "<")
    # ---- act6 (mode 6), with the two bounds tests ------------------------
    b.put(8, 19, "7s")
    b.put(8, 21, "rs")                       # DR
    b.put(8, 23, "rs")                       # ROW
    b.put(8, 25, "X>")                       # X at (8,25); merge at (8,26)
    b.put(9, 25, ">^")                       # ROW > 0 rejoin
    b.put(8, 27, "M`16`*M")                  # B = 16 * ROW
    b.put(8, 34, "rs")                       # DC
    b.put(8, 36, "rs")                       # COL
    b.put(8, 38, "X>")                       # X at (8,38); merge at (8,39)
    b.put(9, 38, ">^")                       # COL > 0 rejoin
    b.put(8, 40, "+M1+M")                    # A = n, B = n
    b.put(8, 45, "rs")                       # FC
    b.put(8, 47, "-X")                       # X at (8,48): FC == n -> eat
    # Dead flush.  The values still to relay may be 0 or negative (DC, COL
    # and FC all can be), so the sign loop cannot be entered directly: each
    # entry first sets BP and runs the counted relay, which forwards BP+1
    # values -- 4 from the ROW test (DC COL FC b1), 2 from the COL test.
    b.put(4, 25, ">3b")                      # ROW < 0 lands here
    b.put(6, 38, ">1b")                      # COL < 0 lands here
    b.put(6, 58, "^")
    b.put(4, 58, ">")
    b.put(4, 62, ">rsv")                     # counted relay, rows 4-6
    b.put(5, 62, "^ md")
    b.put(6, 65, ">^")
    b.put(5, 66, ">rsX")                     # body sign loop
    b.put(6, 69, "<")
    b.put(4, 69, ">1b")                      # MARK exit: BP = 1 (collision)
    b.put(4, 76, "v")
    b.put(39, 76, "<")
    # eat / scan, shifted right by four columns to clear the tests
    b.put(8, 50, ">rsX")                     # eat: body relay loop rows 8-9
    b.put(9, 50, "^  <")
    b.put(7, 53, ">2b")                      # eat flag
    b.put(7, 78, "v")
    b.put(7, 48, ">v")                       # FC-test merge: north path
    b.put(10, 48, ">>")
    b.put(10, 50, ">  rX")                   # scan entry; X1 at (10,54)
    b.put(9, 54, ">s0b")                     # MARK first: all legal
    b.put(9, 80, "v")
    b.put(11, 54, "s")
    b.put(12, 54, "-")
    b.put(13, 54, "X")                       # X2 (heading south)
    b.put(13, 50, "^")
    b.put(13, 56, "v")
    b.put(14, 56, "<")
    b.put(14, 50, "^")
    b.put(15, 54, ">")                       # X2 == 0: PENDING row
    b.put(15, 58, "rX")                      # X3 at (15,59)
    b.put(14, 59, ">s0b")
    b.put(14, 82, "v")
    b.put(16, 59, "s")
    b.put(17, 59, ">rsX")                    # flush loop rows 17-18
    b.put(18, 59, "^  <")
    b.put(16, 62, ">1b")                     # collision flag
    b.put(16, 84, "v")
    # ---- act7 (mode 7): unchanged ----------------------------------------
    b.put(20, 26, "d")
    # ... MrsWsM: the trailing M parks the new head code n in B, where it
    # survives the body relay, so the MARK exit can append it as a trailer
    # for TICKC (which turns it into DRAW's green-head pixel).
    b.put(20, 27, "8srsrsM`16`*Mrsrs+M1+MrsWsM")
    b.put(20, 54, ">rsX")
    b.put(21, 54, "^  <")
    b.put(19, 57, ">Ws")                     # MARK exit: append trailer n
    b.put(19, 86, "v")
    b.put(21, 26, "x")
    b.put(21, 25, "v")
    b.put(23, 25, ">9s4b>rsv")
    b.put(24, 30, "^ md")
    b.put(25, 33, ">>rsX")
    b.put(26, 34, "^  <")
    b.put(24, 37, ">")
    b.put(24, 88, "v")
    b.put(21, 44, "v")
    b.put(28, 44, "<")
    b.put(28, 4, "v")
    b.put(30, 4, ">")
    b.put(30, 5, "`10`s1srsrsM`16`*Mrsrs+M1+Mr0sWsM")
    b.put(30, 38, ">rsX")
    b.put(31, 38, "^  <")
    b.put(29, 41, ">Ws`10`s")
    b.put(29, 90, "v")
    b.put(39, 90, "<")
    b.put(39, 1, "^")
    for c in (76, 78, 80, 82, 84, 86, 88, 92):
        b.put(39, c, "<")
    return b.room()


def build_tickc_fast() -> list[str]:
    """TICKC (act mode 8): drop the tail and hand DRAW *both* pixels.

    [8, DR, ROW, DC, COL, FC, b1..bL, -1, n]
      -> [11, DR, ROW, DC, COL, FC, b1..b(L-1), -1, tail, n]
    The old build emitted [11, 12, ...] and the erase colour 0, which cost
    a whole extra lap: DRAW painted the tail black on mode 11 and then had
    to come round again on mode 12 to repaint the head green.  Handing it
    the tail *and* the head in one packet lets DRAW do both in one pass,
    still tail-first, so a head landing on the vacated cell stays green.
    """
    b = Box()
    cells = {
        (1, 2): "v", (1, 8): "<",
        (2, 1): ">", (2, 2): "@", (2, 3): "r", (2, 4): "M", (2, 5): "8",
        (2, 6): "W", (2, 7): "-", (2, 8): "X",
        (2, 9): "`", (2, 10): "1", (2, 11): "1", (2, 12): "`", (2, 13): "s",
        (2, 18): "4", (2, 19): "b",
        (2, 20): ">", (2, 21): "r", (2, 22): "s", (2, 23): "v",
        (3, 20): "^", (3, 22): "m", (3, 23): "d",
        # MARK exit: emit MARK, the held tail, then relay TICKB's n trailer
        (3, 31): ">", (3, 32): "s", (3, 33): "W", (3, 34): "s", (3, 35): "r",
        (3, 36): "s", (3, 37): "v",
        (4, 23): ">", (4, 24): "r", (4, 25): "M", (4, 26): ">",
        (4, 29): ">", (4, 30): "r", (4, 31): "X",
        (6, 26): "^", (6, 27): "M", (6, 28): "W", (6, 29): "s", (6, 30): "W",
        (6, 31): "<",
        (7, 2): ">", (7, 8): ">", (7, 9): "+", (7, 10): "M", (7, 11): "s",
        (7, 12): "5", (7, 13): "b",
        (7, 14): ">", (7, 15): "r", (7, 16): "s", (7, 17): "v",
        (8, 14): "^", (8, 16): "m", (8, 17): "d",
        (8, 20): ">", (8, 21): "W", (8, 22): "M", (8, 23): "9", (8, 24): "W",
        (8, 25): "-", (8, 26): "M", (8, 27): "1", (8, 28): "W", (8, 29): "-",
        (8, 30): "X",
        (8, 31): "r", (8, 32): "s", (8, 33): "r", (8, 34): "s", (8, 35): "v",
        (9, 17): ">", (9, 18): "r", (9, 19): "s", (9, 20): "X",
        (10, 17): "^", (10, 20): "<",
        (7, 30): ">", (7, 45): "v",
        (11, 1): "^", (11, 30): "<", (11, 35): "<", (11, 37): "<",
        (11, 45): "<",
    }
    for (r, c), ch in cells.items():
        b.put(r, c, ch)
    b.put(11, 44, " ")
    return b.room()


def build_draw_fast() -> list[str]:
    """DRAW with modes 11 and 12 merged into one pass.

    11: [11, hdr5, body, -1, T, N] -> [1, hdr5, body, -1]
        + pixel(T, black) + pixel(N, green) + commit
    Mode 12's corridor is left in place but is now unreachable.
    """
    b = Box()
    cells = {}

    def put(r, c, text):
        for i, ch in enumerate(text):
            if ch != "~":
                cells[(r, c + i)] = ch

    put(2, 1, ">@rM9W-X")
    put(5, 8, ">M1W-X")
    put(8, 13, ">M1W-X")
    put(11, 18, ">M1W-X")
    put(1, 2, "v"); put(1, 8, "<")
    put(14, 2, ">+Ms5b>rsv")
    put(15, 8, "^ md")
    put(16, 11, ">^")
    put(15, 12, ">rsX")
    put(16, 13, "~~<")
    put(14, 15, ">")
    put(14, 70, "v")
    put(2, 9, "1s4b>rsv")
    put(3, 13, "^ md")
    put(4, 16, "> ^")
    put(3, 18, ">                 >rX")
    put(4, 18, "^sN+`02`M*`61`M-W1Ms<")
    put(2, 38, ">s9Ns")
    put(2, 66, "v")
    put(5, 14, "rs4b>rsv")
    put(6, 18, "^ md")
    put(7, 21, ">^")
    put(6, 22, ">rsX")
    put(7, 25, "<")
    put(5, 25, ">rM1W-M`16`*Mr+M`11`+Ns9Ns")
    put(5, 67, "v")
    # ---- merged draw (mode 11): tail black, then head green, then commit
    put(8, 19, "1s4b>rsv")
    put(9, 23, "^ md")
    put(10, 26, ">^")
    put(9, 27, ">rsX")
    put(10, 30, "<")
    put(8, 30, ">rM`16`*M5N+NsrM`16`*M5+Ns9Ns")
    put(8, 68, "v")
    put(11, 24, "1s4b>rsv")
    put(12, 28, "^ md")
    put(13, 31, ">rsM^")
    put(12, 35, ">rsX")
    put(13, 36, "~~<")
    put(11, 38, ">WM1W-M`16`*M`21`+Ns9Ns")
    put(11, 69, "v")
    put(17, 66, "<<<<<")
    put(17, 1, "^")

    for (r, c), ch in cells.items():
        b.put(r, c, ch)
    b.put(1, 70, " ")
    return b.room()


# IN's act path used to leave the dispatch at (58,45), walk east to col 72,
# north to row 2 and west to col 6 -- 148 cells of empty room before it read
# the command word.  Column 49 is free the whole height of the room (every
# corridor between rows 26 and 54 stops at col 48 and the transit columns
# start at 65), so the same walk is 102 cells up col 49.  Likewise the home
# row used to run west to col 2 and climb back east to the ring read at col
# 40; col 39 is free over rows 59..62, so it turns north 37 columns earlier.
IN_SHORTCUTS = {(58, 49): "^", (2, 49): "<", (63, 39): "^", (58, 39): ">"}


def build_in_fast() -> list[str]:
    """:func:`littleman.snake.build_in` with two walk shortcuts patched in.

    Only blank cells are written, so no corridor, literal or pipe binding
    moves; the room keeps its shape and both of its port offsets.
    """
    rows = [list(line) for line in build_in()]
    for (r, c), ch in IN_SHORTCUTS.items():
        assert rows[r][c] == " ", (r, c, rows[r][c])
        rows[r][c] = ch
    return ["".join(line) for line in rows]


def ring_capacity(text: str) -> int:
    """Cell count of the six ring pipes (see snake_press.ring_capacity)."""
    from .snake_press import ring_capacity as _cap

    return _cap(text)


def build_fast_snake() -> str:
    """The lap-reduced Snake machine.  Deterministic: no randomness."""
    cv = Canvas()
    cv.put(I_R, I_C, ["+-+", "|I|", "+-+"])
    cv.put(IN_R, IN_C, build_in_fast())
    cv.put(DRAW_R, DRAW_C, build_draw_fast())
    place_display_block(cv, DISP_R, DISP_C)
    cv.put(TICKA_R, TICKA_C, build_ticka_fast())
    cv.put(TICKB_R, TICKB_C, build_tickb_fast())
    cv.put(TICKC_R, TICKC_C, build_tickc_fast())

    word_end = (IN_R + IN_WORD_PORT[0], IN_C + IN_WORD_PORT[1])
    cv.pipe([(I_R + 3, word_end[1]), word_end])
    cv.pipe([(71, 20), (74, 20)])
    cv.pipe([(110, 20), (112, 20)])
    cv.pipe([(115, 101), (115, 105)])
    cv.pipe([(112, 150), (25, 150)])
    cv.pipe([(25, 90), (28, 90), (28, 82), (DISP_R + 2, 82), (DISP_R + 2, 83)])
    ring_end = (IN_R + IN_RING_PORT[0], IN_C + IN_RING_PORT[1])
    cv.pipe([(DISP_R + 7, DISP_C + 7), (58, DISP_C + 7), (58, 80),
             (ring_end[0], 80), ring_end])
    cv.cells[ring_end] = "^"
    text = cv.render()
    assert ring_capacity(text) >= MIN_RING_CELLS, ring_capacity(text)
    return text
