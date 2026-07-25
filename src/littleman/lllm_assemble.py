"""LLLM final assembly: place the five component rooms and route pipes.

Topology (work order docs/architecture/claude_18_lllm_assembly_workorder.md):

    I -> SCAN -> CLASSIFY -> STEP <-> FETCH <-> RELAY
                              |
                              +-> DIST -> ADDRDRV/DATADRV/SWAPDRV -> LM-75

Rooms are LIFTED byte-identical from the component rigs; only placement and
pipe routing live here.
"""

from __future__ import annotations

from .canvas import Canvas

# ---------------------------------------------------------------- placement
# Three row bands, so no two components can ever share a cell:
#   band A rows    0.. 310  I, SCAN, SCAN's scratch relay
#   band B rows  320.. 510  CLASSIFY
#   band C rows  520.. 650  FETCH + relay, STEP + relay
#   band D rows  749.. 775  DIST + drivers + 16x16 display
SCAN_AT = (0, 6)          # identical to lllm_scan's own rig placement
CLASSIFY_AT = (320, 6)
STEP_BASE = (520, 0)      # lllm_step's rig coordinates are relative to this
DRAW_AT = (758, 20)       # place_display_block anchor (block: rows 749..774)

# free vertical corridors, all west of / east of every room
COL_SCAN_OUT = 4          # SCAN -> CLASSIFY
COL_REQ = 9               # STEP -> FETCH (from lllm_step's rig)
COL_DRAW = 10             # STEP -> DIST
COL_LOAD = 12             # CLASSIFY -> STEP, last leg
COL_LOAD_FAR = 140        # CLASSIFY -> STEP, east bypass around STEP
ROW_LOAD_FAR = 700        # ... and its southern crossing row
ROW_DRAW_IN = 760         # DIST attach row (DRAW_AT[0] + 2)


def build_machine() -> str:
    """The whole LLLM machine as .man text."""
    from . import lllm_classify, lllm_draw, lllm_fetch, lllm_scan, lllm_step

    cv = Canvas()
    _place_scan(cv, lllm_scan)
    _place_classify(cv, lllm_classify)
    _place_step_complex(cv, lllm_fetch, lllm_step)
    lllm_draw.place_display_block(cv, *DRAW_AT)
    _route_spine(cv, lllm_step)
    return cv.render()


def _place_scan(cv: Canvas, mod) -> None:
    """SCAN + its private scratch ring, geometry copied from build_scan_rig."""
    r0, c0 = SCAN_AT
    room = mod.build_scan_room()
    right = c0 + len(room[0]) - 1
    cv.put(r0, c0, room)
    cv.put(r0 + 1, 0, ["+-+", "|I|", "+-+"])
    cv.pipe([(r0 + mod.CMD_ROW, 3), (r0 + mod.CMD_ROW, c0 - 1)])
    relay_left = right + 5
    cv.put(r0 + 1, relay_left, mod.build_relay())
    cv.pipe([(r0 + mod.RING_OUT_ROW, right + 1), (r0 + mod.RING_OUT_ROW,
                                                  relay_left - 1)])
    far = relay_left + 8
    cv.pipe([(r0 + 3, relay_left + 6), (r0 + 3, far),
             (r0 + mod.RING_IN_ROW, far), (r0 + mod.RING_IN_ROW, right + 1)])


def _place_classify(cv: Canvas, mod) -> None:
    r0, c0 = CLASSIFY_AT
    cv.put(r0, c0, mod.build_classify_room())


def _place_step_complex(cv: Canvas, fetch_mod, step_mod) -> None:
    """FETCH + STEP and their two rings, shifted copy of build_step_rig."""
    br, bc = STEP_BASE
    sr, sc = br + step_mod.STEP_AT[0], bc + step_mod.STEP_AT[1]
    fr, fc = br + step_mod.FETCH_AT[0], bc + step_mod.FETCH_AT[1]
    cv.put(fr, fc, fetch_mod.build_fetch().render())
    cv.put(sr, sc, step_mod.build_step_room().render())
    cv.put(fr + 20, fc + 50, fetch_mod.build_relay().render())
    cv.put(sr + step_mod.SCR_OUT_ROW - 1, sc + 80,
           step_mod.build_step_relay().render())
    left, right = sc - 1, sc + step_mod.STEP_COLS + 2
    fleft = fc - 1
    # STEP <-> FETCH
    cv.pipe([(sr + step_mod.REQ_ROW, left), (sr + step_mod.REQ_ROW, COL_REQ),
             (fr + 2, COL_REQ), (fr + 2, fleft)])
    cv.pipe([(fr + 13, fleft), (fr + 13, fleft - 1), (sr - 1, fleft - 1),
             (sr - 1, sc + step_mod.RESP_COL)])
    cv.cells[(sr - 1, sc + step_mod.RESP_COL)] = "v"   # terminal bend
    # FETCH <-> RELAY, the >= 70 cell ring
    cv.pipe([(fr + 2, fc + 47), (fr + 2, fc + 67), (fr + 21, fc + 67),
             (fr + 21, fc + 56)])
    cv.pipe([(fr + 21, fc + 49), (fr + 21, fc + 48), (fr + 5, fc + 48),
             (fr + 5, fc + 47)])
    # STEP <-> its scratch relay
    cv.pipe([(sr + step_mod.SCR_OUT_ROW, right), (sr + step_mod.SCR_OUT_ROW,
                                                  sc + 79)])
    cv.pipe([(sr + step_mod.SCR_OUT_ROW + 1, sc + 86),
             (sr + step_mod.SCR_OUT_ROW + 1, sc + 87),
             (sr + step_mod.SCR_IN_ROW, sc + 87), (sr + step_mod.SCR_IN_ROW,
                                                   right)])


def _route_spine(cv: Canvas, step_mod) -> None:
    """SCAN -> CLASSIFY -> STEP -> DIST, the three cross-band pipes."""
    sr0, sc0 = SCAN_AT
    cr0, cc0 = CLASSIFY_AT
    br, bc = STEP_BASE
    sr, sc = br + step_mod.STEP_AT[0], bc + step_mod.STEP_AT[1]
    left = sc - 1
    scan_out = (sr0 + 6, sc0 - 1)                 # SCAN's rig RESP_ROW
    cls_in = (cr0 + 3, cc0 - 1)                   # CLASSIFY's PIPE_ROW
    cls_right = cc0 + 86                          # room is 86 wide
    cv.pipe([scan_out, (scan_out[0], COL_SCAN_OUT),
             (cls_in[0], COL_SCAN_OUT), cls_in])
    cv.pipe([(cls_in[0], cls_right), (cls_in[0], COL_LOAD_FAR),
             (ROW_LOAD_FAR, COL_LOAD_FAR), (ROW_LOAD_FAR, COL_LOAD),
             (sr + step_mod.LOAD_ROW, COL_LOAD), (sr + step_mod.LOAD_ROW, left)])
    cv.pipe([(sr + step_mod.DRAW_ROW, left), (sr + step_mod.DRAW_ROW, COL_DRAW),
             (ROW_DRAW_IN, COL_DRAW), (ROW_DRAW_IN, DRAW_AT[1] - 1)])


# --------------------------------------------------------------- diagnostics
def room_anchors() -> dict[tuple[int, int], str]:
    """(top, left) -> component name, for labelling a parsed machine."""
    from . import lllm_step

    br, bc = STEP_BASE
    sr, sc = br + lllm_step.STEP_AT[0], bc + lllm_step.STEP_AT[1]
    fr, fc = br + lllm_step.FETCH_AT[0], bc + lllm_step.FETCH_AT[1]
    dr, dc = DRAW_AT
    return {
        (SCAN_AT[0] + 1, 0): "I",
        SCAN_AT: "SCAN",
        (SCAN_AT[0] + 1, SCAN_AT[1] + 86): "SCANRELAY",
        CLASSIFY_AT: "CLASSIFY",
        (fr, fc): "FETCH",
        (fr + 20, fc + 50): "FETCHRELAY",
        (sr, sc): "STEP",
        (sr + lllm_step.SCR_OUT_ROW - 1, sc + 80): "STEPRELAY",
        (dr, dc): "DIST",
        (dr - 7, dc + 18): "ADDRDRV",
        (dr, dc + 19): "DATADRV",
        (dr + 7, dc + 20): "SWAPDRV",
        (dr - 3, dc + 46): "DISPLAY",
    }


def label_rooms(machine) -> dict[int, str]:
    anchors = room_anchors()
    out = {}
    for room in machine.rooms:
        out[id(room)] = anchors.get(
            (room.top, room.left), f"?@{room.top},{room.left}"
        )
    return out


def pipe_names(machine) -> dict[int, str]:
    names = label_rooms(machine)
    return {
        id(p): f"{names[id(p.source)]}->{names[id(p.dest)]}" for p in machine.pipes
    }


class Trace:
    """Per-pipe traffic log: how many values crossed, and when it stopped."""

    def __init__(self, machine):
        self.machine = machine
        self.names = pipe_names(machine)
        self.sent = {k: 0 for k in self.names}
        self.taken = {k: 0 for k in self.names}
        self.last_send = {k: 0 for k in self.names}
        self.last_take = {k: 0 for k in self.names}
        self.tick = 0
        self._install()

    def _install(self):
        m = self.machine
        put, take, tick = m._pipe_put, m._pipe_take, m._tick

        def wrapped_put(pipe, index, value):
            self.sent[id(pipe)] += 1
            self.last_send[id(pipe)] = self.tick
            return put(pipe, index, value)

        def wrapped_take(pipe, index):
            self.taken[id(pipe)] += 1
            self.last_take[id(pipe)] = self.tick
            return take(pipe, index)

        def wrapped_tick(res):
            self.tick = res.ticks
            return tick(res)

        m._pipe_put, m._pipe_take, m._tick = wrapped_put, wrapped_take, wrapped_tick

    def report(self) -> list[str]:
        """One line per pipe, in pipeline order, plus the stall verdict."""
        lines = [f"ticks: {self.tick}"]
        for key, name in sorted(self.names.items(), key=lambda kv: kv[1]):
            lines.append(
                f"  {name:24s} sent={self.sent[key]:6d}@{self.last_send[key]:<9d}"
                f" taken={self.taken[key]:6d}@{self.last_take[key]:<9d}"
            )
        return lines

    def stall(self) -> str:
        """The last pipe that moved a value: where the machine got to."""
        best = max(
            self.names,
            key=lambda k: max(self.last_send[k], self.last_take[k]),
        )
        return (
            f"last traffic: {self.names[best]} "
            f"send@{self.last_send[best]} take@{self.last_take[best]} "
            f"of {self.tick} ticks"
        )


def diagnose(text: str, rounds, max_ticks: int = 2_000_000) -> tuple:
    """Run one case under the judge's controller with a :class:`Trace`."""
    from . import alexey_walljudge
    from .judge import RoundController, normalize_case
    from .sim import Machine

    machine = Machine.parse(text)
    controller = RoundController(rounds)
    with alexey_walljudge._wall_tolerant():
        trace = Trace(machine)          # inside, so wall tolerance still applies
        res = machine.run(max_ticks=max_ticks, controller=controller)
    return res, trace, controller


def men_report(machine) -> list[str]:
    """Where every man stands at the end: the stall point, per component."""
    names = label_rooms(machine)
    lines = []
    for man in machine.men:
        state = "halted" if man.halted else ("blocked " + (man.wait_kind or "")
                                             if man.blocked else "running")
        rel = (man.r - man.room.top, man.c - man.room.left)
        lines.append(
            f"  {names[id(man.room)]:10s} at ({man.r},{man.c}) room-rel {rel} "
            f"glyph={machine.grid[man.r][man.c]!r} dir={man.direction} {state}"
        )
    return lines


def diagnose_case(name: str = "first steps", max_ticks: int = 2_000_000) -> list[str]:
    """Human-readable stall report for one public case."""
    import json
    import pathlib

    from .judge import normalize_case

    problem = json.loads(
        pathlib.Path(
            "data/small/problems/little-little-little-man.json"
        ).read_text()
    )
    case = next(c for c in problem["publicTestData"] if c["name"] == name)
    text = pathlib.Path("submissions/lllm/lllm_00.man").read_text()
    res, trace, controller = diagnose(text, normalize_case(case), max_ticks)
    lines = [
        f"case {name!r}: status={res.status} error={res.error}",
        f"rounds completed {controller.round_idx}/{len(controller.rounds)}"
        f"  frames seen {controller.frame_idx}",
        trace.stall(),
        *trace.report(),
        "men:",
        *men_report(res_machine(res, trace)),
    ]
    return lines


def res_machine(res, trace):
    return trace.machine


def audit_ports(text: str) -> list[str]:
    """Per-room r/s binding margins: which pipe every instruction reaches."""
    from .sim import Machine

    machine = Machine.parse(text)
    names = label_rooms(machine)
    pnames = pipe_names(machine)
    lines = []
    for room in machine.rooms:
        outs = machine.out_pipes.get(id(room), [])
        ins = machine.in_pipes.get(id(room), [])
        if len(outs) < 2 and len(ins) < 2:
            continue
        for kind, pipes, end in (("s", outs, 0), ("r", ins, -1)):
            if len(pipes) < 2:
                continue
            cells = {pnames[id(p)]: p.cells[end] for p in pipes}
            worst = None
            rows, cols = room.interior()
            for r in rows:
                for c in cols:
                    if machine.grid[r][c] != kind:
                        continue
                    d = sorted(
                        (abs(v[0] - r) + abs(v[1] - c), k)
                        for k, v in cells.items()
                    )
                    slack = d[1][0] - d[0][0]
                    if worst is None or slack < worst[0]:
                        worst = (slack, (r, c), d[0][1])
            if worst:
                lines.append(
                    f"{names[id(room)]:10s} {kind} margin={worst[0]} "
                    f"at {worst[1]} -> {worst[2]}"
                )
    return lines


def extract_room(text: str, top: int, left: int, rows: int, cols: int) -> list[str]:
    """The rows x cols block of the rendered machine at (top, left)."""
    lines = text.split("\n")
    out = []
    for r in range(top, top + rows):
        line = lines[r] if r < len(lines) else ""
        line = line + " " * (left + cols - len(line))
        out.append(line[left : left + cols])
    return out


def ring_cells(machine, a: str = "FETCH", b: str = "FETCHRELAY") -> int:
    """Total pipe cells on the two legs of a room-to-relay ring."""
    names = pipe_names(machine)
    return sum(
        len(p.cells)
        for p in machine.pipes
        if names[id(p)] in (f"{a}->{b}", f"{b}->{a}")
    )


def sweep(text: str | None = None, max_ticks: int = 500_000) -> list[str]:
    """Every public case: rounds completed, and where each halted man stands.

    This is the STEP agent's progress meter -- `rounds N/M` is exactly how
    many rounds the assembled machine already reproduces.
    """
    import json
    import pathlib

    from .judge import normalize_case

    if text is None:
        text = pathlib.Path("submissions/lllm/lllm_00.man").read_text()
    problem = json.loads(
        pathlib.Path("data/small/problems/little-little-little-man.json").read_text()
    )
    lines = []
    for case in problem["publicTestData"]:
        res, tr, ctl = diagnose(text, normalize_case(case), max_ticks)
        names = label_rooms(tr.machine)
        stops = [
            (names[id(m.room)], m.r - m.room.top, m.c - m.room.left)
            for m in tr.machine.men
            if m.halted
        ]
        lines.append(
            f"{case['name'][:22]:24s} rounds {ctl.round_idx}/{len(ctl.rounds)}"
            f"  status={res.status}  halted={stops}"
        )
    return lines


def binding_ir(text: str) -> dict:
    """`ir_export.machine_ir`'s resolution map, keyed by component name."""
    from . import ir_export
    from .sim import Machine

    ir = ir_export.machine_ir(text)
    names = label_rooms(Machine.parse(text))
    return {"resolution": ir["resolution"], "rooms": sorted(names.values()),
            "sha256": ir["sha256"]}
