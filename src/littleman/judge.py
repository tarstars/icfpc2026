"""Judge: run programs against problem test cases with round gating."""

from __future__ import annotations

from dataclasses import dataclass, field

from .sim import Machine


def footprint(text: str) -> int:
    rows = [line for line in text.split("\n")]
    occupied = [
        (r, c) for r, line in enumerate(rows) for c, ch in enumerate(line) if ch != " "
    ]
    if not occupied:
        return 0
    rs = [r for r, _ in occupied]
    cs = [c for _, c in occupied]
    width = max(cs) - min(cs) + 1
    height = max(rs) - min(rs) + 1
    return max(width, height) ** 2


def _parse_frame(rows):
    return [[int(ch, 16) for ch in row] for row in rows]


class RoundController:
    """Releases round N+1 input only after all round N output (values
    and/or committed display frames) is received."""

    def __init__(self, rounds):
        self.rounds = [
            {
                "in": [int(v) for v in rd["in"]],
                "out": [int(v) for v in rd.get("out", [])],
                "frames": [_parse_frame(f) for f in rd.get("frames", [])],
            }
            for rd in rounds
        ]
        self.round_idx = 0
        self.out_idx = 0
        self.frame_idx = 0
        self.queue = []
        self.last_output_tick = 0
        self.done = not self.rounds
        self._release_current()

    def _release_current(self):
        while self.round_idx < len(self.rounds):
            rd = self.rounds[self.round_idx]
            self.queue.extend(rd["in"])
            if rd["out"] or rd["frames"]:
                return
            self.round_idx += 1  # nothing expected: unlock next immediately
        self.done = True

    def pop_input(self):
        return self.queue.pop(0) if self.queue else None

    def _round_complete(self, tick):
        rd = self.rounds[self.round_idx]
        if self.out_idx < len(rd["out"]) or self.frame_idx < len(rd["frames"]):
            return None
        self.round_idx += 1
        self.out_idx = 0
        self.frame_idx = 0
        self.last_output_tick = tick
        self._release_current()
        return "passed" if self.done else None

    def on_output(self, value, tick):
        if self.done:
            return "failed"  # output after everything was already matched
        expected = self.rounds[self.round_idx]["out"]
        if self.out_idx >= len(expected) or value != expected[self.out_idx]:
            return "failed"
        self.out_idx += 1
        self.last_output_tick = tick
        return self._round_complete(tick)

    def on_frame(self, frame, tick):
        if self.done:
            return "failed"
        expected = self.rounds[self.round_idx]["frames"]
        if self.frame_idx >= len(expected) or frame != expected[self.frame_idx]:
            return "failed"
        self.frame_idx += 1
        self.last_output_tick = tick
        return self._round_complete(tick)


@dataclass
class CaseResult:
    passed: bool
    ticks: int
    reason: str | None = None


@dataclass
class ProblemReport:
    cases_total: int
    cases_passed: int
    case_ticks: list = field(default_factory=list)
    case_results: list = field(default_factory=list)
    footprint: int = 0
    score: float = float("inf")


def normalize_case(case) -> list:
    if "rounds" in case:
        return case["rounds"]
    return [{"in": case.get("in", []), "out": case.get("out", [])}]


def judge_case(text: str, rounds, max_ticks: int = 5_000_000) -> CaseResult:
    machine = Machine.parse(text)
    controller = RoundController(rounds)
    if controller.done:  # nothing expected at all
        return CaseResult(passed=True, ticks=0)
    res = machine.run(max_ticks=max_ticks, controller=controller)
    if res.status == "passed":
        return CaseResult(passed=True, ticks=controller.last_output_tick)
    reason = "wrong-output" if res.status == "failed" else (res.error or res.status)
    return CaseResult(passed=False, ticks=res.ticks, reason=reason)


def judge_problem(
    text: str, problem: dict, max_ticks: int | None = None
) -> ProblemReport:
    cap = max_ticks or problem.get("tickCap") or 5_000_000
    cases = problem["publicTestData"]
    report = ProblemReport(cases_total=len(cases), cases_passed=0)
    report.footprint = footprint(text)
    for case in cases:
        result = judge_case(text, normalize_case(case), max_ticks=cap)
        report.case_results.append(result)
        if result.passed:
            report.cases_passed += 1
            report.case_ticks.append(result.ticks)
    if report.cases_passed == report.cases_total and report.case_ticks:
        if problem.get("scoring") == "footprint":
            report.score = float(report.footprint)
        else:
            avg = sum(report.case_ticks) / len(report.case_ticks)
            report.score = report.footprint * avg
    return report
