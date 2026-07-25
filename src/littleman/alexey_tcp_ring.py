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

    reads   interior rows 1-4 reach INPUT;  rows 9-12 reach RING-IN
    writes  interior cols 1-2 reach OUTPUT;  cols 11-16 reach RING-OUT

Both boundaries slope, because `nearest` measures to the ring pipes below
the room: reads in rows 5-8 and writes in cols 3-10 flip role part-way
across. `assert_pipe_map` pins only the four corner zones that hold for
every row and column; anything between them must be audited before use.

Read instructions for the packet stream therefore live at the top of the
room, ring traffic at the bottom right, and emits on the left.
"""

from __future__ import annotations

from .canvas import Canvas
from .sim import Machine

SLOTS = 16
PUMP_H, PUMP_W = 12, 16         # pump interior (correctness first, golf later)
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
        if r <= 4:
            assert inc == "INPUT", f"read at {(r, c)} reaches {inc}, wanted INPUT"
        if r >= 9:
            assert inc == "RING-IN", f"read at {(r, c)} reaches {inc}, wanted RING-IN"
        if c <= PUMP_LEFT + 2:
            assert outg == "OUTPUT", f"write at {(r, c)} reaches {outg}, wanted OUTPUT"
        if c >= PUMP_LEFT + 11:
            assert outg == "RING-OUT", f"write at {(r, c)} reaches {outg}, wanted RING-OUT"
