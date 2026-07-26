"""tcp_fast -- Packet Reassembly with a BIT-PACKED 15-slot window.

WHY THIS IS DIFFERENT FROM `alexey_tcp_v3` (the 37x37 live machine).

The live machine stores the reassembly window as 15 separate values in a
pipe ring, so every out-of-order packet relays 15 values through a room
(~8 ticks each) -- ~200 ticks/packet, and the pump that does it is large.

Here the window is three 50-bit words.  Slot `d` (1..15, relative to the
next expected sequence number) lives in ring position ``(d-1) % 3``, field
``(d-1) // 3`` of that word, each field 10 bits (values are 1..999, and 0
means "empty").  Consequences:

* an insert touches ONE word -- the ring is only 3 values long, so a full
  rotation is 3 relays instead of 15;
* a drain step is exactly ``pop head, /1024 -> (word>>10, low field),
  emit the low field, push the shifted word`` -- one `/` does the extract
  and the shift at once, and pushing the head to the tail IS the window
  shift, because renaming R[i] := R[i+1] maps slot d to slot d-1 with the
  field index unchanged for every d except d = 1,4,7,10,13, which are
  exactly the ones in the popped head (hence its >>10).

`exp` is not stored in the machine as such: it equals the number of values
emitted so far, so the room that forwards output owns it (as ``exp + 1``,
so one `-` yields ``d - 1`` directly, which is what the packing wants).

This module holds the reference model, the case/fuzz generators and the
generator for `submissions/tcp/tcp_07.man`.
"""

from __future__ import annotations

import random

WINDOW = 16          # a packet 16 or more ahead loses the stream
FIELDS = 5           # fields per word
BITS = 10            # bits per field
RING = 3             # words


def model_rounds(n: int, order: list[tuple[int, int]]) -> list[dict]:
    """Spec-level oracle: judge-shaped rounds for one arrival order."""
    exp = 0
    buf: dict[int, int] = {}
    rounds: list[dict] = []
    for idx, (seq, val) in enumerate(order):
        ins = [str(n), str(seq), str(val)] if idx == 0 else [str(seq), str(val)]
        if seq - exp >= WINDOW:
            rounds.append({"in": ins, "out": ["-1"]})
            break
        buf[seq] = val
        out = []
        while exp in buf:
            out.append(str(buf.pop(exp)))
            exp += 1
        rounds.append({"in": ins, "out": out})
    return rounds


def ring_rounds(n: int, order: list[tuple[int, int]]) -> list[dict]:
    """Same outputs, computed the way the MACHINE computes them.

    Cross-checking this against `model_rounds` validates the packing, not
    just the specification.
    """
    exp = 0
    ring = [0, 0, 0]
    rounds: list[dict] = []
    for idx, (seq, val) in enumerate(order):
        ins = [str(n), str(seq), str(val)] if idx == 0 else [str(seq), str(val)]
        dm = seq - (exp + 1)          # what the exp room sends
        if dm >= 0:
            f, w = divmod(dm, RING)
            if f >= FIELDS:           # loss: d >= 16
                rounds.append({"in": ins, "out": ["-1"]})
                break
            payload = val << (BITS * f)
            assert ring[w] & (1023 << (BITS * f)) == 0, "slot not empty"
            ring[w] |= payload
            rounds.append({"in": ins, "out": []})
            continue
        assert dm == -1, dm
        out = [str(val)]
        exp += 1
        while True:
            # one pop-push per value already emitted: that rotation IS the
            # window shift, and it yields the next candidate at the same time
            q, v = divmod(ring[0], 1 << BITS)
            ring = ring[1:] + [q]
            if v == 0:
                break
            out.append(str(v))
            exp += 1
        rounds.append({"in": ins, "out": out})
    return rounds


def case(name: str, n: int, order: list[tuple[int, int]]) -> dict:
    return {"name": name, "rounds": model_rounds(n, order)}


def in_order(n: int) -> list[tuple[int, int]]:
    return [(i, 100 + i) for i in range(n)]


def reversed_block(n: int, block: int = 16) -> list[tuple[int, int]]:
    order = []
    for base in range(0, n, block):
        chunk = list(range(base, min(base + block, n)))
        order += [(s, 1 + (s * 37) % 999) for s in reversed(chunk)]
    return order


def fuzz_orders(count: int, seed: int = 0) -> list[tuple[str, int, list]]:
    """Randomised streams that stay inside the 16-window, plus loss ones."""
    rng = random.Random(seed)
    out = []
    for i in range(count):
        n = rng.choice([1, 2, 3, 5, 8, 15, 16, 17, 31, 32, 47, 48])
        vals = [rng.randint(1, 999) for _ in range(n)]
        pending = list(range(n))
        arrived: set[int] = set()
        order: list[tuple[int, int]] = []
        exp = 0
        while pending:
            lim = [s for s in pending if s - exp < WINDOW]
            s = rng.choice(lim[: rng.randint(1, len(lim))])
            pending.remove(s)
            arrived.add(s)
            order.append((s, vals[s]))
            while exp in arrived:
                exp += 1
        if i % 5 == 4 and n > 16:      # force a loss stream
            order = [(WINDOW + rng.randint(0, n - WINDOW - 1), vals[0])]
        out.append((f"fuzz{i}", n, order))
    return out


# --------------------------------------------------------------- walker
DIRS = {"^": (-1, 0), ">": (0, 1), "v": (1, 0), "<": (0, -1)}
CW = {"^": ">", ">": "v", "v": "<", "<": "^"}
CCW = {v: k for k, v in CW.items()}


class Walk:
    """Lay instructions along a little man's path inside one room.

    Rooms are written as code, not as ASCII art: every cell is placed at
    the position the man actually reaches, so a mis-drawn corner is an
    assertion, not a silent wrong turn.
    """

    def __init__(self, cells: dict, r: int, c: int, d: str = ">"):
        self.cells, self.r, self.c, self.d = cells, r, c, d

    def _put(self, ch: str):
        key = (self.r, self.c)
        old = self.cells.get(key)
        assert old in (None, ch), f"cell {key} is {old!r}, want {ch!r}"
        self.cells[key] = ch
        self.r += DIRS[self.d][0]
        self.c += DIRS[self.d][1]

    def op(self, text: str):
        """Place one instruction per character, walking forward."""
        for ch in text:
            self._put(ch)
        return self

    def turn(self, d: str):
        self.d = d
        self._put(d)
        return self

    def lit(self, value: int):
        """A numeric literal, written so it reads `value` in walk order."""
        for ch in "`" + str(value) + "`":
            self._put(ch)
        return self

    def halt(self):
        self.cells[(self.r, self.c)] = "H"
        return self

    def fork(self, ch: str):
        """Place a branch cell; return (straight, cw, ccw) walkers."""
        r, c, d = self.r, self.c, self.d
        self._put(ch)
        return (
            Walk(self.cells, r + DIRS[d][0], c + DIRS[d][1], d),
            Walk(self.cells, r + DIRS[CW[d]][0], c + DIRS[CW[d]][1], CW[d]),
            Walk(self.cells, r + DIRS[CCW[d]][0], c + DIRS[CCW[d]][1], CCW[d]),
        )

    def to(self, r: int, c: int, d: str):
        """Jump the cursor (used to continue a path from a fork target)."""
        self.r, self.c, self.d = r, c, d
        return self


def _room(cells: dict, rows: int, cols: int) -> list[str]:
    """Wrap an interior cell map in walls; assert nothing escaped."""
    for (r, c) in cells:
        assert 0 <= r < rows and 0 <= c < cols, f"cell ({r},{c}) outside room"
    out = ["+" + "-" * cols + "+"]
    for r in range(rows):
        out.append("|" + "".join(cells.get((r, c), " ") for c in range(cols)) + "|")
    out.append("+" + "-" * cols + "+")
    return out


# ------------------------------------------------------------------ rooms
# E -- owns `exp + 1` in B, parses input, forwards output, counts emits.
#   incoming: IN (bottom col 6), FB (bottom col 1)
#   outgoing: TO_P (top col 9), TO_O (top col 2)
E_ROWS, E_COLS = 8, 11
E_PORTS = {"IN": ("bottom", 6), "FB": ("bottom", 1),
           "TO_P": ("top", 9), "TO_O": ("top", 2)}


def build_e() -> list[str]:
    k: dict = {}
    # B is `exp` (0 at spawn); swallow the stream length, then loop
    Walk(k, 4, 5, ">").op("@").op("r").op("  ").turn("v").op(" ") \
        .turn("<").op("     ")
    m = Walk(k, 7, 4, ">").op(">").op("r-b").op("s").op("]").turn("^")
    m.op("]]]")                                   # BP = d >> 4: nonzero = lost
    _, _, lost = m.fork("a")
    lost.op("1N").op("  ").op("s")                # -1, then park in main
    nxt = Walk(k, 2, 10, "^").turn("<")
    drain, ins, _ = nxt.fork("X")                 # d == 0 drains, d > 0 stores
    ins.turn("<").op("r").op("s").op("  ").turn("v").op("     ")
    drain.op("r").op("  ").op("s").op(" ").op("1+M").turn("v")
    fb = Walk(k, 3, 0, ">").op(">").op("r")
    exit_, emit, _ = fb.fork("X")
    emit.op("s").op("1+").turn("<").op("M").turn("^").op("   ")
    exit_.turn("v").op("  ").turn("v").turn(">")
    return _room(k, E_ROWS, E_COLS)


# P -- turns dm into (w, payload); detects loss.  One pipe in, one out, so
# nearest-pipe resolution is trivial here.
P_ROWS, P_COLS = 4, 15
P_PORTS = {"FROM_E": ("bottom", 3), "TO_C": ("top", 11)}


def build_p() -> list[str]:
    k: dict = {}
    m = Walk(k, 1, 0, ">").op(">@r").op("M1W-")       # A = d - 1
    ins0, insgt, drn = m.fork("X")
    drn.turn("<").op("s").op("     ").turn("v")       # dm == -1 straight to C
    insgt.turn(">").turn("^")                         # dm > 0 rejoins dm == 0
    ins0.op(">M3W/").op(" ").turn("v").op(" ").turn("<")
    tail = Walk(k, 3, 13, "<").op("Ws")               # w to C
    tail.op("WM").lit(10).op("W*M").op("r{").turn("^").op("s")
    return _room(k, P_ROWS, P_COLS)


# C -- ring controller.  Three unrolled "rotate one word" blocks: the first
# one whose backpack counter has run out ORs the payload in and then sets
# the backpack positive again (`b` on a value that is >= 1 because the
# payload is), so the later blocks always take the plain relay arm.
C_ROWS, C_COLS = 12, 16
C_PORTS = {"FROM_P": ("bottom", 4), "RING_IN": ("bottom", 11),
           "FB": ("top", 4), "RING_OUT": ("top", 11)}


def _c_block(k: dict, r: int, c: int, east: bool):
    """One rotate-a-word block; returns the walker leaving it, heading south."""
    d, turn = (">", "d") if east else ("<", "a")
    step = 1 if east else -1
    w = Walk(k, r, c, d).op("r")                      # A = ring word
    orm, cw, ccw = w.fork(turn)                       # skip while BP > 0
    skip = cw if east else ccw
    orm.op("|").op("s").op("b").turn("v")             # insert, then guard BP
    skip.turn(d).op("s").op("m").op(" ").turn("v")
    return Walk(k, r + 2, c + 5 * step, "v")


def build_c() -> list[str]:
    k: dict = {}
    # drain loop: B = 1024, pop head, /1024 gives (word>>10, low field)
    Walk(k, 0, 5, ">").op(">").lit(1024).op("M").op("r/").turn("v")
    dl = Walk(k, 1, 15, "v").turn("<").op("sW").op("         ")
    done, emit, _ = dl.fork("X")                      # low field > 0 -> emit
    emit.turn(">").op("s")                            # to E, then loop again
    done.op("0").turn("v").op("s").op(" ")            # 0 terminator to E
    # main: tag from P (-1 drain, -2 loss, else w), then payload
    m = Walk(k, 4, 0, ">").op(">>").op(" ").op("r")
    ins0, insgt, ctl = m.fork("X")
    insgt.turn(">").turn("^")
    _, drainw, lossw = ctl.op("b").fork("x")          # -1 drain, -2 loss
    lossw.op("1N").op("s").halt()                     # loss -> -1 to E
    drainw.turn("^").op(" ")                          # rejoin the drain loop
    ins0.op(">").op("b").op("r").op("M")              # BP = w, B = payload
    _c_block(k, 4, 9, True)
    Walk(k, 6, 14, "v").turn("<")
    _c_block(k, 6, 13, False)
    Walk(k, 8, 8, "v").turn(">")
    _c_block(k, 8, 9, True)
    Walk(k, 10, 14, "v").turn("<").op(" ").turn("<").op("           ")\
        .turn("^").op("     ")
    Walk(k, 11, 0, ">").op("@0").op("       ").op("sss").turn("^")
    return _room(k, C_ROWS, C_COLS)


R_ROWS, R_COLS = 3, 3


def build_r() -> list[str]:
    """Ring relay: a six-cell cycle, so one word costs six ticks."""
    k: dict = {}
    Walk(k, 0, 0, ">").op("@").turn(">").turn("v").op("r")\
        .turn("<").turn("^").op("s")
    return _room(k, R_ROWS, R_COLS)


def build_io(ch: str) -> list[str]:
    return ["+-+", "|" + ch + "|", "+-+"]


# ------------------------------------------------------------------ layout
# Room origins (top row, left col).  Port wall cells are derived from the
# interior port columns declared with each room.
LAYOUT = {
    "E": (0, 4), "O": (12, 6), "I": (12, 11), "P": (12, 18),
    "R": (21, 20), "C": (21, 0),
}
C_PORT_COLS = {"FROM_P": 4, "RING_IN": 13, "FB": 2, "RING_OUT": 15}


def build() -> str:
    """Assemble the machine.  Every port of E is on its floor and every
    port of C on its ceiling, so nearest-pipe resolution is decided by
    column alone inside those two rooms."""
    from .canvas import Canvas
    cv = Canvas()
    for name, room in (("E", build_e()), ("O", build_io("O")),
                       ("I", build_io("I")), ("P", build_p()),
                       ("R", build_r()), ("C", build_c())):
        cv.put(*LAYOUT[name], room)

    def pipe(points, last):
        cv.pipe(points)
        cv.cells[points[-1]] = last

    pipe([(11, 12), (10, 12), (10, 11)], "^")           # I -> E.IN
    pipe([(10, 7), (11, 7)], "v")                       # E.TO_O -> O
    pipe([(10, 14), (11, 14), (11, 20)], "v")           # E.TO_P -> P
    pipe([(16, 17), (16, 5), (20, 5)], "v")             # P -> C.FROM_P
    pipe([(20, 3), (10, 3), (10, 6)], "^")              # C.FB -> E.FB
    pipe([(20, 16), (19, 16), (19, 22), (20, 22)], "v")  # C.RING_OUT -> R
    pipe([(23, 25), (23, 26), (18, 26), (18, 14), (20, 14)], "v")  # R -> C
    return cv.render()


# ------------------------------------------------- compact layout (tcp_08)
# Identical room interiors, repacked.  Two observations drive it:
#   * `_nearest_outgoing/incoming` look only at a pipe's END cell, so a port
#     may sit anywhere on a wall as long as the ranking of the distances from
#     each s/r cell is unchanged.  C's ring ports therefore move to its RIGHT
#     wall (checked below), which puts the relay next door: the ring pipes go
#     from 8 + 24 cells to 2 + 2.
#   * E (13 wide) and P (17 wide) side by side is 31 columns; C (14 tall)
#     underneath makes 31 rows.  35x35 -> 31x31, footprint 1225 -> 961.
# C's ring ports on the right wall, interior rows: RING_IN 3, RING_OUT 5.
# The binding constraints are the two `r` cells at interior (4,9) and (8,9),
# which must still prefer RING_IN over FROM_P: |4-i| + 7 < 10 keeps i in
# [2, 6].  Every other s/r cell has slack of three or more.
LAYOUT_C = {
    "E": (0, 0), "O": (12, 4), "I": (12, 8), "P": (6, 14),
    "R": (20, 20), "C": (17, 0),
}


def build_compact() -> str:
    """The 31x31 repack: same rooms, new placement and pipes."""
    from .canvas import Canvas
    cv = Canvas()
    for name, room in (("E", build_e()), ("O", build_io("O")),
                       ("I", build_io("I")), ("P", build_p()),
                       ("R", build_r()), ("C", build_c())):
        cv.put(*LAYOUT_C[name], room)

    def pipe(points, last):
        cv.pipe(points)
        cv.cells[points[-1]] = last

    # Three server rules shape the routing: a pipe's first cell must point
    # away from its room's wall, a pipe that merely runs alongside a wall
    # counts as connected to that room (so no pipe may graze a room it does
    # not serve), and one-cell pipes are rejected.  E.TO_P moves one column
    # east, to interior 10, which keeps every send margin at 2 or better.  P
    # hangs two rows below E so that its west wall reaches past E's corner:
    # a cell in the gap column beside E would parse as a second E -> P pipe.
    pipe([(10, 11), (11, 11), (11, 13), (10, 13)], ">")  # E.TO_P -> P
    pipe([(11, 9), (10, 9), (10, 7)], "^")              # I -> E.IN
    pipe([(10, 3), (11, 3), (11, 5)], "v")              # E.TO_O -> O
    pipe([(12, 15), (16, 15), (16, 5)], "v")            # P -> C.FROM_P
    pipe([(16, 2), (10, 2)], "^")                       # C.FB -> E.FB
    pipe([(23, 18), (23, 19)], ">")                     # C.RING_OUT -> R
    pipe([(21, 19), (21, 18)], "<")                     # R -> C.RING_IN
    return cv.render()
