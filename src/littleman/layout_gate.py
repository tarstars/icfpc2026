"""The oracle gate: does a re-laid artifact still mean what the original did?

Every check here exists because something got past its absence, and the
order is cheapest-first so a broken candidate dies before the judge runs:

1. **it parses, with the SAME number of pipes.** A pipe count that grew is
   the signature of a bend that went flush against a wall: `sim._find_pipes`
   starts a trace at every arrow adjacent to a room and pointing away from
   it, so one careless corner invents a whole extra connection.
2. **`server_compat.validate_layout`** -- shared wall cells, and the rule
   that exactly one pipe may run against an INPUT room's wall. Both are
   server-only; our parser accepts layouts the server rejects 0/0.
3. **no pipe shorter than two cells.** The server refuses to load them and
   the local judge still reports a clean pass, which silently invalidated
   two submissions.
4. **binding roles identical to the ORIGINAL.** `ir_export.machine_ir`
   records, per instruction cell, which pipe `s`/`r`/`q`/`S`/`R`/`U` binds
   to. Re-placement is only behaviour-preserving if every one of those is
   unchanged, and nothing else in the stack checks it.
5. **no pipe SHRANK.** The one that is not theoretical: a pipe is storage,
   and a ring machine that loses a cell of storage deadlocks with no other
   symptom. A squeezed snake passed 5/5 public and died on an adversarial
   case at snake-length 68; the same failure hit a teammate's independent
   fold the same day, and repairing it meant restoring three legs. Growth
   is allowed (cold-path pipe length is free); shrinkage fails loudly.
6. **the judge**: every public case passes, with avgTicks and score
   reported against the original so the caller can see the real trade.

Checks 4 and 5 need to know WHICH pipe is which across a re-placement, and
neither room order nor pipe order survives moving rooms around -- both come
from a top-left scan. So the correspondence is rebuilt structurally, by
colour refinement on the room graph (rooms are rigid, so their text is a
strong initial colour). If that leaves an ambiguity the gate says so
instead of guessing quietly.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field

from . import ir_export, server_compat
from .judge import footprint
from .sim import LoadError, Machine

PROBLEM_DIR = pathlib.Path(__file__).resolve().parents[2] / "data" / "small" / "problems"


@dataclass
class GateReport:
    passed: bool
    reasons: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    width: int = 0
    height: int = 0
    footprint: int = 0
    cases_passed: int = 0
    cases_total: int = 0
    avg_ticks: float | None = None
    score: float | None = None
    original_footprint: int = 0
    original_avg_ticks: float | None = None
    original_score: float | None = None

    @property
    def gain(self) -> float | None:
        """How many times better than the original, >1 being an improvement."""
        if not self.score or not self.original_score:
            return None
        return self.original_score / self.score

    def summary(self) -> str:
        verdict = "PASS" if self.passed else "FAIL"
        line = (f"{verdict} {self.width}x{self.height} fp={self.footprint:,} "
                f"cases={self.cases_passed}/{self.cases_total}")
        if self.score:
            line += f" score={self.score:,.0f}"
        if self.gain:
            line += f" ({self.gain:.3f}x live)"
        return line


def _room_text(machine: Machine, room) -> tuple:
    """A rigid room's own cells, as its identity across a re-placement."""
    return tuple(
        "".join(machine.grid[r][room.left:room.right + 1])
        for r in range(room.top, room.bottom + 1)
    )


def _colours(machine: Machine) -> list[tuple]:
    """1-WL refinement of the room graph, seeded by each room's own text.

    Rooms move, so nothing about position identifies them; their contents
    do, and where two rooms are textually identical (matmul has ten) the
    wiring around them separates the copies. Two rounds is enough for the
    instances we place -- and where it is not, the caller is told rather
    than handed a guess.
    """
    rooms = list(machine.rooms)
    index = {id(room): i for i, room in enumerate(rooms)}
    colour = [(room.kind, _room_text(machine, room)) for room in rooms]
    edges = [(index[id(p.source)], index[id(p.dest)]) for p in machine.pipes]
    for _ in range(2):
        out_nb: list[list] = [[] for _ in rooms]
        in_nb: list[list] = [[] for _ in rooms]
        for src, dst in edges:
            out_nb[src].append(colour[dst])
            in_nb[dst].append(colour[src])
        colour = [
            (colour[i], tuple(sorted(map(repr, out_nb[i]))),
             tuple(sorted(map(repr, in_nb[i]))))
            for i in range(len(rooms))
        ]
    return colour


def correspondence(original: Machine, candidate: Machine):
    """Map original room/pipe indices to candidate ones. (rooms, pipes, notes)."""
    notes: list[str] = []
    if len(original.rooms) != len(candidate.rooms):
        return None, None, ["room count differs"]
    if len(original.pipes) != len(candidate.pipes):
        return None, None, ["pipe count differs"]
    oc, cc = _colours(original), _colours(candidate)
    buckets: dict = {}
    for i, colour in enumerate(cc):
        buckets.setdefault(repr(colour), []).append(i)
    room_map: dict[int, int] = {}
    for i, colour in enumerate(oc):
        pool = buckets.get(repr(colour))
        if not pool:
            return None, None, [f"original room {i} has no counterpart"]
        if len(pool) > 1:
            notes.append(f"room {i}: {len(pool)} interchangeable candidates")
        room_map[i] = pool.pop(0)

    o_index = {id(r): i for i, r in enumerate(original.rooms)}
    c_index = {id(r): i for i, r in enumerate(candidate.rooms)}
    by_pair: dict = {}
    for j, pipe in enumerate(candidate.pipes):
        by_pair.setdefault(
            (c_index[id(pipe.source)], c_index[id(pipe.dest)]), []).append(j)
    pipe_map: dict[int, int] = {}
    for i, pipe in enumerate(original.pipes):
        key = (room_map[o_index[id(pipe.source)]], room_map[o_index[id(pipe.dest)]])
        pool = by_pair.get(key)
        if not pool:
            return None, None, [f"original pipe {i} has no counterpart"]
        if len(pool) > 1:
            notes.append(f"pipe {i}: {len(pool)} parallel candidates")
        pipe_map[i] = pool.pop(0)
    return room_map, pipe_map, notes


def _bounds(text: str) -> tuple[int, int]:
    cells = [(r, c) for r, line in enumerate(text.split("\n"))
             for c, ch in enumerate(line) if ch != " "]
    if not cells:
        return 0, 0
    rows = [r for r, _ in cells]
    cols = [c for _, c in cells]
    return max(cols) - min(cols) + 1, max(rows) - min(rows) + 1


def _roles(machine: Machine, ir: dict, room_index: dict) -> dict:
    """Binding roles re-keyed from absolute cells to (room, row, col) offsets."""
    out: dict = {}
    for key, entry in ir["resolution"].items():
        r, c = (int(v) for v in key.split(","))
        for i, room in enumerate(machine.rooms):
            if room.contains(r, c):
                out[(i, r - room.top, c - room.left)] = entry
                break
    return out


def _load_problem(slug: str) -> dict:
    return json.loads((PROBLEM_DIR / f"{slug}.json").read_text())


def check(original_text: str, candidate_text: str, problem_slug: str, *,
          judge_original: bool = True, max_ticks: int | None = None
          ) -> GateReport:
    """Gate a re-laid `candidate_text` against the artifact it came from."""
    report = GateReport(passed=False)
    report.width, report.height = _bounds(candidate_text)
    try:
        original = Machine.parse(original_text)
    except LoadError as exc:
        report.reasons.append(f"ORIGINAL does not parse: {exc}")
        return report
    try:
        candidate = Machine.parse(candidate_text)
    except LoadError as exc:
        report.reasons.append(f"candidate does not parse: {exc}")
        return report
    report.footprint = footprint(candidate_text)
    report.original_footprint = footprint(original_text)

    if len(candidate.pipes) != len(original.pipes):
        report.reasons.append(
            f"pipe count {len(candidate.pipes)} != original "
            f"{len(original.pipes)} -- a bend went flush against a wall and "
            "`sim._find_pipes` started a trace there")
    if len(candidate.rooms) != len(original.rooms):
        report.reasons.append(
            f"room count {len(candidate.rooms)} != original {len(original.rooms)}")
    if len(candidate.men) != len(original.men):
        report.reasons.append(
            f"man count {len(candidate.men)} != original {len(original.men)}")
    try:
        server_compat.validate_layout(candidate_text)
    except server_compat.ServerCompatibilityError as exc:
        report.reasons.append(f"server layout rule: {exc}")
    short = [i for i, pipe in enumerate(candidate.pipes) if len(pipe.cells) < 2]
    if short:
        report.reasons.append(
            f"{len(short)} pipe(s) shorter than 2 cells (server refuses to "
            f"load them and the local judge still passes): {short[:5]}")
    if report.reasons:
        return report
    report.reasons.extend(_check_bindings(original, candidate, report))
    if report.reasons:
        return report
    _judge(original_text, candidate_text, problem_slug, report,
           judge_original=judge_original, max_ticks=max_ticks)
    report.passed = not report.reasons
    return report


def _check_bindings(original: Machine, candidate: Machine,
                    report: GateReport) -> list[str]:
    """Roles identical, and no pipe shorter than the one it replaces."""
    room_map, pipe_map, notes = correspondence(original, candidate)
    report.notes.extend(notes)
    if room_map is None:
        return [f"cannot match candidate to original: {notes[0]}"]

    o_roles = _roles(original, ir_export.machine_ir(_text_of(original)),
                     room_map)
    c_roles = _roles(candidate, ir_export.machine_ir(_text_of(candidate)),
                     room_map)
    reasons = []
    diffs = 0
    for (room, dr, dc), entry in o_roles.items():
        want = c_roles.get((room_map[room], dr, dc))
        if want is None:
            diffs += 1
            if diffs <= 3:
                reasons.append(f"binding: no op cell at room {room} +{dr},{dc}")
            continue
        if entry["op"] != want["op"]:
            diffs += 1
            continue
        if "pipe" in entry:
            expect = None if entry["pipe"] is None else pipe_map[entry["pipe"]]
            if want.get("pipe") != expect:
                diffs += 1
                if diffs <= 3:
                    reasons.append(
                        f"binding: `{entry['op']}` at room {room} +{dr},{dc} "
                        f"binds a different pipe")
        if "pipes" in entry:
            expect = sorted(pipe_map[p] for p in entry["pipes"])
            if sorted(want.get("pipes", [])) != expect:
                diffs += 1
                if diffs <= 3:
                    reasons.append(
                        f"binding: `{entry['op']}` at room {room} +{dr},{dc} "
                        f"sees a different pipe set")
    if diffs:
        reasons.append(f"{diffs} binding role diff(s) vs the original")

    shrunk = []
    for i, pipe in enumerate(original.pipes):
        was, now = len(pipe.cells), len(candidate.pipes[pipe_map[i]].cells)
        if now < was:
            shrunk.append((i, was, now))
    if shrunk:
        detail = ", ".join(f"pipe {i}: {was}->{now}" for i, was, now in shrunk[:6])
        reasons.append(
            f"{len(shrunk)} pipe(s) SHRANK ({detail}). A pipe is storage: a "
            "ring machine that loses capacity deadlocks with no other "
            "symptom, and passes the public cases while doing it")
    return reasons


def _text_of(machine: Machine) -> str:
    return "\n".join("".join(row).rstrip() for row in machine.grid) + "\n"


def _judge(original_text: str, candidate_text: str, slug: str,
           report: GateReport, *, judge_original: bool, max_ticks) -> None:
    """Public cases must all pass; report avgTicks and score against live."""
    problem = _load_problem(slug)
    result = server_compat.judge_problem(candidate_text, problem,
                                         max_ticks=max_ticks)
    report.cases_total = result.cases_total
    report.cases_passed = result.cases_passed
    if result.case_ticks and result.cases_passed == result.cases_total:
        report.avg_ticks = sum(result.case_ticks) / len(result.case_ticks)
        report.score = result.score
    else:
        failed = [i for i, case in enumerate(result.case_results)
                  if not case.passed]
        why = {result.case_results[i].reason for i in failed}
        report.reasons.append(
            f"judge: {result.cases_passed}/{result.cases_total} public cases "
            f"pass (failed {failed[:4]}, reasons {sorted(map(str, why))})")
    if judge_original:
        base = server_compat.judge_problem(original_text, problem,
                                           max_ticks=max_ticks)
        if base.case_ticks and base.cases_passed == base.cases_total:
            report.original_avg_ticks = sum(base.case_ticks) / len(base.case_ticks)
            report.original_score = base.score
