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
#       Three routing faults found and fixed (see build_wip). A packet now
#       walks the whole flow: prologue, branch, marker, rotate, discard,
#       val, insert, lap, drain, next packet.
#
# FAULT 4 (design, not routing -- NOT yet fixed). The rotation-debt
#       compensation is wrong. Traced and reproduced on paper:
#
#         inject marker   [s0 s1 .. s15 M]
#         rotate 15 (d=0) [s15 M s0 s1 ..]     head is s15, not s0
#         discard+insert  s15 thrown away, VAL appended at the tail
#         lap to marker   [s0 s1 .. s14 VAL]
#         drain reads     s0                   should have read VAL
#
#       Rotating d-1 (15 when d==0) assumes the head is s1, the debt the
#       drain's terminating zero-read leaves behind. The first packet has
#       no such debt, so it misses by a whole window. Creating the debt in
#       init does not help: then the DRAIN misses, because it reads the
#       head assuming s0. The debt can serve the insert or the drain, never
#       both -- so the compensation has to go.
#
#       Chosen: (a) rotate exactly d and end the drain with a re-alignment
#       lap. ~500 ops per case instead of 258, still far better than
#       tcp_00; projected ~4M against 20M.
#
#       Rotating exactly d has a bonus: the whole `X` branch disappears.
#       No d==0 arm, no vertical `15` literal, no `m` -- BP = d is just
#       `b`. That is 12 cells and a three-way merge gone.
#
# THE REAL BLOCKER is not any single bug. Four of the faults so far were
#       the same shape: a walk crossing a cell another phase owns. Patching
#       them one at a time keeps producing the next one, because routes are
#       being threaded through whatever cells happen to be free at the
#       time. What this needs before more layout work:
#         1. reserve highway columns/rows up front, exclusive to routing,
#            and place phases only in the remaining blocks;
#         2. write the walk checker -- run the man, flag every executed
#            cell belonging to a different phase. Grid guards placement,
#            assert_pipe_map guards pipe zones, and this third checker is
#            the one that would have caught all four.
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


# --- layout helpers ------------------------------------------------------
class Grid:
    """Pump interior with collision detection, cell ownership and highways.

    Three guards, one per class of bug this build actually produced:

    * `put`/`col` refuse to overwrite — catches a phase written across
      cells another phase already owns.
    * `reserve_row`/`reserve_col` mark cells as routing-only. Placing a
      phase there raises, and routing outside them is visible in the
      ownership map. Routes threaded through whatever happened to be free
      is what produced four of the five faults in this machine.
    * `owner` records which phase owns each cell, so `walk_report` can say
      whose cell the man just executed.
    """

    ROUTE = "route"

    def __init__(self, h: int = PUMP_H, w: int = PUMP_W):
        self.h, self.w = h, w
        self.g = [[" "] * (w + 2) for _ in range(h + 2)]
        self.owner: dict[tuple[int, int], str] = {}
        self.reserved: set[tuple[int, int]] = set()

    # -- highways ---------------------------------------------------------
    def reserve_row(self, r: int) -> None:
        self.reserved.update((r, c) for c in range(1, self.w + 1))

    def reserve_col(self, c: int) -> None:
        self.reserved.update((r, c) for r in range(1, self.h + 1))

    def free_rows(self) -> list[int]:
        return [r for r in range(1, self.h + 1) if (r, 1) not in self.reserved]

    # -- placement --------------------------------------------------------
    def _place(self, r: int, c: int, ch: str, phase: str) -> None:
        if ch == " ":
            return
        if self.g[r][c] != " ":
            raise AssertionError(
                f"{phase}: collision at {(r, c)} with "
                f"{self.owner.get((r, c), '?')}'s {self.g[r][c]!r}"
            )
        if (r, c) in self.reserved and phase != self.ROUTE:
            raise AssertionError(
                f"{phase}: {(r, c)} is a reserved highway cell; "
                f"place phases off the highways"
            )
        if (r, c) not in self.reserved and phase == self.ROUTE:
            raise AssertionError(
                f"route cell {(r, c)} lies outside the reserved highways"
            )
        self.g[r][c] = ch
        self.owner[(r, c)] = phase

    def put(self, r: int, c: int, text: str, phase: str = "?") -> None:
        for i, ch in enumerate(text):
            self._place(r, c + i, ch, phase)

    def col(self, r: int, c: int, text: str, phase: str = "?") -> None:
        """Write downward — vertical literals and branch arms."""
        for i, ch in enumerate(text):
            self._place(r + i, c, ch, phase)

    def rows(self) -> list[str]:
        return ["".join(self.g[r][1:self.w + 1]) for r in range(1, self.h + 1)]


def walk_report(text: str, grid: Grid, inputs: list[int], max_ticks: int = 3000):
    """Run the pump man and report which phase owns each cell he executes.

    Returns (steps, phase_sequence). `steps` is one tuple per executed cell
    that carries an instruction: (tick, row, col, char, phase, A, B, BP).
    `phase_sequence` collapses runs, so a walk that strays into another
    phase shows up as that phase appearing where it does not belong —
    the fault that Grid cannot see, because nothing was overwritten.
    """
    machine = Machine.parse(text)
    lines = [list(line) for line in text.split("\n")]
    pump = [r for r in machine.rooms if r.contains_interior(1, PUMP_LEFT + 1)][0]
    man = [m for m in machine.men if m.room is pump][0]
    steps: list[tuple] = []
    original = machine._execute

    def traced(walker):
        if walker is man:
            ch = lines[walker.r][walker.c]
            if ch.strip():
                steps.append((
                    len(steps), walker.r, walker.c - PUMP_LEFT, ch,
                    grid.owner.get((walker.r, walker.c - PUMP_LEFT), "?"),
                    walker.A, walker.B, walker.BP,
                ))
        return original(walker)

    machine._execute = traced
    machine.run(max_ticks=max_ticks, inputs=list(inputs))
    sequence: list[str] = []
    for step in steps:
        if not sequence or sequence[-1] != step[4]:
            sequence.append(step[4])
    return steps, sequence
# Highways: nothing but routing goes here, and routing goes nowhere else.
# Four of the five faults in this build were a walk crossing a cell some
# phase owned; reserving the lanes up front makes that impossible rather
# than unlikely.
#
# NOT YET SOLVED -- route vs route. Highways stop a phase and a route from
# colliding, but ten connections share three highway columns, so they
# collide with each other. First full routing attempt walked
#   init -> route -> marker -> route -> drain
# instead of
#   init -> route -> seed -> route -> prologue -> route -> marker -> ...
# because init's descent down col 11 stepped on (5,11), a cell belonging
# to the prologue->marker connection, and rode it west.
#
# The fix is lane allocation, not more highways: a lane is a (column,
# row-range) segment owned by ONE connection, and Grid should refuse a
# second connection any cell inside it. Same shape as the phase guard, one
# level down. Until that exists, every added connection can silently break
# an earlier one -- which is exactly what the walk checker now surfaces in
# one line instead of a tick-cap.
HIGHWAY_COLS = (1, 11, 18)
HIGHWAY_ROWS = (5, 13, 18, 21)


def new_grid() -> Grid:
    g = Grid()
    for c in HIGHWAY_COLS:
        g.reserve_col(c)
    for r in HIGHWAY_ROWS:
        g.reserve_row(r)
    return g


def place_phases(g: Grid) -> None:
    """Phases only, each inside one block between highways.

    Blocks, and why each phase sits where it does (see the zone map at the
    top of the file): rows 1-4 read INPUT, rows 15-24 read RING, rows 1-9
    write OUTPUT, rows 20-24 write RING, and rows 15-17 are the only band
    that reads RING and writes OUTPUT at once -- which is why the drain
    lives there and nowhere else.
    """
    at = g.put
    at(1, 2, "@r`16`b0", "init")            # rows 1-4 x cols 2-10
    at(3, 2, ">r-b]]]]d", "prologue")       # d = seq - expected, delay test
    at(2, 12, "r", "val")                   # rows 1-4 x cols 12-17
    for i, ch in enumerate("1Ns"):
        at(6 + i, 3, ch, "marker")          # inject the -1 marker
    for i, ch in enumerate("1NsH"):
        at(6 + i, 12, ch, "loss")           # emit -1 and halt
    at(15, 2, ">rX>s", "drain"); at(16, 3, "s1+M0s", "drain")
    at(15, 13, "r", "discard")
    at(19, 2, ">   d", "rotate"); at(20, 2, "^msr<", "rotate")
    at(22, 2, ">rX v", "lap"); at(23, 2, "^s<<", "lap")


def build_wip() -> str:
    """Phases placed under the highway discipline; routes not yet threaded.

    `place_phases` raises if any phase lands on a highway, and Grid raises
    if a route is drawn off one, so the next step -- connecting the phases
    -- cannot reintroduce the fault class that cost this build three
    rounds. Run `walk_report` once the routes are in: it names the phase
    owning every cell the man executes, so a stray walk reads as an
    unexpected phase in the sequence instead of a tick-cap.
    """
    g = new_grid()
    place_phases(g)
    return build_skeleton(g.rows())
