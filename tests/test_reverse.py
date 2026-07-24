"""Reverse-a-list shrinking-ring machine."""

import json
from pathlib import Path

from littleman.judge import judge_problem
from littleman.reverse import build_reverse
from littleman.sim import Machine

PROBLEMS = Path(__file__).resolve().parent.parent / "data" / "small" / "problems"


def test_passes_all_public_cases():
    problem = json.loads((PROBLEMS / "reverse-a-list.json").read_text())
    report = judge_problem(build_reverse(), problem)
    assert report.cases_passed == report.cases_total == 8


def test_corridor_exceeds_ring_round_trip():
    """The q count is only correct if every in-flight value parks before
    the corridor ends: corridor ticks must exceed out-pipe + relay lap +
    in-pipe transit."""
    m = Machine.parse(build_reverse())
    ring = [p for p in m.pipes if p.source.kind == "room" and p.dest.kind == "room"]
    assert len(ring) == 2
    round_trip = sum(len(p.cells) for p in ring) + 8  # 8 = relay lap bound
    corridor = 7 + 1 + 15 + 1 + 15 + 1 + 15 + 1 + 2  # rows 3-7 walk
    assert corridor > round_trip, (corridor, round_trip)


def test_ring_capacity_holds_sixteen():
    m = Machine.parse(build_reverse())
    ring_in = max(
        (p for p in m.pipes if p.source.kind == "room" and p.dest.kind == "room"),
        key=lambda p: len(p.cells),
    )
    assert len(ring_in.cells) >= 17
