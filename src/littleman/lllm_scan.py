"""LLLM SCAN station: the geometry half of LOADER (work order A, claude_17).

SCAN is the ONLY room in the pipeline that ever knows ``W``, ``H`` or a
position.  It consumes ``W H c0 c1 ...`` on one pipe and emits, on one pipe:

* **256 cell tokens** in canvas order (``addr = y*16 + x``)::

      t = char + 256 * perimeter + 512 * padding

  ``char`` is the ASCII code; padding cells and the ``@`` cell both emit 32
  (space).  ``perimeter`` is 1 for ``x in {0, W-1}`` or ``y in {0, H-1}``,
  ``padding`` is 1 for ``x >= W`` or ``y >= H``.  The two bits are computed
  independently, exactly as the frozen interface states.
* **1 man token**: the canvas address of ``@`` (0..255).
* every later input token, relayed verbatim, forever.

Exactly 256 tokens are emitted whatever ``W*H`` is; an input char is
consumed only for a real cell.  :func:`scan_reference` is the model-first
oracle; :func:`build_scan_rig` is the room, graded against it.
"""

from __future__ import annotations

DISPLAY = 16
CELLS = DISPLAY * DISPLAY
SPACE = 32
PERIMETER_BIT = 256
PADDING_BIT = 512
AT = ord("@")

# ------------------------------------------------------------------ SCAN v2
# The LLM (not LLLM) contract.  Two changes, both forced by multi-room, multi-
# man programs, and BOTH additive: every v1 entry point below is untouched so
# `submissions/lllm/lllm_03.man` keeps rebuilding byte for byte.
#
# 1. WALLS ARE NO LONGER POSITIONAL.  An LLM program holds up to three rooms,
#    so an inner divider is a wall in the middle of the canvas while a cell on
#    the bounding box may be outside every room.  The rule validated against
#    `littleman.llm.LLM` on all 24 public programs (10 LLLM + 14 LLM) is:
#
#        wall(y, x)  <=>  ch == '|'
#                     or (ch in '+-' and (perimeter(y, x) or run))
#
#    where `run` is "every cell to my left on this row, back to x = 0, was
#    also a wall '+-'".  It is exact on all ten LLLM programs and on all four
#    pipe-free LLM programs; the only misses are rooms that touch neither
#    x == 0 nor the bounding box, which only occur in the pipe cases that are
#    out of scope.  Crucially `run` is a LEFT-TO-RIGHT scan state, so SCAN can
#    still stream a row without buffering it -- it is carried in the FSM's own
#    control flow (two copies of the interior-column loop), not in the ring.
#
# 2. UP TO THREE MEN.  Instead of one man token, three are emitted.  Missing
#    men report address 0, which is forced to be a wall cell (see below), so a
#    surplus interpreter freezes on tick 1 and never moves; the delta merger
#    then drops its man pixel by value alone (addr 0 * 16 + colour 9 == 9) and
#    keeps its restore pixel, which repaints cell 0 correctly.  No man count
#    has to travel down the pipeline at all.
MEN = 3
WALL_BIT = PERIMETER_BIT       # bit 8 is what CLASSIFY tests; only its
                               # DEFINITION changes, never its position
RUN_CHARS = (ord("+"), ord("-"))
BAR = ord("|")


def scan_reference_v2(tokens: list[int]) -> list[int]:
    """Model-first oracle for the v2 stream: 256 cells, 3 men, then relay.

    The men are reported most-recently-found first because the room shifts
    them along the ring (``MAN0 <- addr``, ``MAN1 <- MAN0``, ``MAN2 <- MAN1``)
    rather than indexing a slot by a count; order is irrelevant downstream.
    """
    width, height = tokens[0], tokens[1]
    chars = iter(tokens[2 : 2 + width * height])
    out: list[int] = []
    men = [0] * MEN
    for addr in range(CELLS):
        y, x = divmod(addr, DISPLAY)
        if x == 0:
            run = False
        if x >= width or y >= height:
            out.append(SPACE + PADDING_BIT)
            run = False
            continue
        char = next(chars)
        perimeter = x in (0, width - 1) or y in (0, height - 1)
        if char == AT:
            men = [addr] + men[: MEN - 1]
            char, wall = SPACE, False
        elif char == BAR:
            wall = True
        elif char in RUN_CHARS:
            wall = perimeter or run
        else:
            wall = False
        run = wall and char != BAR
        if addr == 0:
            wall = True          # the parking cell every surplus man starts on
        out.append(char + WALL_BIT * wall)
    return out + men + list(tokens[2 + width * height :])


def scan_reference(tokens: list[int]) -> list[int]:
    """Pure-Python oracle: 256 cell tokens, ``man_addr``, then the relay."""
    width, height = tokens[0], tokens[1]
    chars = iter(tokens[2 : 2 + width * height])
    out: list[int] = []
    man_addr = 0
    for addr in range(CELLS):
        y, x = divmod(addr, DISPLAY)
        padding = x >= width or y >= height
        perimeter = x in (0, width - 1) or y in (0, height - 1)
        if padding:
            char = SPACE
        else:
            char = next(chars)
            if char == AT:
                man_addr = addr
                char = SPACE
        out.append(char + PERIMETER_BIT * perimeter + PADDING_BIT * padding)
    return out + [man_addr] + list(tokens[2 + width * height :])


# --------------------------------------------------------------- FSM router
# Every block owns one lane of the room and is walked left to right.  A lane
# starts in its zone's column band, runs on to the shared branch column, and
# leaves through a per-edge vertical track.  Zones exist for two reasons:
# pipe binding (``left`` blocks are near the I/O wall, ``right`` blocks near
# the scratch-ring wall) and backtick safety -- every literal-bearing block
# sits in one of the two literal zones with its ticks column-aligned, so the
# vertical pairs the parser forms hold only spaces and digits.
LEFT_ZONES = {"lit_l": 3, "left": 14, "mid": 26}
RIGHT_ZONES = ("lit_r", "right")
ZONE_NAMES = (*LEFT_ZONES, *RIGHT_ZONES)
LITERAL_ZONES = ("lit_l", "lit_r")
LITERAL_DIGITS = 4          # every literal is written `dddd`, zero padded
TICK_OFFSET = 1             # so "M`0320`+" and " `0800`s" agree on columns


class _Fsm:
    """Blocks plus their successors; ``sign`` is the only branch shape."""

    def __init__(self) -> None:
        self.blocks: list[tuple[str, str, str, str, tuple[str, ...]]] = []

    def go(self, name: str, zone: str, code: str, target: str) -> None:
        self.blocks.append((name, zone, code, "goto", (target,)))

    def sign(
        self, name: str, zone: str, code: str, *, neg: str, zero: str, pos: str
    ) -> None:
        self.blocks.append((name, zone, code, "sign", (neg, zero, pos)))

    def bp(self, name: str, zone: str, code: str, *, zero: str, pos: str) -> None:
        """``d`` at the branch column: BP > 0 loops, BP <= 0 walks on."""
        self.blocks.append((name, zone, code, "bp", (zero, pos)))

    def check(self) -> None:
        names = [b[0] for b in self.blocks]
        if len(set(names)) != len(names):
            raise ValueError("duplicate block name")
        known = set(names)
        for name, zone, code, _kind, targets in self.blocks:
            if zone not in ZONE_NAMES:
                raise ValueError(f"{name}: unknown zone {zone}")
            if ("`" in code) != (zone in LITERAL_ZONES):
                raise ValueError(f"{name}: literal/zone mismatch")
            if "`" in code and code.index("`") != TICK_OFFSET:
                raise ValueError(f"{name}: literal not column aligned")
            for target in targets:
                if target not in known:
                    raise ValueError(f"{name}: unknown target {target}")


# Which rows a branch leaves from, relative to the block's own row.  ``X``
# sends A>0 clockwise (down when walking right) and A<0 counter-clockwise
# (up); ``d`` sends BP>0 down and lets BP<=0 walk straight on.
ARMS = {
    "goto": ((0, "goto"),),
    "sign": ((-1, "neg"), (0, "zero"), (1, "pos")),
    "bp": ((0, "zero"), (1, "pos")),
}
BAND = {"goto": 2, "sign": 4, "bp": 3}
BLOCK_OFFSET = {"goto": 1, "sign": 2, "bp": 1}


def _layout(fsm: _Fsm):
    """Assign each block a route row and a block row, top to bottom."""
    route_rows: dict[str, int] = {}
    block_rows: dict[str, int] = {}
    next_row = 2
    for name, _zone, _code, kind, _targets in fsm.blocks:
        route_rows[name] = next_row
        block_rows[name] = next_row + BLOCK_OFFSET[kind]
        next_row += BAND[kind]
    return route_rows, block_rows, next_row


def _tracks(fsm: _Fsm, route_rows, block_rows):
    """Give every edge a column; two edges share one only if they never
    overlap vertically, or if they run the same way into the same block."""
    spans = []
    for name, _zone, _code, kind, targets in fsm.blocks:
        for (offset, label), target in zip(ARMS[kind], targets, strict=True):
            source = block_rows[name] + offset
            route = route_rows[target]
            spans.append(
                (
                    min(source, route),
                    max(source, route),
                    name,
                    label,
                    target,
                    "down" if route > source else "up",
                )
            )
    tracks: list[list[tuple[int, int, str, str]]] = []
    column: dict[tuple[str, str], int] = {}
    for lo, hi, name, label, target, way in sorted(spans):
        index = next(
            (
                i
                for i, members in enumerate(tracks)
                if all(
                    mhi < lo or hi < mlo or (mt == target and mw == way)
                    for mlo, mhi, mt, mw in members
                )
            ),
            len(tracks),
        )
        if index == len(tracks):
            tracks.append([])
        tracks[index].append((lo, hi, target, way))
        column[(name, label)] = index
    return column, len(tracks)


def _columns(tracks: int) -> tuple[dict[str, int], int, int]:
    """Place the column bands once the track count is known.

    The ring pipes hang off the right wall and the I/O pipes off the left,
    so nearest-pipe resolution is a pure left/right split -- but the edge
    tracks widen the room on the right, pushing the midline outwards.  The
    gap before the ring zones therefore grows with the track count, which
    keeps every ring op strictly right of the midline.
    """
    gap = 52 + tracks
    zones = dict(LEFT_ZONES, lit_r=gap - 20, right=gap)
    branch = gap + 14
    return zones, branch, branch + 2


def _compile(fsm: _Fsm) -> list[str]:
    """Render the whole FSM as one room, walls included."""
    fsm.check()
    route_rows, block_rows, height = _layout(fsm)
    edge_track, tracks = _tracks(fsm, route_rows, block_rows)
    zones, branch_col, edge_base = _columns(tracks)
    zone_of = {block[0]: block[1] for block in fsm.blocks}
    width = edge_base + tracks + 2
    grid = [[" "] * (width + 2) for _ in range(height + 2)]
    for c in range(width + 2):
        grid[0][c] = grid[height + 1][c] = "-"
    for r in range(height + 2):
        grid[r][0] = grid[r][width + 1] = "|"
    for r, c in ((0, 0), (0, width + 1), (height + 1, 0), (height + 1, width + 1)):
        grid[r][c] = "+"

    def put(row: int, col: int, char: str) -> None:
        old_char = grid[row][col]
        if old_char not in (" ", char):
            raise ValueError(f"collision at ({row},{col}): {old_char!r}/{char!r}")
        grid[row][col] = char

    for name, zone, code, kind, targets in fsm.blocks:
        row, start = block_rows[name], zones[zone]
        put(row, start - 1, ">")
        for offset, char in enumerate(code):
            if char != " ":
                put(row, start + offset, char)
        if kind != "goto":
            put(row, branch_col, "X" if kind == "sign" else "d")
        for (offset, label), target in zip(ARMS[kind], targets, strict=True):
            if offset:
                put(row + offset, branch_col, ">")
            arm_row = row + offset
            edge = edge_base + edge_track[(name, label)]
            route, entry = route_rows[target], zones[zone_of[target]] - 1
            put(arm_row, edge, "v" if route > arm_row else "^")
            put(route, edge, "<")
            for between in range(route, block_rows[target]):
                put(between, entry, "v")
            put(block_rows[target], entry, ">")
    return ["".join(row) for row in grid]


# ------------------------------------------------------------- the SCAN FSM
# The private scratch ring holds five tokens in this canonical order.  Every
# path that touches it consumes and re-appends all five, so the order is an
# invariant of every block boundary (cookbook section 5).
RING = ("ADDR", "MAN", "W", "NPAD", "RC")
LAP = "rs" * len(RING)          # a full rotation that changes nothing
FETCH_W = "rsrsrMsrsrs"         # ...but leaves B = W on the way past slot 3


def _prologue(fsm: _Fsm, first_row: str) -> None:
    """Read ``W`` and ``H`` and seed the ring with ADDR, MAN, W, NPAD, RC.

    ``W`` is pushed straight through B before any literal can clobber it,
    and both row counts are derived from H while B still holds H: ``NPAD``
    is the number of padding rows ``16 - H`` and ``RC`` the number of
    interior rows ``H - 2``.
    """
    fsm.go("boot", "left", "@rM", "seed_w")
    fsm.go("seed_w", "right", "0s0s0+s", "read_h")
    fsm.go("read_h", "left", "r", "seed_npad")
    fsm.go("seed_npad", "lit_l", "M`0016`-", "push_npad")
    fsm.go("push_npad", "right", "s0+", "seed_rc")
    fsm.go("seed_rc", "lit_l", "M`0002`W-", "push_rc")
    fsm.go("push_rc", "right", "s", first_row)


def _row_pad(fsm: _Fsm, tag: str, after: str) -> None:
    """One wholly padding row: ``800 544*(W-2) 800 544*(16-W)``, no input.

    Nothing is read, so ``@`` cannot appear and ADDR only needs the bulk
    ``+16`` at the end of the row.
    """
    fsm.go(f"{tag}_w", "right", FETCH_W, f"{tag}_bp")
    fsm.go(f"{tag}_bp", "mid", "0+bmm", f"{tag}_x0")
    fsm.go(f"{tag}_x0", "lit_l", " `0800`s", f"{tag}_mid")
    fsm.go(f"{tag}_mid", "lit_l", " `0544`s", f"{tag}_lp")
    fsm.bp(f"{tag}_lp", "mid", "m", zero=f"{tag}_xw", pos=f"{tag}_mid")
    fsm.go(f"{tag}_xw", "lit_l", " `0800`s", f"{tag}_w2")
    fsm.go(f"{tag}_w2", "right", FETCH_W, f"{tag}_lw")
    fsm.go(f"{tag}_lw", "mid", "0+", f"{tag}_bp4")
    fsm.go(f"{tag}_bp4", "lit_l", "M`0016`W-N", f"{tag}_seed4")
    fsm.go(f"{tag}_seed4", "mid", "Mb", f"{tag}_p4")
    fsm.bp(f"{tag}_p4", "mid", "", zero=f"{tag}_end", pos=f"{tag}_tail")
    fsm.go(f"{tag}_tail", "lit_l", " `0544`s", f"{tag}_step")
    fsm.go(f"{tag}_step", "mid", "m", f"{tag}_p4")
    fsm.go(f"{tag}_end", "right", "rM", f"{tag}_bump")
    fsm.go(f"{tag}_bump", "lit_r", " `0016`+s" + "rs" * 4, after)


def _cell_bump(fsm: _Fsm, tag: str, after: str) -> None:
    """``ADDR += 1`` in one rotation, for a cell that read a real char."""
    fsm.go(f"{tag}_a", "right", "rM", f"{tag}_b")
    fsm.go(f"{tag}_b", "lit_r", " `0001`+s" + "rs" * 4, after)


def _edge_cell(fsm: _Fsm, tag: str, after: str) -> None:
    """One program-border column: emit ``char + 256``.

    A border cell is a wall in any real LLLM program, but ``@`` is still
    decoded here so the room matches the oracle for any input at all.
    """
    fsm.go(f"{tag}_r", "left", "r", f"{tag}_at")
    fsm.sign(
        f"{tag}_at",
        "lit_l",
        "M`0064`W-",
        neg=f"{tag}_t",
        zero=f"{tag}_m",
        pos=f"{tag}_t",
    )
    fsm.go(f"{tag}_t", "lit_l", "M`0320`+s", f"{tag}_a")
    _cell_bump(fsm, tag, after)
    fsm.go(f"{tag}_m", "lit_l", " `0288`s", f"{tag}_mb")
    fsm.go(f"{tag}_mb", "right", "rM", f"{tag}_mc")
    fsm.go(f"{tag}_mc", "lit_r", " `0001`+sr0+s" + "rs" * 3, after)


def _row_real(fsm: _Fsm, tag: str, perimeter: int, after: str) -> None:
    """One row of the program: border columns, interior columns, padding.

    ``perimeter`` is 256 on the top and bottom program rows and 0 between,
    and is the whole difference between the two kinds of real row.  The
    interior span is the only place a char can be ``@``; its cell emits a
    plain space and copies ADDR into MAN in the same rotation.
    """
    fsm.go(f"{tag}_w", "right", FETCH_W, f"{tag}_bp")
    fsm.go(f"{tag}_bp", "mid", "0+bmm", f"{tag}_x0_r")
    _edge_cell(fsm, f"{tag}_x0", f"{tag}_c")
    # interior columns x = 1 .. W-2, run W-2 times by the BP countdown
    fsm.go(f"{tag}_c", "left", "r", f"{tag}_at")
    fsm.sign(
        f"{tag}_at",
        "lit_l",
        "M`0064`W-",
        neg=f"{tag}_n",
        zero=f"{tag}_m",
        pos=f"{tag}_n",
    )
    fsm.go(f"{tag}_n", "lit_l", f"M`{64 + perimeter:04d}`+s", f"{tag}_nb_a")
    _cell_bump(fsm, f"{tag}_nb", f"{tag}_lp")
    fsm.go(f"{tag}_m", "lit_l", f" `{32 + perimeter:04d}`s", f"{tag}_mb")
    fsm.go(f"{tag}_mb", "right", "rM", f"{tag}_mc")
    fsm.go(f"{tag}_mc", "lit_r", " `0001`+sr0+s" + "rs" * 3, f"{tag}_lp")
    fsm.bp(f"{tag}_lp", "mid", "m", zero=f"{tag}_xw_r", pos=f"{tag}_c")
    _edge_cell(fsm, f"{tag}_xw", f"{tag}_w2")
    # padding columns x = W .. 15, and the bulk ADDR step over them
    fsm.go(f"{tag}_w2", "right", FETCH_W, f"{tag}_lw")
    fsm.go(f"{tag}_lw", "mid", "0+", f"{tag}_bp4")
    fsm.go(f"{tag}_bp4", "lit_l", "M`0016`W-N", f"{tag}_seed4")
    fsm.go(f"{tag}_seed4", "mid", "Mb", f"{tag}_p4")
    fsm.bp(f"{tag}_p4", "mid", "", zero=f"{tag}_end", pos=f"{tag}_tail")
    fsm.go(f"{tag}_tail", "lit_l", f" `{544 + perimeter:04d}`s", f"{tag}_step")
    fsm.go(f"{tag}_step", "mid", "m", f"{tag}_p4")
    fsm.go(f"{tag}_end", "right", "r+s" + "rs" * 4, after)


def _build_scan_fsm() -> _Fsm:
    """The whole station: one border row, the interior rows, the last
    border row, the padding rows, the man token, then an endless relay.

    Both row loops read their count out of the ring, push the decrement
    back in the same rotation, and branch on the value they read, so the
    ring order is restored whether the loop runs again or falls out.
    """
    fsm = _Fsm()
    _prologue(fsm, "top_w")
    _row_real(fsm, "top", PERIMETER_BIT, "ilp_a")
    fsm.go("ilp_a", "right", LAP[:-1] + "M", "ilp_b")
    fsm.go("ilp_b", "lit_r", " `0001`W-s", "ilp_c")
    fsm.sign("ilp_c", "mid", "", neg="bot_w", zero="mid_w", pos="mid_w")
    _row_real(fsm, "mid", 0, "ilp_a")
    _row_real(fsm, "bot", PERIMETER_BIT, "plp_a")
    fsm.go("plp_a", "right", "rsrsrsrM", "plp_b")
    fsm.go("plp_b", "lit_r", " `0001`W-sMrs", "plp_c")
    fsm.sign("plp_c", "mid", "0+", neg="tail_a", zero="pad_w", pos="pad_w")
    _row_pad(fsm, "pad", "plp_a")
    fsm.go("tail_a", "right", "rsr", "tail_b")
    fsm.go("tail_b", "left", "s", "relay")
    fsm.go("relay", "left", "rs", "relay")
    return fsm


def build_scan_room() -> list[str]:
    """The SCAN room as rendered ASCII rows, walls included."""
    return _compile(_build_scan_fsm())


def build_relay() -> list[str]:
    """The scratch ring's relay room (the memory_04 / FETCH pattern)."""
    return ["+----+", "|@>rv|", "| ^s<|", "+----+"]


# --------------------------------------------------------- the v2 SCAN room
# Seven slots instead of five: the one man token becomes three, and the wall
# run needs no slot at all because it is carried in the FSM's control flow.
RING2 = ("ADDR", "W", "NPAD", "RC", "MAN0", "MAN1", "MAN2")
N2 = len(RING2)
# W lives at slot 1 now, so the "leave W in B" rotation is a different tape;
# it is 15 cells long and the `right` zone only holds 14, hence two blocks.
FETCH_W2 = ("rsrMs" + "rs" * 3, "rs" * 2)


def _bump2(fsm: _Fsm, tag: str, step: int, after: str) -> None:
    """``ADDR += step`` in one seven-slot rotation."""
    fsm.go(f"{tag}_a", "right", "rM", f"{tag}_b")
    fsm.go(f"{tag}_b", "lit_r", " `%04d`+s" % step + "rs" * 5, f"{tag}_c")
    fsm.go(f"{tag}_c", "right", "rs", after)


def _at_bump2(fsm: _Fsm, tag: str, after: str) -> None:
    """``ADDR += 1`` and shift ADDR into MAN0, MAN0 into MAN1, MAN1 into MAN2.

    ``W`` is the whole trick: at each man slot ``r`` loads the old occupant
    into A and ``W`` swaps it with the value queued in B, so one pass writes
    the new value and picks up the displaced one for the next slot.
    """
    fsm.go(f"{tag}_a", "right", "rM", f"{tag}_b")
    fsm.go(f"{tag}_b", "lit_r", " `0001`+s" + "rs" * 3, f"{tag}_c")
    fsm.go(f"{tag}_c", "right", "rWs" * MEN, after)


def _glyph_tests(fsm: _Fsm, tag: str, at: bool, targets: dict[str, str]) -> None:
    """Read one char and fan out on its glyph; A holds the char at every exit.

    Each test is ``M`code`W-``, which leaves ``A = char - code`` and
    ``B = code`` -- the swap puts the CODE in B, not the char -- so a miss
    arm restores the char with a single ``+``, and a hit arm has ``A = 0``
    and emits a compile-time constant instead.
    """
    codes = [(64, "at"), (BAR, "bar"), (RUN_CHARS[0], "plus"), (RUN_CHARS[1], "minus")]
    if not at:
        codes = codes[1:]
    fsm.go(f"{tag}_r", "left", "r", f"{tag}_t0")
    for index, (code, label) in enumerate(codes):
        name, miss = f"{tag}_t{index}", f"{tag}_m{index}"
        fsm.sign(name, "lit_l", "M`%04d`W-" % code,
                 neg=miss, zero=targets[label], pos=miss)
        last = index + 1 == len(codes)
        fsm.go(miss, "left", "+",
               targets["other"] if last else f"{tag}_t{index + 1}")


def _cell2(fsm: _Fsm, tag: str, *, at: bool, wall: bool, run: str, nxt: str) -> None:
    """One program cell: emit its token, bump ADDR, choose the next state.

    ``wall`` says whether a ``+``/``-`` HERE is a wall -- true on the bounding
    box and inside a live run, false otherwise.  When it is, the cell leaves
    for ``run`` (the run continues); every other glyph leaves for ``nxt``,
    because ``|`` is a wall that does NOT continue a horizontal run and
    nothing else is a wall at all.
    """
    labels = ("bar", "plus", "minus", "other") + (("at",) if at else ())
    targets = {label: f"{tag}_e{label}" for label in labels}
    _glyph_tests(fsm, tag, at, targets)
    if at:
        fsm.go(f"{tag}_eat", "lit_l", " `%04d`s" % SPACE, f"{tag}_katb_a")
        _at_bump2(fsm, f"{tag}_katb", nxt)
    fsm.go(f"{tag}_ebar", "lit_l", " `%04d`s" % (BAR + WALL_BIT), f"{tag}_kbar_a")
    _bump2(fsm, f"{tag}_kbar", 1, nxt)
    for label, char in (("plus", RUN_CHARS[0]), ("minus", RUN_CHARS[1])):
        value = char + WALL_BIT * wall
        fsm.go(f"{tag}_e{label}", "lit_l", " `%04d`s" % value, f"{tag}_k{label}_a")
        _bump2(fsm, f"{tag}_k{label}", 1, run if wall else nxt)
    fsm.go(f"{tag}_eother", "left", "s", f"{tag}_koth_a")
    _bump2(fsm, f"{tag}_koth", 1, nxt)


def _pad_tail2(fsm: _Fsm, tag: str, after: str) -> None:
    """Columns ``x >= W`` of a real row: ``16 - W`` space tokens, one bump."""
    fsm.go(f"{tag}_pw", "right", FETCH_W2[0], f"{tag}_pw2")
    fsm.go(f"{tag}_pw2", "right", FETCH_W2[1], f"{tag}_lw")
    fsm.go(f"{tag}_lw", "mid", "0+", f"{tag}_bp4")
    fsm.go(f"{tag}_bp4", "lit_l", "M`0016`W-N", f"{tag}_seed4")
    fsm.go(f"{tag}_seed4", "mid", "Mb", f"{tag}_p4")
    fsm.bp(f"{tag}_p4", "mid", "", zero=f"{tag}_end", pos=f"{tag}_ptail")
    fsm.go(f"{tag}_ptail", "lit_l", " `%04d`s" % (SPACE + PADDING_BIT), f"{tag}_pstep")
    fsm.go(f"{tag}_pstep", "mid", "m", f"{tag}_p4")
    fsm.go(f"{tag}_end", "right", "r+s" + "rs" * 5, f"{tag}_end2")
    fsm.go(f"{tag}_end2", "right", "rs", after)


def _row_pad2(fsm: _Fsm, tag: str, after: str) -> None:
    """A wholly padding row ``y >= H``: sixteen space tokens, one bump."""
    fsm.go(f"{tag}_seed", "lit_l", " `%04d`b" % DISPLAY, f"{tag}_p")
    fsm.bp(f"{tag}_p", "mid", "", zero=f"{tag}_done_a", pos=f"{tag}_t")
    fsm.go(f"{tag}_t", "lit_l", " `%04d`s" % (SPACE + PADDING_BIT), f"{tag}_st")
    fsm.go(f"{tag}_st", "mid", "m", f"{tag}_p")
    _bump2(fsm, f"{tag}_done", DISPLAY, after)


def _row_perim2(fsm: _Fsm, tag: str, top: bool, after: str) -> None:
    """A row of the bounding box: every ``+``/``-``/``|`` on it is a wall."""
    fsm.go(f"{tag}_w", "right", FETCH_W2[0], f"{tag}_w2")
    fsm.go(f"{tag}_w2", "right", FETCH_W2[1], f"{tag}_bp")
    fsm.go(f"{tag}_bp", "mid", "0+bmm", f"{tag}_z_r" if top else f"{tag}_x0_r")
    if top:
        # Cell 0 is where every surplus interpreter parks, so it is forced to
        # be a wall whatever glyph sits there; it is a room corner in all 24
        # public programs, so the force is only ever a no-op in practice.
        fsm.go(f"{tag}_z_r", "left", "r", f"{tag}_z_e")
        fsm.go(f"{tag}_z_e", "lit_l", "M`%04d`+s" % WALL_BIT, f"{tag}_kz_a")
        _bump2(fsm, f"{tag}_kz", 1, f"{tag}_c_r")
    else:
        _cell2(fsm, f"{tag}_x0", at=False, wall=True,
               run=f"{tag}_c_r", nxt=f"{tag}_c_r")
    _cell2(fsm, f"{tag}_c", at=False, wall=True, run=f"{tag}_lp", nxt=f"{tag}_lp")
    fsm.bp(f"{tag}_lp", "mid", "m", zero=f"{tag}_xw_r", pos=f"{tag}_c_r")
    _cell2(fsm, f"{tag}_xw", at=False, wall=True, run=f"{tag}_pw", nxt=f"{tag}_pw")
    _pad_tail2(fsm, tag, after)


def _row_mid2(fsm: _Fsm, tag: str, after: str) -> None:
    """An interior row: two copies of the column loop, one per run state.

    The wall run is FSM state, not memory.  ``_run`` cells treat ``+``/``-``
    as walls and stay in the run; ``_nor`` cells treat them as arithmetic and
    can never re-enter it, which is exactly the left-to-right rule.
    """
    fsm.go(f"{tag}_w", "right", FETCH_W2[0], f"{tag}_w2")
    fsm.go(f"{tag}_w2", "right", FETCH_W2[1], f"{tag}_bp")
    fsm.go(f"{tag}_bp", "mid", "0+bmm", f"{tag}_x0_r")
    _cell2(fsm, f"{tag}_x0", at=False, wall=True,
           run=f"{tag}_run_r", nxt=f"{tag}_nor_r")
    _cell2(fsm, f"{tag}_run", at=True, wall=True,
           run=f"{tag}_rlp", nxt=f"{tag}_nlp")
    _cell2(fsm, f"{tag}_nor", at=True, wall=False,
           run=f"{tag}_nlp", nxt=f"{tag}_nlp")
    fsm.bp(f"{tag}_rlp", "mid", "m", zero=f"{tag}_xw_r", pos=f"{tag}_run_r")
    fsm.bp(f"{tag}_nlp", "mid", "m", zero=f"{tag}_xw_r", pos=f"{tag}_nor_r")
    _cell2(fsm, f"{tag}_xw", at=False, wall=True, run=f"{tag}_pw", nxt=f"{tag}_pw")
    _pad_tail2(fsm, tag, after)


def _prologue2(fsm: _Fsm, first_row: str) -> None:
    """Read ``W`` and ``H``; seed ADDR, W, NPAD, RC and three empty men."""
    fsm.go("boot", "left", "@rM", "seed_a")
    fsm.go("seed_a", "right", "0s0+s", "read_h")
    fsm.go("read_h", "left", "r", "seed_npad")
    fsm.go("seed_npad", "lit_l", "M`0016`-", "push_npad")
    fsm.go("push_npad", "right", "s0+", "seed_rc")
    fsm.go("seed_rc", "lit_l", "M`0002`W-", "push_rc")
    fsm.go("push_rc", "right", "s0" + "s" * MEN, first_row)


def _build_scan_fsm_v2() -> _Fsm:
    """Top row, the interior rows, the bottom row, the padding rows, the
    three man tokens, then an endless relay."""
    fsm = _Fsm()
    _prologue2(fsm, "top_w")
    _row_perim2(fsm, "top", True, "ilp_a")
    fsm.go("ilp_a", "right", "rsrsrsrM", "ilp_b")
    fsm.go("ilp_b", "lit_r", " `0001`W-s", "ilp_c")
    fsm.go("ilp_c", "right", "M" + "rs" * 3, "ilp_d")
    fsm.sign("ilp_d", "mid", "0+", neg="bot_w", zero="mid_w", pos="mid_w")
    _row_mid2(fsm, "mid", "ilp_a")
    _row_perim2(fsm, "bot", False, "plp_a")
    fsm.go("plp_a", "right", "rsrsrM", "plp_b")
    fsm.go("plp_b", "lit_r", " `0001`W-s", "plp_c")
    fsm.go("plp_c", "right", "M" + "rs" * 4, "plp_d")
    fsm.sign("plp_d", "mid", "0+", neg="tail_a", zero="pad_seed", pos="pad_seed")
    _row_pad2(fsm, "pad", "plp_a")
    fsm.go("tail_a", "right", "rs" * 4, "tail_r0")
    for index in range(MEN):
        last = index + 1 == MEN
        fsm.go(f"tail_r{index}", "right", "r", f"tail_s{index}")
        fsm.go(f"tail_s{index}", "left", "s",
               "relay" if last else f"tail_r{index + 1}")
    fsm.go("relay", "left", "rs", "relay")
    return fsm


def build_scan_room_v2() -> list[str]:
    """The v2 SCAN room as rendered ASCII rows, walls included."""
    return _compile(_build_scan_fsm_v2())


def build_scan_rig_v2() -> str:
    """``3x3 I -> SCAN v2 -> 3x3 O`` plus the seven-slot scratch ring."""
    from .canvas import Canvas

    room = build_scan_room_v2()
    right = SCAN_LEFT + len(room[0]) - 1
    cv = Canvas()
    cv.put(0, SCAN_LEFT, room)
    cv.put(CMD_ROW - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(RESP_ROW - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(CMD_ROW, 3), (CMD_ROW, SCAN_LEFT - 1)])
    cv.pipe([(RESP_ROW, SCAN_LEFT - 1), (RESP_ROW, 3)])
    relay_left = right + 5
    cv.put(1, relay_left, build_relay())
    cv.pipe([(RING_OUT_ROW, right + 1), (RING_OUT_ROW, relay_left - 1)])
    # Seven tokens now park in the return leg, not five, so it is longer.
    far = relay_left + 12
    cv.pipe([(3, relay_left + 6), (3, far), (RING_IN_ROW, far),
             (RING_IN_ROW, right + 1)])
    return cv.render()


# ------------------------------------------------------------------- the rig
SCAN_LEFT = 5                 # the room's own column 1 lands at canvas 6
CMD_ROW, RESP_ROW = 2, 6      # I -> SCAN, SCAN -> O, on the left wall
RING_OUT_ROW, RING_IN_ROW = 2, 9   # SCAN <-> relay, on the right wall


def build_scan_rig() -> str:
    """``3x3 I -> SCAN -> 3x3 O`` plus the private scratch ring."""
    from .canvas import Canvas

    room = build_scan_room()
    right = SCAN_LEFT + len(room[0]) - 1
    cv = Canvas()
    cv.put(0, SCAN_LEFT, room)
    cv.put(CMD_ROW - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(RESP_ROW - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(CMD_ROW, 3), (CMD_ROW, SCAN_LEFT - 1)])
    cv.pipe([(RESP_ROW, SCAN_LEFT - 1), (RESP_ROW, 3)])
    relay_left = right + 5
    cv.put(1, relay_left, build_relay())
    cv.pipe([(RING_OUT_ROW, right + 1), (RING_OUT_ROW, relay_left - 1)])
    # The return leg is long on purpose: all five ring tokens park in it, so
    # a rotation never waits on a gap between them.
    far = relay_left + 8
    cv.pipe(
        [
            (3, relay_left + 6),
            (3, far),
            (RING_IN_ROW, far),
            (RING_IN_ROW, right + 1),
        ]
    )
    return cv.render()
