"""Release gates for chatgpt_2's 18-square Sort U-load-loop candidate."""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

from littleman.chatgpt2_sort_hotloop import build_chatgpt2_sort_01
from littleman.judge import judge_case, judge_problem
from littleman.server_compat import validate_layout
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "submissions" / "sort" / "chatgpt2_sort_01.man"
BASELINE = ROOT / "submissions" / "sort" / "tarstars_sort_08.man"
PROBLEM = json.loads(
    (ROOT / "data" / "small" / "problems" / "sort-numbers.json").read_text()
)
SHA256 = "932a3c2bbe3e6cb345c9ab14d3bd4d7c2dbbd2c66699c947c7d59535ca97af79"
PUBLIC_TICKS = [737, 603, 754, 532, 906, 2121, 5236]
BASELINE_TICKS = [755, 617, 772, 544, 928, 2137, 5282]


def _rounds(lists: list[list[int]]) -> list[dict]:
    return [{"in": [len(values), *values], "out": sorted(values)} for values in lists]


def _run(lists: list[list[int]]):
    return judge_case(build_chatgpt2_sort_01(), _rounds(lists))


def test_generator_hash_geometry_and_immutable_pipe_capacities():
    text = build_chatgpt2_sort_01()
    assert text == build_chatgpt2_sort_01() == ARTIFACT.read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == SHA256

    rows = text.splitlines()
    assert len(rows) == max(map(len, rows)) == 18
    machine = Machine.parse(text)
    assert (len(machine.rooms), len(machine.pipes), len(machine.men)) == (4, 4, 2)
    assert sorted(len(pipe.cells) for pipe in machine.pipes) == [2, 2, 7, 17]
    validate_layout(text)

    # The only source changes are r -> U and moving the return arrow one cell.
    baseline = BASELINE.read_text().splitlines()
    candidate = text.splitlines()
    differences = [
        (row, column, before, after)
        for row, (old_line, new_line) in enumerate(zip(baseline, candidate))
        for column, (before, after) in enumerate(zip(old_line, new_line))
        if before != after
    ]
    assert differences == [
        (1, 13, "r", "U"),
        (2, 12, "^", " "),
        (2, 13, " ", "^"),
    ]

    pump = max(
        (room for room in machine.rooms if room.kind == "room"),
        key=lambda room: (room.bottom - room.top) * (room.right - room.left),
    )
    incoming_ends = sorted(pipe.cells[-1] for pipe in machine.in_pipes[id(pump)])
    # If input and ring return are simultaneously ready, U chooses the input
    # endpoint first under the organizer's lexicographic ready-pipe rule.
    assert incoming_ends == [(1, 4), (14, 10)]
    assert text.splitlines()[1][13] == "U"


def test_exact_public_ticks_and_score():
    report = judge_problem(build_chatgpt2_sort_01(), PROBLEM)
    assert report.cases_passed == report.cases_total == 7, report.case_results
    assert report.case_ticks == PUBLIC_TICKS
    assert all(new < old for new, old in zip(PUBLIC_TICKS, BASELINE_TICKS))
    assert report.footprint == 324
    assert report.score == 504_005.1428571429


def test_directed_maximum_and_lifecycle_workloads():
    full = list(range(-8, 8))
    cases = [
        [[0] * 16, [0] * 16],
        [list(range(16, 0, -1))] * 6,
        [list(range(16))] * 6,
        [[10_000, -10_000] * 8],
        [[-10_000] * 8 + [10_000] * 8],
        [full, full[::-1], [7], full, [1, 1]],
        [[1], [2], [3], [4], [5], [6]],
        [[10_000] * 16, [-10_000] * 16] * 3,
    ]
    for lists in cases:
        result = _run(lists)
        assert result.passed, (lists, result.reason)


def test_seeded_random_differential_sweep():
    rng = random.Random(202607271024)
    for trial in range(1_000):
        lists = []
        for _ in range(rng.randint(2, 6)):
            n = 16 if trial % 5 == 0 else rng.randint(1, 16)
            magnitude = rng.choice([3, 100, 10_000])
            lists.append([rng.randint(-magnitude, magnitude) for _ in range(n)])
        result = _run(lists)
        assert result.passed, (trial, lists, result.reason)
