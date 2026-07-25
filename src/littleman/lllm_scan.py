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
