"""LLM3 assembly: SCAN3 chain + STEP3 (live from disk) + DRAW chain.

    I -> S1 -> SR -> P1(+312-slot memory) -> S2 -> STEP3 <-> FETCH
                                                    |
                                                    +-> DIST -> drivers -> LM-75

SCAN3's rooms are placed with build_scan3_machine's EXACT rig geometry
(the O room dropped, its port re-routed to STEP3's LOAD).  The STEP3 room
is re-read from ``littleman.llm_step3`` on every build: whatever room
builder exists on disk is used, else a wall-only stub with the claude_25
planned dimensions, so the machine always assembles and the diagnostic
can say precisely where execution stalls.

NOT YET WIRED: phase C's ring2 (pipe-segment scratch, south wall ~row
220+) has no pinned ports in llm_step3; when its constants land, add a
second relay ring here (the reserved band is rows bottom+2..bottom+10,
east of COL_LOAD -- the LOAD bypass crosses at bottom+12).
"""

from __future__ import annotations

import importlib

from .canvas import Canvas

STEP_BASE = (4000, 0)      # FETCH/STEP3 band, below the 3990-row SCAN3 rig
FETCH_REL = (0, 20)        # lllm_step's proven complex geometry
STEP_REL = (28, 14)
COL_REQ = 9                # STEP3 -> FETCH corridor
COL_DRAW = 10              # STEP3 -> DIST, southbound
COL_LOAD = 12              # LOAD's final northbound approach (from BELOW)
ROW_XING = 3996            # S2 -> east bypass, between the two bands
DRAW_COL = 20              # DIST west wall column

# claude_25 planned STEP3 interface, used when llm_step3 does not (yet)
# export its own values.  Names probed on the module first, then here.
STEP3_DEFAULTS = {
    "STEP_ROWS": 222, "STEP_COLS": 96,
    "REQ_ROW": 2, "RESP_COL": 8, "DRAW_ROW": 20, "LOAD_ROW": 21,
    "SCR_OUT_ROW": 30, "SCR_IN_ROW": 33,
}
_ROOM_BUILDERS = ("build_step3_room", "build_step_room", "build_room")


def step3_spec() -> dict:
    """Fresh look at llm_step3: room rows (or a stub) + port constants."""
    from . import llm_step3

    mod = importlib.reload(llm_step3)
    spec = {"module": mod}
    for key, default in STEP3_DEFAULTS.items():
        spec[key] = getattr(mod, key, default)
    rows = None
    for name in _ROOM_BUILDERS:
        fn = getattr(mod, name, None)
        if fn is None:
            continue
        try:
            rows = fn()
            rows = rows if isinstance(rows, list) else rows.render()
            spec["builder"] = name
            break
        except Exception as exc:  # partial transcription: fall back
            spec["stub"] = f"{name} failed: {exc!r:.120}"
    if rows is None and hasattr(mod, "build_step3_core"):
        try:  # the claude_25 pattern: core fills a Room(ROWS3, COLS3)
            from .lllm_fetch import Room

            room = Room(mod.ROWS3, mod.COLS3)
            mod.build_step3_core(room)
            rows = room.render()
            spec["builder"] = "build_step3_core"
        except Exception as exc:
            spec["stub"] = f"build_step3_core failed: {exc!r:.120}"
    if rows is None:
        spec.setdefault("stub", "no room builder in llm_step3 yet")
        r, c = spec["STEP_ROWS"], spec["STEP_COLS"]
        rows = ["+" + "-" * c + "+"] + ["|" + " " * c + "|"] * r \
            + ["+" + "-" * c + "+"]
    spec.setdefault("stub", None)
    spec["rows"] = rows
    return spec


def _place_scan3(cv: Canvas) -> dict:
    """build_scan3_machine verbatim, minus the O room; returns anchors."""
    from . import llm_scan3 as S
    from .lllm_scan import build_scan_room_v2

    s1 = build_scan_room_v2()
    cv.put(0, 5, s1)
    cv.put(1, 0, ["+-+", "|I|", "+-+"])
    cv.pipe([(2, 3), (2, 4)])
    S._ring(cv, 0, 5 + len(s1[0]) - 1, far_off=12)
    sr = S.build_sr_room()
    y = len(s1) + 2
    cv.put(y, 5, sr)
    cv.pipe([(6, 4), (6, 2), (y + 2, 2), (y + 2, 4)])
    S._ring(cv, y, 5 + len(sr[0]) - 1)
    p1 = S._compile3(S._build_p1_asm(3).fsm())
    yp = y + len(sr) + 2
    cv.put(yp, 5, p1)
    cv.pipe([(y + 6, 4), (y + 6, 2), (yp + 2, 2), (yp + 2, 4)])
    cr = 5 + len(p1[0]) - 1
    S._add_memory(cv, cr + 8, cr, top=yp)
    s2 = S.build_s2_room()
    ys = yp + len(p1) + 2
    cv.put(ys, 5, s2)
    cv.pipe([(yp + 6, 4), (yp + 6, 2), (ys + 2, 2), (ys + 2, 4)])
    S._ring(cv, ys, 5 + len(s2[0]) - 1)
    return {
        "I": (1, 0), "S1": (0, 5), "S1RING": (1, 5 + len(s1[0]) - 1 + 5),
        "SR": (y, 5), "SRRING": (y + 1, 5 + len(sr[0]) - 1 + 5),
        "P1": (yp, 5), "MEMW": (yp, cr + 8), "MEMR": (yp + 13, cr + 8),
        "MEM312": (yp + 23, cr + 8),
        "S2": (ys, 5), "S2RING": (ys + 1, 5 + len(s2[0]) - 1 + 5),
        "s2_out_row": ys + 6,
    }


def _place_step3(cv: Canvas, spec: dict) -> dict:
    """FETCH + STEP3 + both relays, lllm_assemble's proven complex."""
    from .lllm_fetch import build_fetch, build_relay
    from .lllm_step import build_step_relay

    br, bc = STEP_BASE
    fr, fc = br + FETCH_REL[0], bc + FETCH_REL[1]
    sr, sc = br + STEP_REL[0], bc + STEP_REL[1]
    rows = spec["rows"]
    cv.put(fr, fc, build_fetch().render())
    cv.put(sr, sc, rows)
    cv.put(fr + 20, fc + 50, build_relay().render())
    right = sc + len(rows[0]) - 1 + 1          # east attachment column
    bottom = sr + len(rows) - 1
    so, si = sr + spec["SCR_OUT_ROW"], sr + spec["SCR_IN_ROW"]
    cv.put(so - 1, right + 6, build_step_relay().render())
    cv.pipe([(so, right), (so, right + 5)])
    cv.pipe([(so + 1, right + 12), (so + 1, right + 13),
             (si, right + 13), (si, right)])
    return {"FETCH": (fr, fc), "FETCHRELAY": (fr + 20, fc + 50),
            "STEP3": (sr, sc), "STEP3RELAY": (so - 1, right + 6),
            "sr": sr, "sc": sc, "fr": fr, "fc": fc,
            "right": right, "bottom": bottom}


def _route(cv: Canvas, scan: dict, step: dict, spec: dict) -> dict:
    """FETCH round trip, LOAD east bypass, DRAW chain; returns anchors."""
    from .lllm_draw import place_display_block

    sr, sc, fr, fc = step["sr"], step["sc"], step["fr"], step["fc"]
    left, fleft = sc - 1, fc - 1
    # STEP3 <-> FETCH, byte-for-byte the lllm_assemble corridor shape
    cv.pipe([(sr + spec["REQ_ROW"], left), (sr + spec["REQ_ROW"], COL_REQ),
             (fr + 2, COL_REQ), (fr + 2, fleft)])
    cv.pipe([(fr + 13, fleft), (fr + 13, fleft - 1), (sr - 1, fleft - 1),
             (sr - 1, sc + spec["RESP_COL"])])
    cv.cells[(sr - 1, sc + spec["RESP_COL"])] = "v"    # terminal bend
    # FETCH <-> its relay: the >= 70 cell world ring
    cv.pipe([(fr + 2, fc + 47), (fr + 2, fc + 67), (fr + 21, fc + 67),
             (fr + 21, fc + 56)])
    cv.pipe([(fr + 21, fc + 49), (fr + 21, fc + 48), (fr + 5, fc + 48),
             (fr + 5, fc + 47)])
    # S2 -> STEP3 LOAD: east bypass around the whole complex, then north
    col_far = step["right"] + 48
    row_far = step["bottom"] + 12
    load = sr + spec["LOAD_ROW"]
    cv.pipe([(scan["s2_out_row"], 4), (scan["s2_out_row"], 2),
             (ROW_XING, 2), (ROW_XING, col_far), (row_far, col_far),
             (row_far, COL_LOAD), (load, COL_LOAD), (load, left)])
    # STEP3 -> DIST -> drivers -> display (claude_10 delta protocol)
    draw_at = (row_far + 21, DRAW_COL)
    place_display_block(cv, *draw_at)
    cv.pipe([(sr + spec["DRAW_ROW"], left), (sr + spec["DRAW_ROW"], COL_DRAW),
             (draw_at[0] + 2, COL_DRAW), (draw_at[0] + 2, draw_at[1] - 1)])
    dr, dc = draw_at
    return {"DIST": (dr, dc), "ADDRDRV": (dr - 7, dc + 18),
            "DATADRV": (dr, dc + 19), "SWAPDRV": (dr + 7, dc + 20),
            "DISPLAY": (dr - 3, dc + 46)}


def assemble(spec: dict | None = None) -> tuple[str, dict]:
    """(machine text, anchors).  STEP3 is re-read from disk via the spec."""
    spec = spec or step3_spec()
    cv = Canvas()
    scan = _place_scan3(cv)
    step = _place_step3(cv, spec)
    draw = _route(cv, scan, step, spec)
    anchors = {v: k for k, v in scan.items() if isinstance(v, tuple)}
    for name in ("FETCH", "FETCHRELAY", "STEP3", "STEP3RELAY"):
        anchors[step[name]] = name
    for name, at in draw.items():
        anchors[at] = name
    return cv.render(), anchors


def build_machine(spec: dict | None = None) -> str:
    """The whole LLM3 machine as .man text (STEP3 re-read from disk)."""
    return assemble(spec)[0]


def room_anchors(spec: dict | None = None) -> dict[tuple[int, int], str]:
    """(top, left) -> component name, for labelling a parsed machine."""
    return assemble(spec)[1]


# --------------------------------------------------------------- diagnostics
def label_rooms(machine, anchors) -> dict[int, str]:
    return {
        id(room): anchors.get((room.top, room.left),
                              f"?@{room.top},{room.left}")
        for room in machine.rooms
    }


def pipe_names(machine, anchors) -> dict[int, str]:
    names = label_rooms(machine, anchors)
    return {id(p): f"{names[id(p.source)]}->{names[id(p.dest)]}"
            for p in machine.pipes}


class Trace:
    """Per-pipe traffic counters (lllm_assemble's proven wrap technique)."""

    def __init__(self, machine, anchors):
        self.machine = machine
        self.names = pipe_names(machine, anchors)
        self.sent = dict.fromkeys(self.names, 0)
        self.taken = dict.fromkeys(self.names, 0)
        self.last_send = dict.fromkeys(self.names, 0)
        self.last_take = dict.fromkeys(self.names, 0)
        self.tick = self.base = 0
        put, take, tick = machine._pipe_put, machine._pipe_take, machine._tick

        def wput(pipe, index, value):
            self.sent[id(pipe)] += 1
            self.last_send[id(pipe)] = self.tick
            return put(pipe, index, value)

        def wtake(pipe, index):
            self.taken[id(pipe)] += 1
            self.last_take[id(pipe)] = self.tick
            return take(pipe, index)

        def wtick(res):
            self.tick = self.base + res.ticks
            return tick(res)

        machine._pipe_put, machine._pipe_take, machine._tick = wput, wtake, wtick

    def last_traffic(self) -> int:
        return max(
            max(self.last_send.values(), default=0),
            max(self.last_take.values(), default=0),
        )

    def stall_pipe(self) -> str:
        key = max(self.names, key=lambda k: (
            max(self.last_send[k], self.last_take[k]), self.taken[k]))
        return self.names[key]


def extract_room(text: str, top: int, left: int, rows: int, cols: int):
    """The rows x cols block of the rendered machine at (top, left)."""
    lines = text.split("\n")
    out = []
    for r in range(top, top + rows):
        line = lines[r] if r < len(lines) else ""
        line = line + " " * (left + cols - len(line))
        out.append(line[left : left + cols])
    return out


def ring_cells(machine, anchors, a: str, b: str) -> int:
    """Total pipe cells on the legs of a room-to-relay ring."""
    names = pipe_names(machine, anchors)
    return sum(len(p.cells) for p in machine.pipes
               if names[id(p)] in (f"{a}->{b}", f"{b}->{a}"))


def binding_audit(text: str, anchors) -> list[str]:
    """room_ports margins over ir_export's own resolution map.

    Each s/r cell's port is the pipe the ENGINE binds it to; the margin
    is the slack before that binding would flip to another pipe.  Rooms
    with fewer than two pipes in a direction are trivially safe.
    """
    from . import ir_export, room_ports
    from .sim import Machine

    ir = ir_export.machine_ir(text)
    machine = Machine.parse(text)
    names = label_rooms(machine, anchors)
    lines = []
    for room in machine.rooms:
        if getattr(room, "kind", "room") != "room":
            continue
        ops, positions = [], {}
        for i, pipe in enumerate(machine.pipes):
            if pipe.source is room:
                positions[f"out{i}"] = tuple(pipe.cells[0])
            if pipe.dest is room:
                positions[f"in{i}"] = tuple(pipe.cells[-1])
        for key, entry in ir["resolution"].items():
            r, c = map(int, key.split(","))
            if not (room.top < r < room.bottom and room.left < c < room.right):
                continue
            if entry.get("pipe") is None:
                lines.append(f"{names[id(room)]:11s} {entry['op']} at "
                             f"({r},{c}) binds NO pipe")
                continue
            tag = ("out" if entry["op"] == "s" else "in") + str(entry["pipe"])
            ops.append(room_ports.Op((r, c), tag, entry["op"] == "s"))
        if ops and positions:
            m = room_ports.margin(ops, positions)
            if m < 10**9:
                lines.append(f"{names[id(room)]:11s} margin={m} "
                             f"({len(ops)} pipe ops)")
    return lines


def case_rows(case: dict) -> list[str]:
    """Round-1 tokens (w, h, chars) back into the program grid."""
    t = [int(v) for v in case["rounds"][0]["in"]]
    w, h = t[0], t[1]
    return ["".join(chr(c) for c in t[2 + r * w : 2 + (r + 1) * w])
            for r in range(h)]


def stream_section(rows: list[str], index: int) -> str:
    """Name stream[index] of the SCAN3 -> STEP3 contract for a case."""
    from .llm_lockstep import machine_stream

    n = len(machine_stream(rows))
    if index < 64:
        return f"world word {index} (cells {4 * index}..{4 * index + 3})"
    if index < 67:
        return f"man addr {index - 64}"
    if index == 67:
        return "pipe count"
    if index < n:
        p, w = divmod(index - 68, 8)
        kind = "header" if w == 0 else f"cell word {w - 1}"
        return f"pipe {p} descriptor {kind}"
    return f"round-{index - n + 2} k value"


def diagnose(text: str, rounds, anchors, max_ticks: int = 30_000_000,
             quiet: int = 150_000):
    """Run under the judge's controller until pass/fail/error/QUIESCENCE.

    Pure sim (hookable) with wall-tolerant server semantics; stops early
    once no pipe moves a value for ``quiet`` ticks -- that IS the stall.
    """
    from . import alexey_walljudge
    from .judge import RoundController
    from .sim import Machine

    machine = Machine.parse(text)
    controller = RoundController(rounds)
    with alexey_walljudge._wall_tolerant():
        trace = Trace(machine, anchors)
        res = None
        while trace.base < max_ticks:
            chunk_base = trace.base
            res = machine.run(max_ticks=quiet, controller=controller)
            trace.base += res.ticks
            if res.status != "tick-cap":
                break
            if trace.last_traffic() <= chunk_base:
                res.status = "quiescent"
                break
    return res, trace, controller


def men_report(machine, anchors) -> list[str]:
    """Every man's cell at the stall: absolute, room-relative, state."""
    names = label_rooms(machine, anchors)
    lines = []
    for man in machine.men:
        state = ("halted" if man.halted else
                 "blocked " + (man.wait_kind or "") if man.blocked
                 else "running")
        rel = (man.r - man.room.top, man.c - man.room.left)
        lines.append(f"  {names[id(man.room)]:11s} ({man.r},{man.c}) "
                     f"rel {rel} {machine.grid[man.r][man.c]!r} {state}")
    return lines


def stall_report(rows, res, trace, controller, anchors) -> list[str]:
    """The product: WHERE execution stalled and what STEP3 must do next."""
    m = trace.machine
    names = label_rooms(m, anchors)
    lines = [
        f"status={res.status} error={res.error} ticks={trace.base}",
        f"rounds completed {controller.round_idx}/{len(controller.rounds)}"
        f"  frames matched this round {controller.frame_idx}",
        f"last pipe traffic: {trace.stall_pipe()} at tick "
        f"{trace.last_traffic()}",
    ]
    for key, name in sorted(trace.names.items(), key=lambda kv: kv[1]):
        pipe = next(p for p in m.pipes if id(p) == key)
        fill = sum(v is not None for v in pipe.values)
        state = ("FULL" if fill == len(pipe.cells) else
                 "empty" if fill == 0 else f"{fill}/{len(pipe.cells)}")
        lines.append(
            f"  {name:22s} sent={trace.sent[key]:5d}@{trace.last_send[key]:<9d}"
            f" taken={trace.taken[key]:5d}@{trace.last_take[key]:<9d} {state}")
    load_key = next((k for k, v in trace.names.items() if v == "S2->STEP3"),
                    None)
    if load_key is not None:
        taken = trace.taken[load_key]
        lines.append(
            f"STEP3 consumed {taken} stream values; next it must read: "
            f"{stream_section(rows, taken)}")
    step_men = [man for man in m.men if names[id(man.room)] == "STEP3"]
    if not step_men:
        lines.append("STEP3 man: NONE (stub or man-less room on disk)")
    for man in step_men:
        lines.append(f"STEP3 man at rel ({man.r - man.room.top},"
                     f"{man.c - man.room.left}) glyph "
                     f"{m.grid[man.r][man.c]!r}")
    lines.append("men:")
    lines.extend(men_report(m, anchors))
    return lines
