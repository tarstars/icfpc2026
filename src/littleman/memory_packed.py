"""Generator for a PACKED Memory machine (`memory_02` candidate).

Baseline `memory.py` circulates 100 raw cell values around a FIFO ring, so an
operation whose target sits ``k`` positions away costs ``k+1`` ring-item
relays. Profiling `memory_01` on the public "interleaved cells" case shows the
ring relays dominate: 6108 relays over 125 operations at ~8.9 ticks each,
accounting for ~93% of that case's 55 482 ticks.

This module packs THREE cell values into one signed-64 word, shrinking the
circulating ring from 100 items to 34 and the relay count on the same case
from 6108 to 1994 (3.06x).

Packing
-------
A cell value ``v`` lies in ``[-1_000_000, 1_000_000]``, which fits exactly in a
signed 21-bit field (``[-1_048_576, 1_048_575]``). Three such fields are stored
in bits ``[0,21)``, ``[21,42)`` and ``[42,63)`` of one word::

    word = (f0 & MASK21) | ((f1 & MASK21) << 21) | ((f2 & MASK21) << 42)

with ``MASK21 = 2**21 - 1``. Because every field is masked to 21 bits before
being shifted in, bit 63 is always 0 and a word is always a non-negative
signed-64 integer; no littleman arithmetic ever wraps. A freshly zeroed memory
is therefore the word ``0``, so the ring seeds with 34 plain zeros instead of a
19-digit literal.

Cell ``addr`` lives in word ``addr // 3``, field ``addr % 3`` -- both produced
by a single littleman ``/`` with ``B = 3``. With ``shift = 21 * (addr % 3)``:

* read:  ``value = (word << (43 - shift)) >> 43``. The left shift parks the
  field's sign bit in bit 63 and the arithmetic right shift sign-extends it,
  so neither a mask nor a bias constant is needed.
* write: ``word' = (word & ~(MASK21 << shift)) | ((v & MASK21) << shift)``.

Both forms only ever need two live quantities at a time, which is what makes
them expressible with A and B alone.

Architecture
------------
::

    I -> P1 -> HEAD -> P2 -> STATION -> O
                             STATION <-> RELAY   (the 34-word ring)

* ``P1`` parses one operation and emits ``[tag, w, w, shift, x, shift]``,
  where ``tag`` is 0 (READ) or 1 (WRITE) and ``x`` is 0 (READ) or the written
  value. ``tag`` is stashed in the write-only backpack, so one ``d`` near the
  end of an otherwise straight-line room performs the whole branch.
* ``HEAD`` carries the head word index ``hw`` in A across laps -- no delay
  pipe -- and rewrites the stream to ``[tag, k, shift, x, shift]`` with
  ``k = (w - hw) % 34``, then leaves ``hw = (w + 1) % 34`` in A.
* ``P2`` turns the tail into the constants the station needs:
  ``[tag, k, 43 - shift]`` for a READ and
  ``[tag, k, ~(MASK21 << shift), (v & MASK21) << shift]`` for a WRITE.
* ``STATION`` is the only room on the ring. It seeds 34 zeros, then per
  operation relays ``k+1`` words for a READ (leaving the target in A and the
  decode constant in B, which survives the relay loop) or ``k`` words for a
  WRITE before splicing the new field in.
* ``RELAY`` closes the ring: a pipe may not have the same room as source and
  destination, so one minimal 6-tick relay room is required. Its man runs
  concurrently with the station's, so it does not add to the per-item cost.

Everything here is new; `memory.py` and `memory_01.man` are untouched.
"""

from __future__ import annotations

from .canvas import Canvas

# --------------------------------------------------------------- constants
CELLS = 100
FIELDS_PER_WORD = 3
FIELD_BITS = 21
WORDS = (CELLS + FIELDS_PER_WORD - 1) // FIELDS_PER_WORD  # 34
MASK21 = (1 << FIELD_BITS) - 1                            # 2_097_151
DECODE_BASE = 64 - FIELD_BITS                             # 43

VALUE_MIN = -1_000_000
VALUE_MAX = 1_000_000


# ------------------------------------------------------- reference packing
def pack(values: list[int]) -> int:
    """Pack up to three signed cell values into one word (little-endian)."""
    word = 0
    for i, v in enumerate(values):
        word |= (v & MASK21) << (FIELD_BITS * i)
    return word


def read_field(word: int, field: int) -> int:
    """Signed value in ``field`` of ``word``, exactly as the machine reads it."""
    left = DECODE_BASE - FIELD_BITS * field
    shifted = (word << left) & ((1 << 64) - 1)
    if shifted >= 1 << 63:  # reinterpret as a signed 64-bit integer
        shifted -= 1 << 64
    return shifted >> DECODE_BASE


def write_field(word: int, field: int, value: int) -> int:
    """``word`` with ``field`` replaced by ``value``."""
    shift = FIELD_BITS * field
    return (word & ~(MASK21 << shift)) | ((value & MASK21) << shift)


def cell_to_word_field(addr: int) -> tuple[int, int]:
    """Cell address -> (word index, field index)."""
    return divmod(addr, FIELDS_PER_WORD)


# ------------------------------------------------------------- room helper
class Room:
    """A room built by explicit 1-indexed interior cell placement.

    Hand-written ASCII art for these rooms is unreadable and easy to
    mis-index, so every instruction is placed by coordinate and the walls are
    rendered afterwards.
    """

    def __init__(self, rows: int, cols: int):
        self.rows = rows
        self.cols = cols
        self.cells: dict[tuple[int, int], str] = {}

    def put(self, row: int, col: int, text: str) -> None:
        """Write ``text`` rightwards starting at interior cell (row, col)."""
        for i, ch in enumerate(text):
            c = col + i
            if not (1 <= row <= self.rows and 1 <= c <= self.cols):
                raise ValueError(f"cell ({row},{c}) outside {self.rows}x{self.cols}")
            if (row, c) in self.cells:
                raise ValueError(f"cell ({row},{c}) already holds {self.cells[(row, c)]!r}")
            self.cells[(row, c)] = ch

    def col(self, col: int, rows: range | list, ch: str) -> None:
        """Write the same glyph down a column."""
        for r in rows:
            self.put(r, col, ch)

    def render(self) -> list[str]:
        top = "+" + "-" * self.cols + "+"
        body = [
            "|" + "".join(self.cells.get((r, c), " ") for c in range(1, self.cols + 1)) + "|"
            for r in range(1, self.rows + 1)
        ]
        return [top, *body, top]


# ------------------------------------------------------------------- rooms
def build_p1() -> Room:
    """Parse one operation.

    Stream out: ``[tag, w, w, shift, x, shift]``.

    ``r`` reads the single input pipe and ``s`` writes the single output pipe,
    so no nearest-pipe resolution is involved here.
    """
    room = Room(3, 27)
    # r(op) s(tag) b(BP=op) | r(addr) M 3 W / -> A=w, B=f
    # s(w) s(w) | W -> A=f, B=w | M 3 `21` * -> A=shift=21*f
    # s(shift) M(B=shift) d(branch on BP)
    room.put(1, 1, ">@rsbrM3W/ssWM`21`*sMd")
    room.put(1, 23, "0sWsv")          # READ tail: x=0, then shift again
    room.put(2, 22, ">rsWsv")         # WRITE tail: x=value, then shift again
    room.put(3, 27, "<")
    room.col(1, [2, 3], "^")
    return room


def build_head() -> Room:
    """Head-pointer arithmetic; ``hw`` rides in A across laps.

    Stream in ``[tag, w, w, shift, x, shift]``, out ``[tag, k, shift, x, shift]``
    with ``k = (w - hw) % 34``; leaves ``hw' = (w + 1) % 34`` in A.
    """
    room = Room(2, 27)
    # M(B=hw) r(tag) s | r(w) - M `34` W % -> A=k | s(k)
    # r(w) M 1 + M `34` W % -> A=hw' | M(B=hw')
    room.put(1, 1, ">@Mrsr-M`34`W%srM1+M`34`W%v")
    # westward tail: r s r s r s W  (forward the three trailing tokens, then
    # swap hw' back into A for the next lap)
    room.put(2, 19, "WsrsrsrM<")
    room.put(2, 1, "^")
    return room


def build_p2() -> Room:
    """Constant builder.

    Stream in ``[tag, k, shift, x, shift]``.
    Stream out ``[tag, k, 43-shift]`` (READ) or
    ``[tag, k, ~(MASK21<<shift), (v & MASK21) << shift]`` (WRITE).
    """
    room = Room(5, 24)
    # header: r(tag) s b(BP=tag) r(k) s d(branch)
    room.put(1, 1, ">@rsbrsd")
    # READ, straight on: r(shift) M `43` - -> A = 43-shift, s, then drop the
    # two trailing tokens (x and the second shift).
    room.put(1, 9, "rM `43`-srr")
    room.put(1, 24, "v")
    room.put(2, 8, "v")
    # WRITE row A (eastward): r(shift) M `2097151` { -> MASKF, M, 1
    room.put(3, 8, ">rM`2097151`{M1")
    room.put(3, 23, "v")
    # WRITE row B (westward): N ~ -> NOTMASK, s; then `2097151` walked west,
    # M, r(x=value), & -> u, M, r(shift), W, { -> nfP, s
    room.put(4, 23, "<")
    room.put(4, 20, "s~N")            # walked west: N, ~, s
    room.put(4, 10, "`1517902`")      # walked west: 2097151
    room.put(4, 2, "s{WrM&rM")        # walked west: M r & M r W { s
    room.put(5, 24, "<")
    room.col(1, [2, 3, 4, 5], "^")
    return room


def build_station() -> Room:
    """The only room on the ring: seeds it, relays it, reads and writes it.

    Pipes: cmd in on the left at row 4, output out on the left at row 13,
    ring in on top at column 18, ring out on the right at row 5. Every ``r``
    and ``s`` below was placed so that nearest-pipe resolution is unambiguous
    (see :func:`probe_station_pipes`).
    """
    room = Room(13, 22)
    # --- prologue (off the main loop): send 34 zero words into the ring
    room.put(1, 1, "@`33`b0 >sv")
    room.put(2, 9, "^md")
    room.put(3, 11, "<")
    room.put(3, 2, "v")
    # --- main entry: r(tag) X
    room.put(4, 1, ">>rX")
    # READ (tag == 0, straight on): r(k) b r(43-shift) M(B=const)
    room.put(4, 5, "rbrM")
    room.put(4, 14, "v")
    room.put(5, 14, ">rsv")           # READ relay loop: relays k+1 words
    room.put(6, 14, "^ md")
    # READ decode, walked west: { M `43` W } ... s(output)
    room.put(7, 9, "}W`34`M{<")
    room.put(7, 2, "s")
    # WRITE (tag == 1): drop to row 8
    room.col(4, [5, 6], "v")
    room.put(8, 4, ">rX")             # r(k) X: k>0 turns down, k==0 goes on
    room.put(8, 7, "rM")              # k == 0: r(NOTMASK) M, then straight to the splice
    room.put(8, 20, "v")
    room.put(9, 6, ">bmrM")           # k > 0: BP=k-1, r(NOTMASK), M
    room.put(9, 14, ">rsv")           # WRITE relay loop: relays k words
    room.put(10, 14, "^ md")
    # splice, walked west: r(ring) & M ... r(nfP) | ; then east to s(ring)
    room.put(11, 20, "<")
    room.put(11, 14, "M&r<")          # walked west: r(ring) & M
    room.put(11, 3, "v|r")            # walked west: r(nfP) |
    room.put(12, 3, ">")
    room.put(12, 20, "sv")
    room.put(13, 21, "<")
    room.col(1, range(5, 14), "^")
    return room


def build_relay() -> Room:
    """Minimal always-on ring relay: 6 ticks per word."""
    # `@` sits off the lap: walking onto it is a nop, so a lap that re-entered
    # it would keep heading north into the wall.
    room = Room(2, 4)
    room.put(1, 1, "@>rv")
    room.put(2, 2, "^s<")
    return room


# --------------------------------------------------------------- assembly
# Room origins (top-left wall cell) on the shared canvas.
P1_AT = (0, 6)        # rows 0-4,   cols 6-34
HEAD_AT = (7, 6)      # rows 7-10,  cols 6-34
P2_AT = (13, 6)       # rows 13-19, cols 6-31
STATION_AT = (22, 6)  # rows 22-36, cols 6-29
RELAY_AT = (30, 31)   # rows 30-33, cols 31-36

# STATION pipe attachments, in the station's own interior coordinates.
STA_CMD_COL = 2      # top wall
STA_RINGOUT_ROW = 1  # right wall
STA_RINGIN_ROW = 2   # right wall
STA_OUT_ROW = 13     # left wall


def build_memory_packed() -> str:
    """Render the packed `memory_02` candidate."""
    cv = Canvas()
    st_r, st_c = STATION_AT
    st_right = st_c + 23    # station's right wall column

    cv.put(1, 0, ["+-+", "|I|", "+-+"])
    cv.put(*P1_AT, build_p1().render())
    cv.put(*HEAD_AT, build_head().render())
    cv.put(*P2_AT, build_p2().render())
    cv.put(*STATION_AT, build_station().render())
    cv.put(st_r + STA_OUT_ROW - 1, 0, ["+-+", "|O|", "+-+"])
    cv.put(*RELAY_AT, build_relay().render())

    # Command chain. P1, HEAD and P2 each have exactly one incoming and one
    # outgoing pipe, so no nearest-pipe resolution is involved along it.
    cv.pipe([(2, 3), (2, 5)])            # I -> P1 (left wall)
    cv.pipe([(5, 10), (6, 10)])          # P1 -> HEAD
    cv.pipe([(11, 10), (12, 10)])        # HEAD -> P2
    cv.pipe([(20, 8), (21, 8)])          # P2 -> STATION (top wall, col 2)

    # Output.
    cv.pipe([(st_r + STA_OUT_ROW, 5), (st_r + STA_OUT_ROW, 3)])

    # The ring: STATION -> RELAY -> STATION. The words have to park
    # somewhere, so the two pipes together must hold all 34 of them; the
    # outbound pipe therefore serpentines through the free column band
    # beside the station rather than taking the short route.
    ring_out_row = st_r + STA_RINGOUT_ROW
    ring_in_row = st_r + STA_RINGIN_ROW
    cv.pipe(
        [
            (ring_out_row, st_right + 1), (ring_out_row, 36),
            (26, 36), (26, 31), (28, 31), (28, 36), (29, 36), (29, 33),
        ]
    )
    cv.cells[(29, 33)] = "v"          # terminal bend into the relay's top wall
    cv.pipe([(34, 34), (35, 34), (35, 30), (ring_in_row, 30)])
    cv.cells[(ring_in_row, 30)] = "<"  # terminal bend into the station
    return cv.render()

