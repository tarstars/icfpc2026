"""Packet Reassembly rebuilt around an offset-addressed window (tcp_01).

`alexey_tcp_model.py` holds the validated algorithm; this module builds the
machine. Shape:

    I -> PUMP -> O,  with PUMP <-> RELAY carrying the 16-slot window ring.

The pump keeps `expected` in B for the whole program. Every op on the main
path preserves B (`r s m d a x ] b X`, digits, arrows); only the `M` that
bumps `expected` after an emit rewrites it.

Per packet:

    r -               d = seq - expected            (B keeps expected)
    b ]]]] d          d >= 16 -> emit -1 and halt   (6 cells, not 15 m's)
    X on d            d == 0 rotates 15, see the debt note below
    1 N s             drop a -1 marker into the ring
    loop r s          rotate BP slots
    r  r  s           discard the empty slot, read val, write it
    loop r X s        rotate on until the marker returns, dropping it
    loop r X ...      drain: emit while the head is nonzero

**The rotation debt.** The drain stops by reading a zero it cannot put back
at the head, so each packet leaves the ring rotated one slot forward. The
rotation count compensates: d-1 normally, 15 when d == 0. That is the only
reason the `X` on d exists.

**Pipe discipline.** The pump has two incoming and two outgoing pipes, so
every `r` and `s` must be placed where `nearest` resolves the way we mean.
`assert_pipe_map` pins the layout that `build_skeleton` produces:

    reads   interior rows 1-10 reach INPUT;   rows 15-24 reach RING-IN
    writes  interior rows 1-9  reach OUTPUT;  rows 20-24 reach RING-OUT

With the pump this tall the zones are simply top and bottom: packet reads
and emits live in the top third, all ring traffic in the bottom third, and
rows 11-14 / 10-19 are the sloping middle that must be audited before use.
This is why the layout puts `r seq`, `r val` and the `-1` emit up top and
every ring loop down below.

Read instructions for the packet stream therefore live at the top of the
room, ring traffic at the bottom right, and emits on the left.
"""

from __future__ import annotations

from .canvas import Canvas
from .sim import Machine

# --- build state -------------------------------------------------------
# DONE: algorithm (alexey_tcp_model, 6/6 public, 258 ring ops/case), the room
#       and pipe skeleton, the pipe-zone map with assertions, and all ten
#       layout nodes (build_wip) -- it builds, parses and holds the zones.
# FIXED: the init used to descend col 9 and stepped on (3,9), a ']' of the
#       prologue (BP 16 -> 8, so the ring got 8 zeros), and on (16,9), the
#       drain's 's' (a stray value into the ring). Nothing was overwritten,
#       so Grid could not catch it: the conflict was between a WALK and
#       cells another phase owns. The pump gained two columns and the init
#       now descends col 17, which no phase occupies. Traced clean: BP stays
#       16 the whole way down.
# TODO: FOUND. Diffed against alexey_tcp_model on the shortest stream: the
#       machine matches the model exactly through init (ring seeded, BP
#       16->0), the prologue (seq=0, d=0), the X into the d==0 arm (BP=15)
#       and the -1 marker injection. It then spins forever in the rotate
#       loop, BP pinned, because the body had no `m`. FIXED: the loop moved
#       to rows 23-24 (the only run of five free cells) and its body is now
#       `^ m s r <`.
#       Still failing: a packet does not complete. Trace next from the
#       rotate exit at (23,7) through the discard and the insert.
#
#       Worth adding: a walk checker that runs the man and flags every cell
#       he executes that belongs to a different phase. Grid only guards
#       placement; this class of bug needs the trace.
#
# The drain is the one node with a real constraint behind its placement:
# it must both read the ring and write the output, and rows 15-17 at low
# columns are the only band where `nearest` gives RING for reads and OUTPUT
# for writes at the same time.
#
# Estimated landing: ~750k at this room size, against tcp_00's 20,028k and
# the best known 593k. Compaction comes after it is correct.

SLOTS = 16
PUMP_H, PUMP_W = 24, 18         # pump interior (correctness first, golf later)
PUMP_TOP, PUMP_LEFT = 0, 5      # canvas position of the pump's top-left corner

# Pipe segment cells, by role. These are the cells `nearest` measures to.
INPUT_END = (1, 4)
OUTPUT_SRC = (5, 4)
RING_OUT_SRC = (PUMP_TOP + PUMP_H + 2, 16)
RING_IN_END = (PUMP_TOP + PUMP_H + 2, 10)


def build_skeleton(interior: list[str] | None = None) -> str:
    """Rooms and the four pipes, with an optional pump interior.

    `interior` is PUMP_H rows of PUMP_W characters; spaces where the man
    should simply walk on. The ring-in pipe is 23 cells, comfortably above
    the 17 values that ride it (16 slots plus the injected marker).

    The pump is deliberately roomy: get the machine correct first, then
    golf. At 258 ring ops per case even this 23x20 box projects to ~750k,
    against tcp_00's 20,028k.
    """
    if interior is None:
        interior = [" " * PUMP_W for _ in range(PUMP_H)]
    assert len(interior) == PUMP_H and all(len(r) == PUMP_W for r in interior)

    cv = Canvas()
    cv.put(0, 0, ["+-+", "|I|", "+-+"])                 # I: rows 0-2
    cv.put(4, 0, ["+-+", "|O|", "+-+"])                 # O: rows 4-6
    edge = "+" + "-" * PUMP_W + "+"
    cv.put(PUMP_TOP, PUMP_LEFT,
           [edge] + ["|" + row + "|" for row in interior] + [edge])
    relay_top = PUMP_TOP + PUMP_H + 4
    cv.put(relay_top, 13, ["+----+", "|>s@v|", "|^r <|", "+----+"])   # relay

    cv.pipe([(1, 3), (1, 4)])                            # I -> pump left wall
    cv.pipe([(5, 4), (5, 3)])                            # pump left wall -> O
    bot = PUMP_TOP + PUMP_H + 2        # first free row below the pump wall
    cv.pipe([(bot, 16), (bot + 1, 16)])                   # ring out -> relay
    cv.pipe([(relay_top + 2, 12), (relay_top + 2, 2), (bot + 1, 2),
             (bot + 1, 10), (bot, 10)])                   # ring in
    return cv.render()


def pipe_map(text: str) -> dict:
    """{(row, col): (incoming_role, outgoing_role)} for every pump interior cell."""
    machine = Machine.parse(text)
    pump = [r for r in machine.rooms if r.contains_interior(1, PUMP_LEFT + 1)][0]
    roles = {INPUT_END: "INPUT", OUTPUT_SRC: "OUTPUT",
             RING_OUT_SRC: "RING-OUT", RING_IN_END: "RING-IN"}

    class Probe:
        pass

    out = {}
    for r in range(1, PUMP_H + 1):
        for c in range(PUMP_LEFT + 1, PUMP_LEFT + 1 + PUMP_W):
            probe = Probe()
            probe.r, probe.c, probe.room = r, c, pump
            inc = machine._nearest_incoming(probe)
            outg = machine._nearest_outgoing(probe)
            out[(r, c)] = (roles.get(inc.cells[-1], "?"),
                           roles.get(outg.cells[0], "?"))
    return out


def assert_pipe_map(text: str | None = None) -> None:
    """Fail loudly if the geometry stops resolving pipes the way the code assumes."""
    mapping = pipe_map(text or build_skeleton())
    for (r, c), (inc, outg) in mapping.items():
        if r <= 10:
            assert inc == "INPUT", f"read at {(r, c)} reaches {inc}, wanted INPUT"
        if r >= 15:
            assert inc == "RING-IN", f"read at {(r, c)} reaches {inc}, wanted RING-IN"
        if r <= 9:
            assert outg == "OUTPUT", f"write at {(r, c)} reaches {outg}, wanted OUTPUT"
        if r >= 20:
            assert outg == "RING-OUT", f"write at {(r, c)} reaches {outg}, wanted RING-OUT"


# --- layout helper -------------------------------------------------------
class Grid:
    """1-based pump interior with collision detection.

    Every layout mistake in this build so far was a silent overwrite: a
    horizontal `put` running across cells another phase already owned, or a
    vertical literal written as a string. `put` refuses to overwrite, and
    `col` writes downward, so those fail loudly at build time.
    """

    def __init__(self, h: int = PUMP_H, w: int = PUMP_W):
        self.h, self.w = h, w
        self.g = [[" "] * (w + 2) for _ in range(h + 2)]

    def put(self, r: int, c: int, text: str) -> None:
        for i, ch in enumerate(text):
            if ch == " ":
                continue
            if self.g[r][c + i] != " ":
                raise AssertionError(
                    f"collision at {(r, c + i)}: {self.g[r][c + i]!r} vs {ch!r}"
                )
            self.g[r][c + i] = ch

    def col(self, r: int, c: int, text: str) -> None:
        """Write downward — vertical literals and branch arms."""
        for i, ch in enumerate(text):
            if ch == " ":
                continue
            if self.g[r + i][c] != " ":
                raise AssertionError(
                    f"collision at {(r + i, c)}: {self.g[r + i][c]!r} vs {ch!r}"
                )
            self.g[r + i][c] = ch

    def rows(self) -> list[str]:
        return ["".join(self.g[r][1:self.w + 1]) for r in range(1, self.h + 1)]


def build_wip() -> str:
    """All ten nodes placed. Builds and parses; still hits the tick cap.

    History of faults found and fixed here, each by one trace:
      1. init descended col 9 and stepped on the prologue's ']' (BP 16->8)
         and the drain's 's' -- fixed by giving the pump two spare columns
         and descending col 17, which no phase owns.
      2. the rotate loop body was `^ s r <`, no decrement, so it spun with
         BP pinned -- fixed by moving the loop to rows 23-24, the only place
         with five free cells in a row, and writing the body as `^ m s r <`.
    Still failing: a packet does not complete. Next trace should start from
    the rotate loop's exit at (23,7) and follow the discard and insert.
    """
    g = Grid()
    # init: read n and drop it, A=0, BP=16, seed the ring with 16 zeros.
    # The descent uses col 17 because no phase occupies it -- the prologue
    # fills row 3 across cols 2-11 and the drain fills row 16.
    g.put(1, 1, "@r`16`b0"); g.put(1, 17, "v")
    g.put(19, 17, "<"); g.put(19, 3, "v")
    g.put(20, 3, ">   d"); g.put(21, 3, "^ ms<"); g.put(20, 8, "^")
    g.put(2, 8, "<"); g.put(2, 2, "v")
    # packet prologue and the three arms
    g.put(3, 2, ">r-b]]]]dX"); g.col(3, 12, "v`15`b<")
    g.col(4, 11, "bm"); g.put(9, 11, "v")
    g.col(4, 10, "1N<"); g.put(6, 2, "Hs")
    g.col(10, 11, "1Ns")                    # inject the -1 marker
    # marker done -> west along row 18 -> down col 2 -> rotate loop
    g.col(13, 11, "     <"); g.put(18, 2, "v"); g.col(19, 2, "    >")
    g.put(23, 3, "   d")                    # rotate test
    g.put(24, 2, "^msr<")                   # body: the `m` is what was missing
    g.put(23, 7, "v"); g.put(24, 7, ">"); g.put(24, 16, "^")
    g.put(17, 16, "r")                      # discard the empty slot
    # val: up col 16 into the input zone, back down col 14 to the insert
    g.put(2, 15, "r"); g.put(2, 16, "<"); g.put(2, 14, "v")
    g.col(13, 14, "s<"); g.put(14, 13, "v")
    g.put(21, 13, "<"); g.put(21, 10, "v")
    # lap on until the marker returns
    g.put(22, 10, ">rX v"); g.put(23, 10, "^s<<"); g.put(21, 12, "^")
    # drain: rows 15-17 are the only band that reads RING and writes OUTPUT
    g.put(15, 2, ">rX>s^"); g.put(16, 4, "s1+M0s")
    g.put(16, 10, "v"); g.put(17, 10, "<"); g.put(17, 2, "^")
    g.put(4, 7, "<"); g.put(4, 2, "^")
    return build_skeleton(g.rows())
