"""SCAN v3: room-shaped model of the pinned LLM machine_stream contract.

Chain of 1-in/1-out stream rooms (cookbook section 4's most reliable
pattern), each function here the exact algorithm its room will run:

  S1  = build_scan_room_v2() VERBATIM: 256 cell tokens (char + heuristic
        wall bit + padding bit), 3 man addrs (0 = absent), then relay.
  P1  = controller + memory subsystem (memory.py's P3W/P3R/RELAY ring,
        grown to N = 312 slots: 256 cells, 3 men, room/candidate/pipe
        state).  Ingest strips the heuristic wall bit per cell
        (t%256 + 512*(t>>9)); find_rooms walks cells by address; wall
        pokes are fused into room acceptance (field := char + 256);
        then man->room, pipe-head candidates, traces, descriptors; the
        emit phase drains 256 corrected fields, men, count and
        descriptors, then relays every later token forever.  Every
        memory access is an op plus a dummy WRITE to pad slot N-2 so
        the ring always rotates one full lap: the head position is an
        invariant and reads never emit junk.
  S2  = packer: the first 256 stream values are packed 4 per word in
        13-bit fields (64 words out); everything after is relayed.

Every stage keeps state within its room's scratch budget (asserted via
the CAP constants) and touches values only in ways A/B/ring FIFOs can.
find_rooms runs on the space-padded 16x16 canvas, which is equivalent
to running it on the true WxH grid: padding is all spaces, so every
run/corner probe fails at the boundary exactly as the bounds check
would.  The nested-candidate drop is asserted to be a no-op (interiors
cannot contain `|`, so a candidate can never nest inside another in a
valid program) and the room therefore omits it.
"""

from __future__ import annotations

from .lllm_scan import scan_reference_v2

FIELD = 8192          # 2**13, one packed cell field
CHAR = 256            # char lives in bits 0-7 of a field
WALL = 256            # wall bit inside a field
ROWS = 16
WORDS = 64
MEN = 3
DR = (-1, 0, 1, 0)    # 0=N 1=E 2=S 3=W, clockwise (llm_lockstep order)
DC = (0, 1, 0, -1)
ARROW_CODE = {94: 0, 62: 1, 118: 2, 60: 3}     # ^ > v <
PROBE = {0: 0, 2: 1, 3: 2, 1: 3}               # dir -> N,S,W,E probe rank
CAND_CAP = 8          # pipe-head candidate slots in P1
SENT_KEY = 1 << 14    # sorts after every real candidate key


def pack64(stream: list[int]) -> list[int]:
    """S2: pack the first 256 fields 4 per word, relay the rest."""
    out = [
        sum(stream[4 * w + k] * FIELD**k for k in range(4))
        for w in range(WORDS)
    ]
    return out + stream[4 * WORDS:]


def p1_rooms(words: list[int]) -> list[tuple[int, int, int, int]]:
    """find_rooms via the P1 read primitive, walk-for-walk.

    Candidate scan order is reading order of the `+` top-left corner;
    the right run stops at the first non-`-`, the down run at the first
    non-`|`, and both must land on `+` at distance >= 2; then the far
    corner, bottom `-` run and right `|` column are validated.
    """
    rooms = []
    for r in range(ROWS):
        for c in range(ROWS):
            if _char(words, r * 16 + c) != 43:
                continue
            c2 = c + 1
            while c2 < ROWS and _char(words, r * 16 + c2) == 45:
                c2 += 1
            if c2 >= ROWS or c2 == c + 1 or _char(words, r * 16 + c2) != 43:
                continue
            r2 = r + 1
            while r2 < ROWS and _char(words, r2 * 16 + c) == 124:
                r2 += 1
            if r2 >= ROWS or r2 == r + 1 or _char(words, r2 * 16 + c) != 43:
                continue
            if _char(words, r2 * 16 + c2) != 43:
                continue
            if any(_char(words, r2 * 16 + x) != 45 for x in range(c + 1, c2)):
                continue
            if any(_char(words, y * 16 + c2) != 124 for y in range(r + 1, r2)):
                continue
            rooms.append((r, c, r2, c2))
    assert len(rooms) <= 3, "more than three rooms"
    for i, a in enumerate(rooms):                # find_rooms' nested drop:
        for j, b in enumerate(rooms):            # must be a no-op, or the
            if i != j:                           # room transcription breaks
                assert not (b[0] <= a[0] and b[1] <= a[1]
                            and b[2] >= a[2] and b[3] >= a[3]), "nested room"
    return rooms


def _contains(rm, r, c):
    return rm[0] <= r <= rm[2] and rm[1] <= c <= rm[3]


def _on_border(rm, r, c):
    return _contains(rm, r, c) and (r in (rm[0], rm[2]) or c in (rm[1], rm[3]))


def _char(cells, addr):
    return cells[addr] % CHAR


def _poke_wall(cells, addr):
    """Idempotent: field := char + WALL (frame cells are never padding)."""
    cells[addr] = cells[addr] % CHAR + WALL


def p1_stream(stream: list[int]) -> list[int]:
    """Rooms, walls, man rooms, pipe discovery, emission, relay.

    Input is the raw v2 stream; the ingest strip is the room's exact
    per-token formula  t % 256 + 512 * (t >> 9).
    """
    words = [t % CHAR + 512 * (t >> 9) for t in stream[: 4 * WORDS]]
    men = stream[4 * WORDS : 4 * WORDS + MEN]
    rooms = p1_rooms(words)
    for t, l, b, r in rooms:                     # wall pokes, 4 runs a room
        for c in range(l, r + 1):
            _poke_wall(words, t * 16 + c)
            _poke_wall(words, b * 16 + c)
        for y in range(t + 1, b):
            _poke_wall(words, y * 16 + l)
            _poke_wall(words, y * 16 + r)
    man_rooms = [
        next(i for i, rm in enumerate(rooms)
             if rm[0] < a >> 4 < rm[2] and rm[1] < (a & 15) < rm[3])
        for a in reversed(men) if a
    ]
    cands = []
    for addr in range(256):                      # one lap: pipe-head hunt
        d = ARROW_CODE.get(_char(words, addr))
        if d is None:
            continue
        gr, gc = addr >> 4, addr & 15
        br, bc = gr - DR[d], gc - DC[d]
        if not (0 <= br < 16 and 0 <= bc < 16):
            continue
        for si, rm in enumerate(rooms):
            if _on_border(rm, br, bc) and not _contains(rm, gr, gc):
                cands.append((si << 10 | (br * 16 + bc) << 2 | PROBE[d], addr, d))
    assert len(cands) <= CAND_CAP, "candidate slot budget exceeded"
    cands.sort()                                 # (room, border scan, NSWE)
    pipes, used = [], set()
    for key, gaddr, d in cands:
        if gaddr in used:
            continue
        si = key >> 10
        r, c = gaddr >> 4, gaddr & 15
        cells = [gaddr]
        while True:
            nd = ARROW_CODE.get(_char(words, r * 16 + c))
            if nd is not None:
                d = nd
                fr, fc = r + DR[d], c + DC[d]
                ti = next((i for i, rm in enumerate(rooms)
                           if _on_border(rm, fr, fc)), -1)
                if ti >= 0 and ti != si:
                    break
            r, c = r + DR[d], c + DC[d]
            cells.append(r * 16 + c)
            assert len(cells) <= 20, "pipe trace overran the cell budget"
        used.update(cells)
        pipes.append((cells, si, ti))
    out = words + list(men) + [len(pipes)]
    for cells, si, ti in pipes:
        om = sum(1 << i for i, mr in enumerate(man_rooms) if mr == si)
        im = sum(1 << i for i, mr in enumerate(man_rooms) if mr == ti)
        out.append(len(cells) | cells[0] << 5 | cells[-1] << 13
                   | om << 21 | im << 24)
        for base in range(0, 21, 3):
            out.append(sum(cells[base + k] << (21 * k) for k in range(3)
                           if base + k < len(cells)))
    return out + stream[4 * WORDS + MEN :]


def scan3_reference(tokens: list[int]) -> list[int]:
    """The whole chain: v2 ingest -> rooms/walls/pipes -> pack."""
    return pack64(p1_stream(scan_reference_v2(tokens)))


# ------------------------------------------------------- FSM compiler, v3
# lllm_scan's _Fsm/_layout/_tracks are reused verbatim; only the column
# bands differ: v3 literals run up to 15 digits (bit masks to 2**47), so
# the literal zones are wider, and the zone table is otherwise v2's.
from .lllm_scan import ARMS, _Fsm, _layout, _tracks  # noqa: E402

L_ZONES3 = {"lit_l": 3, "left": 25, "mid": 37}
R_ZONES3 = ("lit_r", "right")
Z_NAMES3 = (*L_ZONES3, *R_ZONES3)
LIT_ZONES3 = ("lit_l", "lit_r")
TICK_OFFSET3 = 1


def _check3(fsm: _Fsm) -> None:
    names = [b[0] for b in fsm.blocks]
    if len(set(names)) != len(names):
        raise ValueError("duplicate block name")
    known = set(names)
    for name, zone, code, _kind, targets in fsm.blocks:
        if zone not in Z_NAMES3:
            raise ValueError(f"{name}: unknown zone {zone}")
        if ("`" in code) != (zone in LIT_ZONES3):
            raise ValueError(f"{name}: literal/zone mismatch")
        if "`" in code and code.index("`") != TICK_OFFSET3:
            raise ValueError(f"{name}: literal not column aligned")
        for target in targets:
            if target not in known:
                raise ValueError(f"{name}: unknown target {target}")


def _columns3(tracks: int) -> tuple[dict[str, int], int, int]:
    """lit zones hold 21 columns, op zones 11; ring ops stay right of the
    midline for any track count (width = 94 + 2*tracks)."""
    lit_r = 48 + tracks
    zones = dict(L_ZONES3, lit_r=lit_r, right=lit_r + 22)
    branch = lit_r + 42
    return zones, branch, branch + 2


def _compile3(fsm: _Fsm) -> list[str]:
    """v2's renderer with the v3 zone tables (collision rules identical)."""
    _check3(fsm)
    route_rows, block_rows, height = _layout(fsm)
    edge_track, tracks = _tracks(fsm, route_rows, block_rows)
    zones, branch_col, edge_base = _columns3(tracks)
    zone_of = {block[0]: block[1] for block in fsm.blocks}
    width = edge_base + tracks + 2
    grid = [[" "] * (width + 2) for _ in range(height + 2)]
    for c in range(width + 2):
        grid[0][c] = grid[height + 1][c] = "-"
    for r in range(height + 2):
        grid[r][0] = grid[r][width + 1] = "|"
    for r, c in ((0, 0), (0, width + 1), (height + 1, 0),
                 (height + 1, width + 1)):
        grid[r][c] = "+"

    def put(row: int, col: int, char: str) -> None:
        old = grid[row][col]
        if old not in (" ", char):
            raise ValueError(f"collision at ({row},{col}): {old!r}/{char!r}")
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


def _lit(n: int) -> str:
    """15-digit literal, walked rightward (leading zeros are harmless)."""
    return f"`{n:015d}`"


# ------------------------------------------------------------ the S2 room
# Per word, four statically unrolled phases k = 0..3.  Phase invariant:
# the private ring holds [partial] on entry (empty for k = 0); the raw
# token is parked once, char = t % 256 is parked once, and the ring FIFO
# rotation e/f brings the partial behind them, so every value is in A
# exactly when its literal step needs it.  Phase 3 sends to the OUTPUT
# (left zone s) instead of re-parking, leaving the ring empty.
def _s2_phase(fsm: _Fsm, tag: str, mult: int, last: bool, nxt: str) -> None:
    fsm.go(f"{tag}a", "left", "r", f"{tag}b")            # A = field
    if mult == 1:
        fsm.go(f"{tag}b", "right", "s", nxt)             # becomes partial
        return
    fsm.go(f"{tag}b", "lit_r", "M" + _lit(mult) + "W*M", f"{tag}c")
    fsm.go(f"{tag}c", "right", "r+", f"{tag}d")          # + old partial
    fsm.go(f"{tag}d", "left" if last else "right", "s", nxt)


def _build_s2_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "lit_l", "@" + _lit(WORDS) + "b", "k0a")
    for k, nxt in ((0, "k1a"), (1, "k2a"), (2, "k3a"), (3, "wl")):
        _s2_phase(fsm, f"k{k}", FIELD**k, k == 3, nxt)
    fsm.bp("wl", "mid", "m", zero="relay", pos="k0a")
    fsm.go("relay", "left", "rs", "relay")
    return fsm


def build_s2_room() -> list[str]:
    """The packer room: 256 fields in -> 64 words out, then pure relay."""
    return _compile3(_build_s2_fsm())


# --------------------------------------------- P1 controller assembler
# Memory slot map (N = 312 ring slots; DK = N - 2 is the dummy target):
NSLOT = 312
DK = NSLOT - 2
MEN_S = 256      # 256..258 man addrs
NR_S = 259       # room count
RC_S = 260       # 260..271 room coords t,l,b,r per room
MR_S = 272       # 272..274 man->room (reading order), -1 absent
CN_S = 275       # candidate count
C_S = 276        # 276..283 candidate words key<<10 | gaddr<<2 | dir
PC_S = 284       # pipe count
D_S = 285        # 285..300 descriptor words, 8 per pipe
S0, S1, S2, S3, S4, S5, S6 = range(301, 308)     # scratch


class _Asm:
    """Linear block emitter over _Fsm: goto blocks auto-chain to the
    next emitted block; labels name join points for branches/loops."""

    def __init__(self) -> None:
        self.rows: list[list] = []       # [name, zone, code, kind, targets]
        self.count = 0
        self.next_name: str | None = None

    def _emit(self, zone, code, kind, targets) -> str:
        name = self.next_name or f"b{self.count}"
        self.next_name = None
        self.count += 1
        if self.rows and self.rows[-1][3] == "goto" \
                and self.rows[-1][4] == ["AUTO"]:
            self.rows[-1][4] = [name]
        self.rows.append([name, zone, code, kind, list(targets)])
        return name

    def label(self, name: str) -> None:
        self.next_name = name

    def go(self, zone, code, to="AUTO"):
        return self._emit(zone, code, "goto", [to])

    def sign(self, zone, code, neg, zero, pos):
        return self._emit(zone, code, "sign", [neg, zero, pos])

    def bp(self, zone, code, zero, pos):
        return self._emit(zone, code, "bp", [zero, pos])

    def fsm(self) -> _Fsm:
        out = _Fsm()
        for name, zone, code, kind, targets in self.rows:
            assert targets != ["AUTO"], f"{name}: unresolved chain"
            out.blocks.append((name, zone, code, kind, tuple(targets)))
        return out

    # ---- memory macros: one op + one dummy write = one full ring lap
    def rd_c(self, slot):
        """A := mem[slot]; B is preserved through the whole read."""
        self.go("lit_r", " " + _lit(slot + 1) + "Ns")
        self.go("lit_r", " " + _lit(DK - slot) + "s0s")
        self.go("right", "r")

    def wr_c(self, slot):
        """mem[slot] := A (A survives; B ends holding slot)."""
        self.go("lit_r", "M" + _lit(slot) + "sWs")
        self.go("lit_r", " " + _lit(DK - slot) + "s0s")

    def rd_a(self):
        """A := mem[A] (B clobbered)."""
        self.go("lit_r", "M" + _lit(1) + "+Ns")
        self.go("lit_r", " " + _lit(DK) + "-s0s")
        self.go("right", "r")

    def wr_a(self):
        """mem[A] := B (both clobbered)."""
        self.go("right", "sWs")
        self.go("lit_r", " " + _lit(DK) + "W-N")
        self.go("right", "s0s")

    def op(self, opch, n):
        """A := A <opch> n  (B ends holding n)."""
        self.go("lit_r", "M" + _lit(n) + "W" + opch)

    def test(self, n, neg, zero, pos):
        """Branch on sign of A - n; every arm receives A = A - n."""
        self.sign("lit_r", "M" + _lit(n) + "W-", neg, zero, pos)

    def bump(self, slot, delta):
        """mem[slot] += delta (A ends holding the new value)."""
        self.rd_c(slot)
        self.op("+" if delta >= 0 else "-", abs(delta))
        self.wr_c(slot)

    def setc(self, slot, value):
        """mem[slot] := literal value (A/B dead after, like wr_c)."""
        self.go("lit_r", " " + _lit(value))
        self.wr_c(slot)

    def jmp(self, to):
        self.go("right", "", to=to)


def _p1_ingest(a: _Asm, done: str) -> None:
    """mem[0..255] := stripped cells, mem[256..258] := men; i in S0."""
    a.label("ing_top")
    a.rd_c(S0)
    a.test(256 + MEN, "ing_body", done, done)
    a.label("ing_body")
    a.go("right", "+")                   # A = i again
    a.wr_c(S3)
    a.rd_c(S3)
    a.test(256, "ing_strip", "ing_man", "ing_man")
    a.label("ing_strip")
    a.go("left", "r")                    # A = raw v2 token
    a.wr_c(S1)
    a.rd_c(S1)
    a.op("}", 9)                         # padding bit
    a.op("*", 512)
    a.wr_c(S2)
    a.rd_c(S1)
    a.op("%", 256)                       # char
    a.go("right", "M")
    a.rd_c(S2)                           # A = 512*pad, B = char
    a.go("right", "+M")                  # A = clean field, B = clean
    a.rd_c(S3)                           # A = i, B = clean
    a.wr_a()
    a.jmp("ing_inc")
    a.label("ing_man")
    a.go("left", "r")
    a.go("right", "M")
    a.rd_c(S3)
    a.wr_a()
    a.label("ing_inc")
    a.bump(S0, 1)
    a.jmp("ing_top")


def _p1_emit(a: _Asm, relay: str) -> None:
    """Drain fields+men, PC, then 8*PC descriptor words; then relay."""
    a.label("em0")
    a.setc(S0, 0)
    a.label("em_top")
    a.rd_c(S0)
    a.test(256 + MEN, "em_body", "em_pc", "em_pc")
    a.label("em_body")
    a.go("right", "+")
    a.rd_a()
    a.go("left", "s")
    a.bump(S0, 1)
    a.jmp("em_top")
    a.label("em_pc")
    a.rd_c(PC_S)
    a.go("left", "s")
    a.test(1, relay, "em_d8", "em_d16")
    a.label("em_d8")
    a.setc(S1, D_S + 8)
    a.jmp("em_dini")
    a.label("em_d16")
    a.setc(S1, D_S + 16)
    a.label("em_dini")
    a.setc(S0, D_S)
    a.label("em_dtop")
    a.rd_c(S0)
    a.go("right", "M")
    a.rd_c(S1)                           # A = limit, B = q
    a.go("right", "W-")                  # A = q - limit
    a.sign("mid", "", "em_dbody", relay, relay)
    a.label("em_dbody")
    a.go("right", "+")                   # A = q
    a.rd_a()
    a.go("left", "s")
    a.bump(S0, 1)
    a.jmp("em_dtop")


def _build_p1_asm(phases: int = 9) -> _Asm:
    """The controller program; ``phases`` gates how much is built."""
    a = _Asm()
    a.go("mid", "@")
    _p1_ingest(a, "em0")
    _p1_emit(a, "relay")
    a.label("relay")
    a.go("left", "rs", to="relay")
    return a


def build_p1_rig(phases: int = 9) -> str:
    """I -> controller(+312-slot memory) -> O, for phase gates."""
    from .canvas import Canvas

    room = _compile3(_build_p1_asm(phases).fsm())
    cr = 5 + len(room[0]) - 1
    cv = Canvas()
    cv.put(0, 5, room)
    cv.put(1, 0, ["+-+", "|I|", "+-+"])
    cv.put(5, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(2, 3), (2, 4)])
    cv.pipe([(6, 4), (6, 3)])
    _add_memory(cv, cr + 8, cr)
    return cv.render()


# ------------------------------------------------ P1 memory subsystem
# memory.py's P3W/P3R verbatim; the seeding relay grown to 312 zeros.
RELAY312 = [
    "+-----------+",
    "|@`311`b0>sv|",
    "|        ^md|",
    "|        >sv|",
    "|        ^r<|",
    "+-----------+",
]


def _serpentine(top: int, bot: int, left: int, cols: int) -> list[tuple]:
    """Zigzag waypoints over ``cols`` vertical runs; ends on the top row
    (use an odd ``cols``), ready for a leftward return corridor."""
    out = []
    for j in range(cols):
        c = left + 2 * j
        if j % 2 == 0:
            out += [(bot, c), (top, c)]
        else:
            out += [(top, c), (bot, c)]
    return out


def _add_memory(cv, mx: int, cr: int) -> None:
    """Rooms + wiring for the 312-slot ring; controller wall is at cr."""
    from .memory import P3R, P3W

    cv.put(0, mx, P3W)                    # rows 0..10
    cv.put(13, mx, P3R)                   # rows 13..20
    cv.put(23, mx, RELAY312)              # rows 23..28
    cv.pipe([(2, cr + 1), (2, mx - 3), (3, mx - 3), (3, mx - 1)])
    cv.pipe([(18, mx - 1), (18, cr + 2), (9, cr + 2), (9, cr + 1)])
    cv.pipe([(11, mx + 2), (12, mx + 2)])            # cmd fwd
    cv.pipe([(11, mx + 16), (12, mx + 16), (12, mx + 9)])  # ring W->R
    cv.cells[(12, mx + 9)] = "v"          # terminal bend into P3R top
    cv.pipe([(21, mx + 10), (22, mx + 10), (22, mx - 3), (27, mx - 3),
             (27, mx - 1)])               # ring R -> RELAY
    serp = _serpentine(14, 26, mx + 15, 25)
    cv.pipe([(26, mx + 13), (26, mx + 14)] + serp
            + [(13, serp[-1][1]), (13, mx + 18), (12, mx + 18),
               (11, mx + 18)])            # RELAY -> park -> P3W ring-in


def build_s2_rig() -> str:
    """``I -> S2 -> O`` plus the 3-deep private ring, for unit tests."""
    from .canvas import Canvas
    from .lllm_scan import build_relay

    room = build_s2_room()
    right = 5 + len(room[0]) - 1
    cv = Canvas()
    cv.put(0, 5, room)
    cv.put(1, 0, ["+-+", "|I|", "+-+"])
    cv.put(5, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(2, 3), (2, 4)])
    cv.pipe([(6, 4), (6, 3)])
    relay_left = right + 5
    cv.put(1, relay_left, build_relay())
    cv.pipe([(2, right + 1), (2, relay_left - 1)])
    far = relay_left + 8
    cv.pipe([(3, relay_left + 6), (3, far), (9, far), (9, right + 1)])
    return cv.render()
