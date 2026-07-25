"""Judge programs whose last little man walks into a wall after his final `s`.

The contest server tolerates this: the man dies, but values already in the
output pipe still drain and the round still passes. `littleman.sim` is
stricter — it ends the whole program on the wall step, one tick before a
just-sent value reaches the end of a 2-cell output pipe — so a program that
scores on the server fails locally with reason 'wall'.

Confirmed on 2026-07-25: submission c9cf76d1 (triangle, 8x8, `s` on the last
interior cell, no trailing cell and no `H`) passed 19/19 for a score of 832,
while `judge_problem` reported 0/6 with reason 'wall'.

That matters for geometry, not just tidiness: needing a cell after `s`
forces a bigger interior, and a bigger interior costs turns, and turns cost
ticks. Dropping it is what took triangle from 15 ticks to 13.

Use `judge_case` / `judge_problem` from here in place of the ones in
`littleman.judge` when a design deliberately ends at a wall. Programs that
pass under `littleman.judge` also pass here — this only widens what is
accepted, it never hides a real failure.
"""

from __future__ import annotations

import contextlib

from .judge import CaseResult, ProblemReport, RoundController, footprint, normalize_case
from .sim import Machine


@contextlib.contextmanager
def _wall_tolerant():
    """Halt a man who steps into a wall instead of ending the program."""
    original = Machine._tick

    def patched(self, res):
        err = original(self, res)
        if err != "wall":
            return err
        for man in self.men:
            if man.halted or man.blocked:
                continue
            nr = man.r + man.direction[0]
            nc = man.c + man.direction[1]
            if not man.room.contains_interior(nr, nc):
                man.halted = True
        return None

    Machine._tick = patched
    try:
        yield
    finally:
        Machine._tick = original


def judge_case(text: str, rounds, max_ticks: int = 5_000_000) -> CaseResult:
    machine = Machine.parse(text)
    controller = RoundController(rounds)
    if controller.done:
        return CaseResult(passed=True, ticks=0)
    with _wall_tolerant():
        res = machine.run(max_ticks=max_ticks, controller=controller)
    if res.status == "passed":
        return CaseResult(passed=True, ticks=controller.last_output_tick)
    reason = "wrong-output" if res.status == "failed" else (res.error or res.status)
    return CaseResult(passed=False, ticks=res.ticks, reason=reason)


def judge_problem(text: str, problem: dict, max_ticks: int | None = None) -> ProblemReport:
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
