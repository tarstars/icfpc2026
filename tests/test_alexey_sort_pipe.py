"""Tests for the compacted Sort systolic pipeline (sort_04 candidate).

The rooms are verified separately before the assembled program, because a
protocol bug in one room is otherwise indistinguishable from a wiring bug:

* a stage is driven directly against its reference semantics, including
  the reset token and the warm-up zeros;
* the loader and the gate are driven through their own token contracts;
* the whole machine is then judged on the public cases and stressed at
  the constraint boundary.
"""

import random

import pytest

from littleman.alexey_sort_pipe import (
    SHIFT,
    STAGES,
    build_gate_probe,
    build_loader_probe,
    build_sort_pipe,
    build_stage_probe,
    loader_model,
    stage_model,
)
from littleman.judge import footprint, judge_case
from littleman.sim import Machine


def _sort_rounds(lists):
    return [{"in": [len(xs)] + xs, "out": sorted(xs)} for xs in lists]


def _run(lists):
    return judge_case(build_sort_pipe(), _sort_rounds(lists), max_ticks=300_000)


def test_geometry():
    text = build_sort_pipe()
    machine = Machine.parse(text)
    assert len(machine.rooms) == STAGES + 4      # stages, I, O, loader, gate
    assert len(machine.pipes) == STAGES + 3      # 15 links + I, O, loader, gate
    assert footprint(text) == 2500


@pytest.mark.parametrize(
    "tokens",
    [
        [5], [0], [-1], [5, 3], [3, 5], [5, 5],
        [7, 2, 9, 1, -1, 4, 6],
        [0, 0, 0],
        [1, 2, 3, 4, 5, -1, 5, 4, 3, 2, 1],
    ],
)
def test_stage_semantics(tokens):
    probe = build_stage_probe()
    res = judge_case(probe, [{"in": tokens, "out": stage_model(tokens)}], 20_000)
    assert res.passed, res.reason


def test_stage_semantics_random():
    probe = build_stage_probe()
    rng = random.Random(11)
    for _ in range(30):
        tokens = [
            rng.choice([0, -1] + list(range(1, 40)))
            for _ in range(rng.randint(1, 14))
        ]
        res = judge_case(probe, [{"in": tokens, "out": stage_model(tokens)}], 20_000)
        assert res.passed, (tokens, res.reason)


@pytest.mark.parametrize(
    "values",
    [[5], [1, 2, 3], [-10000, 10000, 0], list(range(16)), [7] * 16],
)
def test_loader_contract(values):
    res = judge_case(
        build_loader_probe(),
        [{"in": [len(values)] + values, "out": loader_model(values)}],
        50_000,
    )
    assert res.passed, res.reason


@pytest.mark.parametrize(
    "values", [[5], [1, 2, 3], [-10000, 10000], list(range(16))]
)
def test_gate_contract(values):
    stream = [0] * STAGES + [v + SHIFT for v in values] + [-1]
    res = judge_case(build_gate_probe(), [{"in": stream, "out": values}], 50_000)
    assert res.passed, res.reason


def test_worst_case_shapes():
    full = list(range(-8, 8))
    cases = [
        [[5]],
        [[0] * 16, [0] * 16],
        [list(range(16, 0, -1))] * 3,
        [list(range(16))] * 3,
        [[10000, -10000] * 8],
        [[-10000] * 16],
        [full, full[::-1], [7], full, [1, 1]],
        [[1], [2], [3], [4], [5], [6]],
    ]
    for lists in cases:
        res = _run(lists)
        assert res.passed, (lists, res.reason)


def test_randomized_sweep():
    rng = random.Random(20260724)
    for trial in range(60):
        lists = []
        for _ in range(rng.randint(2, 6)):
            n = 16 if trial % 3 == 0 else rng.randint(1, 16)
            base = rng.choice([10000, 100, 3])
            lists.append([rng.randint(-base, base) for _ in range(n)])
        res = _run(lists)
        assert res.passed, (trial, lists, res.reason)
