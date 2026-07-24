"""Shrinking-ring selection sort (sort_02)."""

import json
from pathlib import Path

from littleman.judge import judge_problem
from littleman.sim import Machine
from littleman.sort_ring import build_sort_ring

PROBLEMS = Path(__file__).resolve().parent.parent / "data" / "small" / "problems"


def test_passes_all_public_cases():
    problem = json.loads((PROBLEMS / "sort-numbers.json").read_text())
    report = judge_problem(build_sort_ring(), problem)
    assert report.cases_passed == report.cases_total == 7


def test_sorts_negatives_and_duplicates():
    m = Machine.parse(build_sort_ring())
    res = m.run(inputs=[6, 5, -5, 0, 5, -10000, 10000], max_ticks=20000)
    assert res.output == [-10000, -5, 0, 5, 5, 10000]


def test_corridor_exceeds_ring_round_trip():
    m = Machine.parse(build_sort_ring())
    ring = [p for p in m.pipes if p.source.kind == "room" and p.dest.kind == "room"]
    round_trip = sum(len(p.cells) for p in ring) + 8  # + relay lap bound
    corridor = 7 + 1 + 15 + 1 + 15 + 1 + 15 + 1 + 2
    assert corridor > round_trip, (corridor, round_trip)
