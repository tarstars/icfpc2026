"""LLLM FETCH station: the world-owner half of EXEC (work order claude_11a).

FETCH knows *nothing* about interpretation.  It owns the packed world and
answers the frozen claude_11a request grammar on one pipe:

* SETUP -- the first 64 tokens received are the packed world (claude_09
  format, four 13-bit records per token, little-endian, base 8192).  They
  are pushed into the private ring in order.
* ``0..255``   -- op fetch, ``addr = t``; respond ``class << 4 | value``.
* ``256..511`` -- colour fetch, ``addr = t - 256``; respond ``colour``.
* ``-1``       -- full stream; respond with 256 tokens, the colour of every
  cell in canvas order.

The world is READ-ONLY: every ring token is re-emitted unchanged and the
count of appends restores the canonical ring order (cookbook section 5).

:func:`fetch_reference` is the MODEL-FIRST deliverable -- the pure-Python
oracle every rig test is graded against.
"""

from __future__ import annotations

# ------------------------------------------------------- claude_09 grammar
RECORD_BITS = 13
RECORD_BASE = 1 << RECORD_BITS          # 8192
RECORDS_PER_TOKEN = 4
WORLD_TOKENS = 64
CELLS = WORLD_TOKENS * RECORDS_PER_TOKEN  # 256

FULL_STREAM = -1


def unpack_world(world: list[int]) -> list[int]:
    """The 64 packed tokens -> 256 raw records, canvas order."""
    if len(world) != WORLD_TOKENS:
        raise ValueError(f"world must be {WORLD_TOKENS} tokens, got {len(world)}")
    records: list[int] = []
    for token in world:
        rec = token
        for _ in range(RECORDS_PER_TOKEN):
            records.append(rec % RECORD_BASE)
            rec //= RECORD_BASE
    return records


# interior glyph -> (class, value, colour); identical to lllm_step.GLYPH so
# the two stations agree bit for bit on the claude_09 record layout.
CLASS_SPACE, CLASS_WALL = 0, 1
GLYPH = {
    " ": (0, 0, 0), "^": (2, 0, 3), ">": (2, 1, 3), "v": (2, 2, 3),
    "V": (2, 2, 3), "<": (2, 3, 3), "M": (4, 0, 12), "+": (5, 0, 10),
    "-": (6, 0, 10), "X": (7, 0, 3), "H": (8, 0, 3),
    **{d: (3, int(d), 8) for d in "0123456789"},
}
WALL_REC = 4 | (CLASS_WALL << 4) | (1 << 12)
DISPLAY = 16


def pack_world(rows: list[str]) -> tuple[list[int], int]:
    """Local claude_09 packer: 64 tokens plus ``man_addr`` (LOADER stand-in).

    Padding is space, the PROGRAM perimeter is wall whatever the glyph, and
    ``@`` is a space that yields ``man_addr``.  Cross-checked against
    ``lllm_step.pack_world`` in the tests.
    """
    height, width = len(rows), len(rows[0])
    recs: list[int] = []
    man_addr = 0
    for addr in range(CELLS):
        y, x = divmod(addr, DISPLAY)
        if y >= height or x >= width:
            recs.append(0)
        elif x in (0, width - 1) or y in (0, height - 1):
            recs.append(WALL_REC)
        else:
            ch = rows[y][x]
            if ch == "@":
                man_addr, ch = addr, " "
            cls, val, col = GLYPH.get(ch, (CLASS_SPACE, 0, 0))
            recs.append(col | (cls << 4) | (val << 8))
    tokens = [
        sum(recs[4 * j + i] << (RECORD_BITS * i) for i in range(RECORDS_PER_TOKEN))
        for j in range(WORLD_TOKENS)
    ]
    return tokens, man_addr


class Room:
    """A room built by explicit 1-indexed interior cell placement.

    Same helper shape as ``memory_packed.Room``: hand-drawn ASCII for a room
    this dense is unreadable, so every glyph is placed by coordinate and the
    walls are rendered afterwards.
    """

    def __init__(self, rows: int, cols: int):
        self.rows, self.cols = rows, cols
        self.cells: dict[tuple[int, int], str] = {}

    def put(self, row: int, col: int, text: str) -> None:
        """Write ``text`` rightwards from interior cell (row, col)."""
        for i, ch in enumerate(text):
            c = col + i
            if not (1 <= row <= self.rows and 1 <= c <= self.cols):
                raise ValueError(f"cell ({row},{c}) outside {self.rows}x{self.cols}")
            if (row, c) in self.cells and self.cells[(row, c)] != ch:
                raise ValueError(f"cell ({row},{c}) holds {self.cells[(row, c)]!r}")
            self.cells[(row, c)] = ch

    def render(self) -> list[str]:
        top = "+" + "-" * self.cols + "+"
        body = [
            "|" + "".join(self.cells.get((r, c), " ") for c in range(1, self.cols + 1))
            + "|"
            for r in range(1, self.rows + 1)
        ]
        return [top, *body, top]


# ------------------------------------------------------------ FETCH layout
FETCH_ROWS, FETCH_COLS = 23, 45

# CMD in / RESP out on the LEFT wall, both ring pipes on the RIGHT wall, so
# nearest-pipe resolution is a left/right split everywhere except the setup
# loop (which straddles, and is centred so both bindings still hold).
CMD_ROW, RESP_ROW = 2, 13          # left wall attachments
RING_OUT_ROW, RING_IN_ROW = 2, 5   # right wall attachments

# addr -> BP = word+2 and A = 2**(13*field), from A = addr, B = kind.
CHAIN = "WM8W+M4W/bWM`13`*M1{"
CHAIN_AT = 18                       # cols 18..37


def build_relay() -> Room:
    """Minimal always-on ring relay: 6 ticks per token (memory_04 pattern)."""
    room = Room(2, 4)
    room.put(1, 1, "@>rv")
    room.put(2, 2, "^s<")
    return room


def _fetch_setup(room: Room) -> None:
    """Rows 1-6: prologue, ring load, marker, and the MAIN dispatch."""
    # Prologue (off every lap): BP = 63, then fall into the setup relay.
    room.put(1, 1, "@ `63`b")   # offset so no backtick shares a column
    room.put(1, 20, "v")
    # Setup relay (post-test, BP=63 -> exactly 64 tokens CMD -> ring).
    room.put(2, 20, ">rsv")
    room.put(3, 20, "^ md")
    # The ring marker: one -1 behind the 64 world tokens.  Loop 2 and the
    # full stream relay until they see it, so no path needs a second count.
    room.put(4, 23, ">")
    room.put(4, 30, "1Nsv")
    room.put(5, 33, "<")
    room.put(5, 1, "v")
    # MAIN: park on a blocking r, then split -1 (full stream) from a fetch.
    # `M1W+` leaves A = req+1 and B = 1, so X sees 0 exactly for the -1.
    room.put(6, 1, ">rM1W+X")
    room.put(6, 45, "v")


def _fetch_decode(room: Room) -> None:
    """Rows 7-9: kind split, the two addressing chains, and their merge.

    ``M`256`W/`` leaves A = kind, B = addr in one divide.  Both chains are
    identical; the colour one only appends ``N`` so that B carries
    ``-2**(13*field)``.  That single packed word is the ONLY thing that has
    to survive the relay loop: its magnitude is the peel divisor and its
    sign is the request kind, recovered by one ``X`` on the far side.
    """
    room.put(7, 7, ">-M`256`W/X")
    room.put(7, CHAIN_AT, CHAIN)
    room.put(7, 44, "v")
    room.put(8, 17, ">")
    room.put(8, CHAIN_AT, CHAIN)
    room.put(8, 43, "Nv")
    room.put(9, 44, "M")          # merge: B = +/- 2**(13*field)


def _fetch_relay(room: Room) -> None:
    """Rows 10-12: the counted ring relay and the kind branch.

    Pre-test countdown with ``m`` on the entry row: BP = word+2 relays
    exactly word+1 tokens, zero included, and ``s`` never clobbers A -- so
    the loop falls out with the target token in A and the packed peel word
    still in B.
    """
    room.put(10, 44, "<")
    room.put(10, 37, "v")
    room.put(11, 37, ">m d")
    room.put(11, 41, "WX")      # A = packed word, B = target token
    room.put(12, 37, "^sr<")
    room.put(12, 42, "v")         # X clockwise: op fetch, tail on row 13


def _fetch_peels(room: Room) -> None:
    """The two response tails, walked WEST (literals written reversed).

    Colour (row 9): ``N W / M `15` &`` -- undo the sign, divide the token by
    ``2**(13*field)`` and mask the low nibble.

    Op (row 13): ``W / M `4080` & M `256` W / +``.  The window ``z & 0xFF0``
    is ``16*class + 256*value``, so one divide splits it into quotient
    ``value`` and remainder ``16*class`` and ``+`` fuses them into the
    frozen ``class<<4 | value`` -- no nibble swap anywhere.
    """
    room.put(9, 32, "&`51`M/WN <")
    room.put(9, 2, "vs")
    room.put(13, 23, "+/W`652`M&`0804`M/W<")
    room.put(13, 2, "vs")
    for r in range(10, 14):        # response chute down to the loop-2 lane
        room.put(r, 2, "v")


def _fetch_loop2(room: Room) -> None:
    """Rows 14-17: finish the rotation, marker-driven, then home to MAIN.

    Loop 1 left the ring rotated by ``word+1``; relaying until the marker
    comes round puts the marker back at the tail, so the canonical order is
    restored for ANY rotation and no second counter is ever needed.
    """
    room.put(14, 2, ">")
    room.put(14, 39, ">")
    room.put(14, 44, "v")
    room.put(15, 39, "^s<<")
    room.put(15, 44, "v")
    room.put(16, 41, "^Xr<")
    room.put(17, 41, "s<")        # marker seen: re-send it and go home
    for r in range(7, 19):        # the home corridor
        room.put(r, 1, "^")


def _fetch_stream(room: Room) -> None:
    """Rows 18-23: the ``-1`` full stream -- one rotation, four colours a lap.

    The outer lap is the same marker-driven relay as loop 2, so BP is free
    for the inner peel: ``3 b`` on the entry row, then a post-test loop that
    emits ``v & 15`` and shifts ``v >>= 13`` four times.
    """
    room.put(18, 39, "s<")         # marker: re-send it, then home
    room.put(19, 2, ">3b")
    room.put(19, 38, ">rXv")
    room.put(20, 2, "^")
    room.put(20, 3, "v")           # into the peel
    room.put(20, 39, "s<<")
    room.put(21, 2, "^>M`15`&sWM`13`W}dv")
    room.put(22, 2, "^^")
    room.put(22, 10, "m")
    room.put(22, 19, "<v")
    room.put(23, 2, "^")
    room.put(23, 20, "<")
    room.put(23, 45, "<")
    for r in range(7, 23):         # MAIN -> full stream chute
        room.put(r, 45, "v")


def build_fetch() -> Room:
    """The whole FETCH station."""
    room = Room(FETCH_ROWS, FETCH_COLS)
    _fetch_setup(room)
    _fetch_decode(room)
    _fetch_relay(room)
    _fetch_peels(room)
    _fetch_loop2(room)
    _fetch_stream(room)
    return room


def build_fetch_rig() -> str:
    """3x3 I -> FETCH + RELAY -> 3x3 O, ready for the simulator."""
    from .canvas import Canvas

    cv = Canvas()
    cv.put(0, 5, build_fetch().render())
    cv.put(20, 55, build_relay().render())
    cv.put(CMD_ROW - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(RESP_ROW - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(CMD_ROW, 3), (CMD_ROW, 4)])            # I -> FETCH
    cv.pipe([(RESP_ROW, 4), (RESP_ROW, 3)])          # FETCH -> O
    # The ring parks 65 tokens (64 world + marker) plus the relay man's own
    # hand, so the outbound leg serpentines to 51 cells: 70 together, tight
    # enough that the station rarely waits on a gap in the ring.
    cv.pipe([(RING_OUT_ROW, 52), (RING_OUT_ROW, 72), (21, 72), (21, 61)])
    cv.pipe([(21, 54), (21, 53), (RING_IN_ROW, 53), (RING_IN_ROW, 52)])
    return cv.render()


def rig_stream(world: list[int], requests: list[int]) -> list[int]:
    """The input the rig consumes: 64 world tokens then the requests."""
    return list(world) + list(requests)


def fetch_reference(world: list[int], requests: list[int]) -> list[int]:
    """Pure-Python oracle for the claude_11a request grammar."""
    records = unpack_world(world)
    out: list[int] = []
    for t in requests:
        if t == FULL_STREAM:
            out.extend(rec & 15 for rec in records)
        elif 0 <= t < CELLS:
            rec = records[t]
            out.append((((rec >> 4) & 15) << 4) | ((rec >> 8) & 15))
        elif CELLS <= t < 2 * CELLS:
            out.append(records[t - CELLS] & 15)
        else:
            raise ValueError(f"request {t} outside the claude_11a grammar")
    return out
