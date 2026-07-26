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


def strip256(stream: list[int]) -> list[int]:
    """SR room model: heuristic wall bit off the first 256 tokens."""
    return [t % CHAR + 512 * (t >> 9) for t in stream[:256]] + stream[256:]


def p1_stream(stream: list[int]) -> list[int]:
    """Rooms, walls, man rooms, pipe discovery, emission, relay.

    Input is the SR-stripped stream: 256 clean fields, 3 men, tail.
    """
    words = list(stream[: 4 * WORDS])
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
    """The whole chain: v2 -> strip -> rooms/walls/pipes -> pack."""
    return pack64(p1_stream(strip256(scan_reference_v2(tokens))))


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


def _build_sr_fsm() -> _Fsm:
    """SR: strip the heuristic wall bit off 256 tokens, then relay.

    Per token the 2-deep private ring parks the raw token and the char
    so  char + 512*(t>>9)  can be summed without losing either.
    """
    fsm = _Fsm()
    fsm.go("boot", "lit_l", "@" + _lit(256) + "b", "t0")
    fsm.go("t0", "left", "r", "t1")                  # A = t
    fsm.go("t1", "right", "s", "t2")                 # park t
    fsm.go("t2", "lit_r", "M" + _lit(256) + "W%", "t3")   # A = char
    fsm.go("t3", "right", "s", "t4")                 # park char
    fsm.go("t4", "right", "r", "t5")                 # A = t again
    fsm.go("t5", "lit_r", "M" + _lit(9) + "W}", "t6")
    fsm.go("t6", "lit_r", "M" + _lit(512) + "W*", "t7")   # A = 512*pad
    fsm.go("t7", "right", "Mr+", "t8")               # + char
    fsm.go("t8", "left", "s", "tl")                  # emit clean field
    fsm.bp("tl", "mid", "m", zero="relay", pos="t0")
    fsm.go("relay", "left", "rs", "relay")
    return fsm


def build_sr_room() -> list[str]:
    return _compile3(_build_sr_fsm())


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
S7, S8, S9 = 308, 309, 310   # more scratch: every dummy write lands on
                             # slot 311 (head+k'+1 = 312), so only 311
                             # must stay clear of live state.


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
    def rd_c(self, slot, post=""):
        """A := mem[slot]; B is preserved through the whole read.

        ``post`` appends register ops to the receiving block: "M" parks
        the value, "-"/"+"/"*" combine it with the preserved B.
        """
        self.go("lit_r", " " + _lit(slot + 1) + "Ns")
        self.go("lit_r", " " + _lit(DK - slot) + "s0s")
        self.go("right", "r" + post)

    def diff(self, xs, ys):
        """A := mem[xs] - mem[ys]  (B := mem[ys])."""
        self.rd_c(ys, "M")
        self.rd_c(xs, "-")

    def wr_at(self, slot):
        """mem[mem[slot]] := A (A/B clobbered)."""
        self.go("right", "M")
        self.rd_c(slot)
        self.wr_a()

    def wr_c(self, slot):
        """mem[slot] := A (A survives; B ends holding slot)."""
        self.go("lit_r", "M" + _lit(slot) + "sWs")
        self.go("lit_r", " " + _lit(DK - slot) + "s0s")

    def rd_a(self, post=""):
        """A := mem[A] (B := the address read)."""
        self.go("lit_r", "M" + _lit(1) + "+Ns")
        self.go("lit_r", " " + _lit(DK) + "-s0s")
        self.go("right", "r" + post)

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


def _p1_ingest(a: _Asm) -> None:
    """259 rolling writes (k = 0 advances the head by one), realign."""
    a.go("lit_l", " " + _lit(256 + MEN) + "b")
    a.label("ing_t")
    a.go("left", "r")                    # A = clean field / man addr
    a.go("right", "M0sWs")               # write k=0: [0, value]
    a.bp("mid", "m", zero="ing_fix", pos="ing_t")
    a.label("ing_fix")                   # head = 259; write pad 311
    a.go("lit_r", " " + _lit(NSLOT - 260) + "s0s")


def _p1_emit(a: _Asm, relay: str) -> None:
    """Rolling drain: fields+men, skip to PC, then 8*PC descriptors."""
    a.label("em0")
    a.go("lit_l", " " + _lit(256 + MEN) + "b")
    a.label("em_t")
    a.go("lit_r", " " + _lit(1) + "Ns")  # read k=0: next slot
    a.go("right", "r")
    a.go("left", "s")
    a.bp("mid", "m", zero="em_pc", pos="em_t")
    a.label("em_pc")                     # head = 259; PC sits at k = 25
    a.go("lit_r", " " + _lit(PC_S - 259 + 1) + "Ns")
    a.go("right", "r")
    a.go("left", "s")
    a.test(1, relay, "em_d8", "em_d16")
    a.label("em_d8")
    a.go("lit_l", " " + _lit(8) + "b")
    a.jmp("em_dt")
    a.label("em_d16")
    a.go("lit_l", " " + _lit(16) + "b")
    a.label("em_dt")                     # head = 285 = D_S: roll again
    a.go("lit_r", " " + _lit(1) + "Ns")
    a.go("right", "r")
    a.go("left", "s")
    a.bp("mid", "m", zero=relay, pos="em_dt")


def _p1_rooms_walls(a: _Asm, done: str = "em0") -> None:
    """Phase 2: find_rooms walk + fused frame pokes (model: p1_rooms).

    Outer addr scan in S0; on '+' (43 or 299 — poked cells add 256,
    matching the model's %256): c2 scan in S1, r2 scan in S2, corner
    in S3, then bottom-run/right-column validation; on accept write
    t,l,b,rt to RC_S + 4*NR, poke the four frame runs (cur S4, last
    S5, literal stride per copy, field := field%256 + 256), NR += 1.
    Every glyph test accepts g and g+256, which makes fusing the
    pokes into the scan exactly the model's collect-then-poke.
    """
    _p2_scan(a, done)
    _p2_edges(a)
    _p2_corner(a)
    _p2_accept(a)


def _p2_scan(a: _Asm, done: str) -> None:
    """Reading-order hunt for a '+' top-left corner; exit to ``done``."""
    a.setc(S0, 0)
    a.label("sc_t")
    a.rd_c(S0)
    a.rd_a()                                 # A = field at addr a
    a.test(43, "sc_n", "sc_hit", "sc_p1")
    a.label("sc_p1")
    a.test(256, "sc_n", "sc_hit", "sc_n")    # 299 = poked '+'
    a.label("sc_n")                          # a += 1; 256 -> done
    a.rd_c(S0)
    a.op("+", 1)
    a.test(256, "sc_keep", done, done)
    a.label("sc_keep")
    a.op("+", 256)                           # undo the test's subtract
    a.wr_c(S0)
    a.jmp("sc_t")


def _p2_edges(a: _Asm) -> None:
    """c2 scan (S1, '-' run, same row) and r2 scan (S2, '|' run)."""
    a.label("sc_hit")
    a.rd_c(S0)
    a.op("+", 1)
    a.wr_c(S1)
    a.label("cj_t")
    a.rd_c(S1)
    a.op("%", 16)
    a.sign("right", "", "sc_n", "sc_n", "cj_rd")     # wrapped the row
    a.label("cj_rd")
    a.rd_c(S1)
    a.rd_a()
    a.test(43, "sc_n", "cj_c", "cj_p1")
    a.label("cj_p1")
    a.test(2, "sc_n", "cj_adv", "cj_p2")             # 45 = '-'
    a.label("cj_p2")
    a.test(254, "sc_n", "cj_c", "cj_p3")             # 299
    a.label("cj_p3")
    a.test(2, "sc_n", "cj_adv", "sc_n")              # 301
    a.label("cj_adv")
    a.bump(S1, 1)
    a.jmp("cj_t")
    a.label("cj_c")                          # corner needs j - a >= 2
    a.diff(S1, S0)
    a.test(2, "sc_n", "ck_s", "ck_s")
    a.label("ck_s")
    a.rd_c(S0)
    a.op("+", 16)
    a.wr_c(S2)
    a.label("ck_t")
    a.rd_c(S2)
    a.test(256, "ck_rd", "sc_n", "sc_n")             # k >= 256 reject
    a.label("ck_rd")
    a.op("+", 256)                           # A back to k, then read
    a.rd_a()
    a.test(43, "sc_n", "ck_c", "ck_p1")
    a.label("ck_p1")
    a.test(81, "sc_n", "ck_adv", "ck_p2")            # 124 = '|'
    a.label("ck_p2")
    a.test(175, "sc_n", "ck_c", "ck_p3")             # 299
    a.label("ck_p3")
    a.test(81, "sc_n", "ck_adv", "sc_n")             # 380
    a.label("ck_adv")
    a.bump(S2, 16)
    a.jmp("ck_t")
    a.label("ck_c")                          # corner needs k - a >= 32
    a.diff(S2, S0)
    a.test(32, "sc_n", "cc_s", "cc_s")


def _p2_corner(a: _Asm) -> None:
    """S3 = far corner k + (j - a); validate it, then the two runs."""
    a.label("cc_s")
    a.diff(S1, S0)                           # A = j - a
    a.go("right", "M")
    a.rd_c(S2, "+")                          # A = k + (j - a)
    a.wr_c(S3)
    a.rd_c(S3)
    a.rd_a()
    a.test(43, "sc_n", "cb_s", "cc_p1")
    a.label("cc_p1")
    a.test(256, "sc_n", "cb_s", "sc_n")
    a.label("cb_s")                          # bottom run k+1 .. corner-1
    a.rd_c(S2)
    a.op("+", 1)
    a.wr_c(S4)
    a.label("cb_t")
    a.diff(S3, S4)
    a.sign("right", "", "sc_n", "cb_done", "cb_rd")
    a.label("cb_rd")
    a.rd_c(S4)
    a.rd_a()
    a.test(45, "sc_n", "cb_adv", "cb_p1")
    a.label("cb_p1")
    a.test(256, "sc_n", "cb_adv", "sc_n")            # 301
    a.label("cb_adv")
    a.bump(S4, 1)
    a.jmp("cb_t")
    a.label("cb_done")                       # right column j+16 .. c-16
    a.rd_c(S1)
    a.op("+", 16)
    a.wr_c(S4)
    a.label("cr_t")
    a.diff(S3, S4)
    a.sign("right", "", "sc_n", "acc", "cr_rd")
    a.label("cr_rd")
    a.rd_c(S4)
    a.rd_a()
    a.test(124, "sc_n", "cr_adv", "cr_p1")
    a.label("cr_p1")
    a.test(256, "sc_n", "cr_adv", "sc_n")            # 380
    a.label("cr_adv")
    a.bump(S4, 16)
    a.jmp("cr_t")


def _p2_accept(a: _Asm) -> None:
    """Write t,l,b,rt to RC_S + 4*NR, poke the frame, NR += 1."""
    a.label("acc")
    a.rd_c(NR_S)
    a.op("*", 4)
    a.op("+", RC_S)
    a.wr_c(S6)                               # coord write cursor
    for src, opch, tag in ((S0, "}", "t"), (S0, "%", "l"),
                           (S2, "}", "b"), (S3, "%", "r")):
        a.rd_c(src)
        a.op(opch, 4 if opch == "}" else 16)
        a.wr_at(S6)
        if tag != "r":
            a.bump(S6, 1)
    a.bump(NR_S, 1)
    for tag, lo, dlo, hi, dhi, stride, nxt in (
        ("pt", S0, 0, S1, 0, 1, "pk_r"),
        ("pr", S1, 16, S3, -16, 16, "pk_b"),
        ("pb", S2, 0, S3, 0, 1, "pk_l"),
        ("pl", S0, 16, S2, -16, 16, "sc_n"),
    ):
        if tag != "pt":
            a.label("pk_" + tag[1])
        a.rd_c(lo)
        if dlo:
            a.op("+", dlo)
        a.wr_c(S4)
        a.rd_c(hi)
        if dhi:
            a.op("-", -dhi)
        a.wr_c(S5)
        _pk(a, tag, stride, nxt)


def _pk(a: _Asm, tag: str, stride: int, nxt: str) -> None:
    """Poke mem[S4]..mem[S5] step ``stride``: field := field%256+256."""
    a.label(f"{tag}_t")
    a.rd_c(S4)
    a.rd_a()
    a.op("%", 256)
    a.go("right", "+")                       # B = 256 from the op
    a.wr_at(S4)
    a.bump(S4, stride)
    a.diff(S5, S4)
    a.sign("right", "", nxt, f"{tag}_t", f"{tag}_t")


def _p1_manrooms(a: _Asm) -> None:
    """Phase 3a: MR_S[i] = room of reading-order man i, -1 absent.

    Slot cursor S0 walks 258 -> 256 (stream order is reversed reading
    order); packed index S6 fills MR_S; y/x in S1/S2; room in S4.
    """
    a.label("mr0")
    for i in range(MEN):
        a.go("lit_r", " " + _lit(1) + "N")
        a.wr_c(MR_S + i)
    a.setc(S6, 0)
    a.setc(S0, MEN_S + 2)
    a.label("mr_m")
    a.rd_c(S0)
    a.rd_a()
    a.sign("right", "", "mr_nx", "mr_nx", "mr_f")    # addr 0 = absent
    a.label("mr_f")
    a.wr_c(S3)
    a.rd_c(S3)
    a.op("}", 4)
    a.wr_c(S1)                               # y
    a.rd_c(S3)
    a.op("%", 16)
    a.wr_c(S2)                               # x
    a.setc(S4, 0)
    a.label("mr_r")
    a.diff(NR_S, S4)
    a.sign("right", "", "mr_nx", "mr_nx", "mr_c")
    a.label("mr_c")
    a.rd_c(S4)
    a.op("*", 4)
    a.op("+", RC_S)
    a.wr_c(S5)                               # coord base
    for off, coord, arms in ((0, S1, ("mr_rn", "mr_rn", "mr_c2")),
                             (2, S1, ("mr_c3", "mr_rn", "mr_rn")),
                             (1, S2, ("mr_rn", "mr_rn", "mr_c4")),
                             (3, S2, ("mr_hit", "mr_rn", "mr_rn"))):
        if off:
            a.label({2: "mr_c2", 1: "mr_c3", 3: "mr_c4"}[off])
        a.rd_c(S5)
        if off:
            a.op("+", off)
        a.rd_a("M")
        a.rd_c(coord, "-")                   # A = y/x - coord value
        a.sign("right", "", *arms)
    a.label("mr_rn")
    a.bump(S4, 1)
    a.jmp("mr_r")
    a.label("mr_hit")                        # MR_S[S6] := room S4
    a.rd_c(S6)
    a.op("+", MR_S)
    a.wr_c(S5)
    a.rd_c(S4)
    a.wr_at(S5)
    a.bump(S6, 1)
    a.label("mr_nx")                         # slot cursor -= 1; 255 done
    a.rd_c(S0)
    a.op("-", 1)
    a.test(MEN_S - 1, "mr_keep", "ca0", "mr_keep")
    a.label("mr_keep")
    a.op("+", MEN_S - 1)
    a.wr_c(S0)
    a.jmp("mr_m")


def _p1_cands(a: _Asm) -> None:
    """Phase 3b: arrow scan -> C_S words (key<<10 | addr<<2 | d), then
    a fixed 7-pass bubble sort.  key = si<<10 | baddr<<2 | probe.

    Slots: S0 addr, S1 baddr, S2 pre = addr<<2|d, S3 probe, S4 room,
    S5 addr temp, S6 value temp.  A candidate is appended per room
    whose border holds baddr while (gr,gc) is outside it, exactly the
    model's per-room loop; the wall bit on baddr (poked in phase 2 =
    true border membership) is a lossless pre-filter.
    """
    a.label("ca0")
    for i in range(CAND_CAP):
        a.setc(C_S + i, 1 << 23)             # sort sentinels
    a.setc(CN_S, 0)
    a.setc(S0, 0)
    a.label("ca_t")
    a.rd_c(S0)
    a.rd_a()
    a.test(60, "ca_nx", "ca_w", "ca_t1")     # '<'  d=3
    a.label("ca_t1")
    a.test(2, "ca_nx", "ca_e", "ca_t2")      # '>'  d=1
    a.label("ca_t2")
    a.test(32, "ca_nx", "ca_n", "ca_t3")     # '^'  d=0
    a.label("ca_t3")
    a.test(24, "ca_nx", "ca_s", "ca_nx")     # 'v'  d=2
    a.label("ca_n")                          # baddr=addr+16, need row<15
    a.rd_c(S0)
    a.test(240, "can_ok", "ca_nx", "ca_nx")
    a.label("can_ok")
    a.op("+", 256)                           # addr + 16
    a.wr_c(S1)
    _ca_tail(a, 0, 0)
    a.label("ca_s")                          # baddr=addr-16, need row>0
    a.rd_c(S0)
    a.test(16, "ca_nx", "cas_ok", "cas_ok")
    a.label("cas_ok")
    a.wr_c(S1)                               # A was already addr-16
    _ca_tail(a, 2, 1)
    a.label("ca_e")                          # baddr=addr-1, need col>0
    a.rd_c(S0)
    a.op("%", 16)
    a.sign("right", "", "ca_nx", "ca_nx", "cae_ok")
    a.label("cae_ok")
    a.rd_c(S0)
    a.op("-", 1)
    a.wr_c(S1)
    _ca_tail(a, 1, 3)
    a.label("ca_w")                          # baddr=addr+1, need col<15
    a.rd_c(S0)
    a.op("%", 16)
    a.test(15, "caw_ok", "ca_nx", "ca_nx")
    a.label("caw_ok")
    a.rd_c(S0)
    a.op("+", 1)
    a.wr_c(S1)
    _ca_tail(a, 3, 2)
    _q_rooms(a)
    _q_sort(a)


def _ca_tail(a: _Asm, d: int, probe: int) -> None:
    """Seed pre/probe for one arrow direction and enter the filter."""
    a.rd_c(S0)
    a.op("*", 4)
    if d:
        a.op("+", d)
    a.wr_c(S2)
    a.setc(S3, probe)
    a.jmp("ca_f")


def _q_rooms(a: _Asm) -> None:
    """Wall-bit filter, then per-room border/outside checks + append."""
    a.label("ca_f")
    a.rd_c(S1)
    a.rd_a()
    a.op("%", 512)
    a.test(256, "ca_nx", "ca_rl", "ca_rl")   # baddr not on any border
    a.label("ca_rl")
    a.setc(S4, 0)
    a.label("qr_t")
    a.diff(NR_S, S4)
    a.sign("right", "", "ca_nx", "ca_nx", "qr_c")
    a.label("qr_c")
    a.rd_c(S4)
    a.op("*", 4)
    a.op("+", RC_S)
    a.wr_c(S5)
    # contains(br,bc) with edge tracking: chain a = all strict so far,
    # chain b = an equality seen (border already established).
    plan = (("qa1", 0, "}", S1, ("qr_n", "qb2", "qa2")),
            ("qa2", 2, None, None, ("qa3", "qb3", "qr_n")),
            ("qa3", 1, "%", S1, ("qr_n", "qb4", "qa4")),
            ("qa4", 3, None, None, ("qr_n", "qbrd", "qr_n")),
            ("qb2", 2, None, None, ("qb3", "qb3", "qr_n")),
            ("qb3", 1, "%", S1, ("qr_n", "qb4", "qb4")),
            ("qb4", 3, None, None, ("qbrd", "qbrd", "qr_n")))
    for name, off, drv, src, arms in plan:
        if name != "qa1":
            a.label(name)
        if drv:                              # S6 := br (>>4) / bc (%16)
            a.rd_c(src)
            a.op(drv, 4 if drv == "}" else 16)
            a.wr_c(S6)
        a.rd_c(S5)
        if off:
            a.op("+", off)
        a.rd_a("M")
        a.rd_c(S6, "-")                      # A = br/bc - coord
        a.sign("right", "", *arms)
    gplan = (("qbrd", 0, "}", ("qap", "qg2", "qg2")),
             ("qg2", 2, None, ("qg3", "qg3", "qap")),
             ("qg3", 1, "%", ("qap", "qg4", "qg4")),
             ("qg4", 3, None, ("qr_n", "qr_n", "qap")))
    for name, off, drv, arms in gplan:       # NOT contains(gr,gc)
        a.label(name)
        if drv:                              # S6 := gr / gc from pre
            a.rd_c(S2)
            a.op("}", 6 if drv == "}" else 2)
            if drv == "%":
                a.op("%", 16)
            a.wr_c(S6)
        a.rd_c(S5)
        if off:
            a.op("+", off)
        a.rd_a("M")
        a.rd_c(S6, "-")                      # A = gr/gc - coord
        a.sign("right", "", *arms)
    a.label("qap")                           # append the candidate
    a.rd_c(S4)
    a.op("*", 1024)
    a.wr_c(S6)
    a.rd_c(S1)
    a.op("*", 4)
    a.go("right", "M")
    a.rd_c(S6, "+")
    a.wr_c(S6)
    a.rd_c(S3, "M")
    a.rd_c(S6, "+")                          # A = key
    a.op("*", 1024)
    a.go("right", "M")
    a.rd_c(S2, "+")                          # A = key<<10 | pre
    a.wr_c(S6)
    a.rd_c(CN_S)
    a.op("+", C_S)
    a.wr_c(S5)
    a.rd_c(S6)
    a.wr_at(S5)
    a.bump(CN_S, 1)
    a.label("qr_n")
    a.bump(S4, 1)
    a.jmp("qr_t")
    a.label("ca_nx")                         # addr += 1; 256 -> sort
    a.rd_c(S0)
    a.op("+", 1)
    a.test(256, "ca_keep", "so0", "so0")
    a.label("ca_keep")
    a.op("+", 256)
    a.wr_c(S0)
    a.jmp("ca_t")


def _q_sort(a: _Asm) -> None:
    """Fixed 7x7 bubble sort of C_S..C_S+7 (sentinels sink last)."""
    a.label("so0")
    a.setc(S0, CAND_CAP - 1)                 # passes
    a.label("so_p")
    a.setc(S1, C_S)                          # left slot cursor
    a.label("so_t")
    a.rd_c(S1)
    a.rd_a()
    a.wr_c(S2)                               # left value
    a.rd_c(S1)
    a.op("+", 1)
    a.rd_a()
    a.wr_c(S3)                               # right value
    a.diff(S3, S2)
    a.sign("right", "", "so_sw", "so_nx", "so_nx")
    a.label("so_sw")                         # right < left: swap
    a.rd_c(S3)
    a.wr_at(S1)
    a.rd_c(S1)
    a.op("+", 1)
    a.wr_c(S4)
    a.rd_c(S2)
    a.wr_at(S4)
    a.label("so_nx")                         # cursor += 1 to C_S+6
    a.rd_c(S1)
    a.op("+", 1)
    a.test(C_S + CAND_CAP - 1, "so_keep", "so_pn", "so_pn")
    a.label("so_keep")
    a.op("+", C_S + CAND_CAP - 1)
    a.wr_c(S1)
    a.jmp("so_t")
    a.label("so_pn")                         # passes -= 1
    a.rd_c(S0)
    a.op("-", 1)
    a.sign("right", "", "tr0", "tr0", "so_wr")
    a.label("so_wr")
    a.wr_c(S0)
    a.jmp("so_p")


def _p1_traces(a: _Asm) -> None:
    """Phase 3c: per sorted candidate, used-check then trace + header.

    Slots: S0 q, S1 cur (starts gaddr), S2 desc cursor then cellbase,
    S3 si, S4 pipe cursor then off, S5/S6 temps (S5 = ti at break),
    S7 L, S8/S9 = fr/fc for the forward-cell border search.
    """
    a.label("tr0")
    a.setc(S0, 0)
    a.label("tr_q")
    a.diff(CN_S, S0)
    a.sign("right", "", "em0", "em0", "tr_c")
    a.label("tr_c")
    a.rd_c(S0)
    a.op("+", C_S)
    a.rd_a()
    a.op("}", 2)
    a.op("%", 256)
    a.wr_c(S1)                               # gaddr
    a.rd_c(S0)
    a.op("+", C_S)
    a.rd_a()
    a.op("}", 20)
    a.wr_c(S3)                               # si
    a.setc(S4, 0)
    a.label("us_p")                          # used-check over pipes
    a.diff(PC_S, S4)
    a.sign("right", "", "tr_go", "tr_go", "us_c")
    a.label("us_c")
    a.rd_c(S4)
    a.op("*", 8)
    a.op("+", D_S)
    a.wr_c(S2)
    a.rd_c(S2)
    a.rd_a()
    a.op("%", 32)
    a.wr_c(S7)                               # length countdown
    a.bump(S2, 1)
    a.label("us_w")
    a.rd_c(S7)
    a.sign("right", "", "us_pn", "us_pn", "us_w1")
    a.label("us_w1")
    a.rd_c(S2)
    a.rd_a()
    a.wr_c(S6)                               # packed cell word
    for k in range(3):
        if k:
            a.label(f"us_k{k}")
            a.rd_c(S7)
            a.sign("right", "", "us_pn", "us_pn", f"us_c{k}")
            a.label(f"us_c{k}")
            a.rd_c(S6)
            a.op("}", 21)
            a.wr_c(S6)
        a.rd_c(S6)
        a.op("%", 1 << 21)
        a.go("right", "M")
        a.rd_c(S1, "-")                      # gaddr - cell
        a.sign("right", "", f"us_m{k}", "tr_nx", f"us_m{k}")
        a.label(f"us_m{k}")
        a.bump(S7, -1)
    a.bump(S2, 1)
    a.jmp("us_w")
    a.label("us_pn")
    a.bump(S4, 1)
    a.jmp("us_p")
    _t_trace(a)
    _t_border(a)
    _t_finish(a)


def _t_trace(a: _Asm) -> None:
    """Append-then-examine loop: cells 3-per-word 21-bit into D_S."""
    a.label("tr_go")
    a.rd_c(PC_S)
    a.op("*", 8)
    a.op("+", D_S + 1)
    a.wr_c(S2)                               # cell words base
    a.setc(S7, 0)                            # L
    a.label("tr_lp")                         # append cur
    a.rd_c(S7)
    a.op("%", 3)
    a.op("*", 21)
    a.wr_c(S5)                               # shift
    a.rd_c(S7)
    a.op("/", 3)
    a.go("right", "M")                       # B = word index
    a.rd_c(S2, "+")
    a.wr_c(S6)                               # target slot
    a.rd_c(S5, "M")
    a.rd_c(S1)
    a.go("right", "{")                       # cur << shift
    a.wr_c(S5)
    a.rd_c(S6)
    a.rd_a("M")
    a.rd_c(S5, "+")
    a.wr_at(S6)
    a.bump(S7, 1)
    a.rd_c(S1)                               # examine cur
    a.rd_a()
    a.test(60, "tr_mv", "ta_w", "tw1")
    a.label("tw1")
    a.test(2, "tr_mv", "ta_e", "tw2")
    a.label("tw2")
    a.test(32, "tr_mv", "ta_n", "tw3")
    a.label("tw3")
    a.test(24, "tr_mv", "ta_s", "tr_mv")
    for tag, off, dr, dc in (("ta_n", -16, -1, 0), ("ta_e", 1, 0, 1),
                             ("ta_s", 16, 1, 0), ("ta_w", -1, 0, -1)):
        a.label(tag)
        if off > 0:
            a.setc(S4, off)
        else:
            a.go("lit_r", " " + _lit(-off) + "N")
            a.wr_c(S4)
        a.rd_c(S1)
        a.op("}", 4)
        if dr:
            a.op("+" if dr > 0 else "-", 1)
        a.wr_c(S8)                           # fr
        a.rd_c(S1)
        a.op("%", 16)
        if dc:
            a.op("+" if dc > 0 else "-", 1)
        a.wr_c(S9)                           # fc
        a.jmp("tb_t")
    a.label("tr_mv")                         # cur += off
    a.rd_c(S4, "M")
    a.rd_c(S1, "+")
    a.wr_c(S1)
    a.jmp("tr_lp")


def _t_border(a: _Asm) -> None:
    """First room with (fr,fc) on border; == si -> advance, else break."""
    a.label("tb_t")
    a.setc(S5, 0)
    a.label("tb_l")
    a.diff(NR_S, S5)
    a.sign("right", "", "tr_mv", "tr_mv", "tb_c")
    a.label("tb_c")
    plan = (("", 0, S8, ("tb_n", "tb_b2", "tb_a2")),
            ("tb_a2", 2, S8, ("tb_a3", "tb_b3", "tb_n")),
            ("tb_a3", 1, S9, ("tb_n", "tb_b4", "tb_a4")),
            ("tb_a4", 3, S9, ("tb_n", "tb_hit", "tb_n")),
            ("tb_b2", 2, S8, ("tb_b3", "tb_b3", "tb_n")),
            ("tb_b3", 1, S9, ("tb_n", "tb_b4", "tb_b4")),
            ("tb_b4", 3, S9, ("tb_hit", "tb_hit", "tb_n")))
    for name, off, src, arms in plan:
        if name:
            a.label(name)
        a.rd_c(S5)
        a.op("*", 4)
        a.op("+", RC_S + off)
        a.rd_a("M")
        a.rd_c(src, "-")                     # A = fr/fc - coord
        a.sign("right", "", *arms)
    a.label("tb_n")
    a.bump(S5, 1)
    a.jmp("tb_l")
    a.label("tb_hit")
    a.diff(S5, S3)                           # ti - si
    a.sign("right", "", "tr_fin", "tr_mv", "tr_fin")


def _t_finish(a: _Asm) -> None:
    """Header L | head<<5 | tail<<13 | om<<21 | im<<24, PC += 1."""
    a.label("tr_fin")                        # S5 = ti, S1 = tail
    a.setc(S6, 0)
    for grp, slot in (("ho", S3), ("hi", S5)):
        for i in range(MEN):
            if grp != "ho" or i:
                a.label(f"{grp}{i}")
            a.diff(MR_S + i, slot)
            nxt = f"{grp}{i + 1}" if i < 2 else \
                ("hi0" if grp == "ho" else "hd_l")
            a.sign("right", "", nxt, f"{grp}{i}b", nxt)
            a.label(f"{grp}{i}b")
            a.rd_c(S6)
            a.op("+", 1 << (21 + i if grp == "ho" else 24 + i))
            a.wr_c(S6)
    a.label("hd_l")
    a.rd_c(S7, "M")
    a.rd_c(S6, "+")
    a.wr_c(S6)                               # + L
    a.rd_c(S2)
    a.rd_a()
    a.op("%", 1 << 21)
    a.op("*", 32)
    a.go("right", "M")
    a.rd_c(S6, "+")
    a.wr_c(S6)                               # + head<<5 (cell 0)
    a.rd_c(S1)
    a.op("*", 8192)
    a.go("right", "M")
    a.rd_c(S6, "+")
    a.wr_c(S6)                               # + tail<<13
    a.rd_c(S2)
    a.op("-", 1)
    a.wr_c(S5)
    a.rd_c(S6)
    a.wr_at(S5)                              # header word
    a.bump(PC_S, 1)
    a.label("tr_nx")
    a.rd_c(S0)
    a.op("+", 1)
    a.wr_c(S0)
    a.jmp("tr_q")


def _build_p1_asm(phases: int = 9) -> _Asm:
    """The controller program; ``phases`` gates how much is built."""
    a = _Asm()
    a.go("mid", "@")
    _p1_ingest(a)
    if phases >= 2:
        _p1_rooms_walls(a, "mr0" if phases >= 3 else "em0")
    if phases >= 3:
        _p1_manrooms(a)
        _p1_cands(a)
        _p1_traces(a)
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


def _add_memory(cv, mx: int, cr: int, top: int = 0) -> None:
    """Rooms + wiring for the 312-slot ring; controller wall is at cr."""
    from .memory import P3R, P3W

    cv.put(top, mx, P3W)                  # rows top..top+10
    cv.put(top + 13, mx, P3R)
    cv.put(top + 23, mx, RELAY312)
    cv.pipe([(top + 2, cr + 1), (top + 2, mx - 3), (top + 3, mx - 3),
             (top + 3, mx - 1)])
    cv.pipe([(top + 18, mx - 1), (top + 18, cr + 2), (top + 9, cr + 2),
             (top + 9, cr + 1)])
    cv.pipe([(top + 11, mx + 2), (top + 12, mx + 2)])      # cmd fwd
    cv.pipe([(top + 11, mx + 16), (top + 12, mx + 16),
             (top + 12, mx + 9)])                          # ring W->R
    cv.cells[(top + 12, mx + 9)] = "v"    # terminal bend into P3R top
    cv.pipe([(top + 21, mx + 10), (top + 22, mx + 10), (top + 22, mx - 3),
             (top + 27, mx - 3), (top + 27, mx - 1)])      # R -> RELAY
    serp = _serpentine(top + 14, top + 26, mx + 15, 25)
    cv.pipe([(top + 26, mx + 13), (top + 26, mx + 14)] + serp
            + [(top + 13, serp[-1][1]), (top + 13, mx + 18),
               (top + 12, mx + 18), (top + 11, mx + 18)])


def _ring(cv, top: int, right: int, far_off: int = 8) -> None:
    """Private FIFO scratch ring on a stage's right wall (s2-rig shape)."""
    from .lllm_scan import build_relay

    rl = right + 5
    cv.put(top + 1, rl, build_relay())
    cv.pipe([(top + 2, right + 1), (top + 2, rl - 1)])
    far = rl + far_off
    cv.pipe([(top + 3, rl + 6), (top + 3, far), (top + 9, far),
             (top + 9, right + 1)])


def build_scan3_machine() -> str:
    """The full SCAN3 chain: I -> S1(v2) -> SR -> P1(+memory) -> S2 -> O.

    Stages stack vertically, left walls at col 5; each stage's private
    ring/memory hangs on its right wall (the geometry each stage was
    sim-verified with).  Stage outputs leave on left-wall row 6 and
    descend the col-2 corridor to the next stage's row-2 input, so
    every stage keeps exactly one incoming and one outgoing stream
    pipe on its left wall and its scratch on the right.
    """
    from .canvas import Canvas
    from .lllm_scan import build_scan_room_v2

    cv = Canvas()
    s1 = build_scan_room_v2()
    cv.put(0, 5, s1)
    cv.put(1, 0, ["+-+", "|I|", "+-+"])
    cv.pipe([(2, 3), (2, 4)])
    _ring(cv, 0, 5 + len(s1[0]) - 1, far_off=12)
    sr = build_sr_room()
    y = len(s1) + 2
    cv.put(y, 5, sr)
    cv.pipe([(6, 4), (6, 2), (y + 2, 2), (y + 2, 4)])
    _ring(cv, y, 5 + len(sr[0]) - 1)
    p1 = _compile3(_build_p1_asm(3).fsm())
    yp = y + len(sr) + 2
    cv.put(yp, 5, p1)
    cv.pipe([(y + 6, 4), (y + 6, 2), (yp + 2, 2), (yp + 2, 4)])
    cr = 5 + len(p1[0]) - 1
    _add_memory(cv, cr + 8, cr, top=yp)
    s2 = build_s2_room()
    ys = yp + len(p1) + 2
    cv.put(ys, 5, s2)
    cv.pipe([(yp + 6, 4), (yp + 6, 2), (ys + 2, 2), (ys + 2, 4)])
    _ring(cv, ys, 5 + len(s2[0]) - 1)
    cv.put(ys + 5, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(ys + 6, 4), (ys + 6, 3)])
    return cv.render()


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
