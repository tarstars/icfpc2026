"""Component gates for the folded Matrix Multiply controller."""

from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path

import pytest

from littleman.ir_export import machine_ir
from littleman.judge import footprint, judge_case, judge_problem
from littleman.matmul_components import build_matmul_controller_folded
from littleman.server_compat import validate_layout
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "submissions" / "matmul" / "matmul_06.man"
ARTIFACT = ROOT / "submissions" / "matmul" / "matmul_07.man"
PROBLEM = ROOT / "data" / "small" / "problems" / "matmul.json"


@pytest.fixture(scope="module")
def base():
    return BASE.read_text()


@pytest.fixture(scope="module")
def candidate(base):
    return build_matmul_controller_folded(base)


def _room_name(machine, room):
    if room is machine.rooms[0]:
        return "controller"
    if room.kind != "room":
        return room.kind
    return f"relay@{room.left}"


def _resolution_signature(text):
    machine = Machine.parse(text)
    pipes = list(machine.pipes)
    roles = {
        index: (
            _room_name(machine, pipe.source),
            _room_name(machine, pipe.dest),
        )
        for index, pipe in enumerate(pipes)
    }
    signature = Counter()
    for key, entry in machine_ir(text)["resolution"].items():
        row, col = map(int, key.split(","))
        if not machine.rooms[0].contains_interior(row, col):
            continue
        pipe_ids = [entry["pipe"]] if "pipe" in entry else entry["pipes"]
        signature[
            (
                entry["op"],
                tuple(sorted(roles[index] for index in pipe_ids if index is not None)),
            )
        ] += 1
    return signature


def test_controller_contract_and_single_wall_precondition(base):
    machine = Machine.parse(base)
    controller = machine.rooms[0]
    incoming = machine.in_pipes[id(controller)]
    outgoing = machine.out_pipes[id(controller)]
    assert len(incoming) == len(outgoing) == 9
    assert all(pipe.cells[-1][0] == controller.bottom + 1 for pipe in incoming)
    assert all(pipe.cells[0][0] == controller.bottom + 1 for pipe in outgoing)


def test_fold_is_deterministic_and_matches_artifact(base, candidate):
    assert build_matmul_controller_folded(base) == candidate
    assert ARTIFACT.read_text() == candidate


def test_fold_preserves_every_controller_pipe_role(base, candidate):
    assert _resolution_signature(candidate) == _resolution_signature(base)


def test_folded_shape_capacity_and_layout(candidate):
    machine = Machine.parse(candidate)
    controller = machine.rooms[0]
    assert (max(map(len, candidate.splitlines())), len(candidate.splitlines())) == (
        115,
        98,
    )
    assert (controller.right - controller.left + 1) == 109
    assert (controller.bottom - controller.top + 1) == 80
    assert footprint(candidate) == 13_225
    assert sorted(len(pipe.cells) for pipe in machine.pipes)[-2:] == [256, 268]
    validate_layout(candidate)


def test_folded_machine_passes_public_cases_with_exact_ticks(candidate):
    report = judge_problem(candidate, json.loads(PROBLEM.read_text()))
    assert report.cases_passed == report.cases_total == 7
    assert report.case_ticks == [
        16_882,
        22_698,
        76_614,
        2_610_270,
        484_958,
        131_968,
        268_790,
    ]


def _matmul_round(n, m, k, a, b):
    output = [
        sum(a[row * m + inner] * b[inner * k + col] for inner in range(m))
        for row in range(n)
        for col in range(k)
    ]
    return {"in": [n, m, k, *a, *b], "out": output}


def test_folded_machine_passes_deterministic_adversarial_cases(candidate):
    rng = random.Random(20260726)
    dimensions = [
        (2, 16, 2),
        (2, 2, 16),
        (16, 2, 2),
        (3, 5, 4),
        (6, 6, 6),
        (16, 16, 16),
    ]
    for index, (n, m, k) in enumerate(dimensions):
        if index == 0:
            a = [(-99 if item % 2 else 99) for item in range(n * m)]
            b = [(99 if item % 3 else -99) for item in range(m * k)]
        else:
            a = [rng.randint(-99, 99) for _ in range(n * m)]
            b = [rng.randint(-99, 99) for _ in range(m * k)]
        round_ = _matmul_round(n, m, k, a, b)
        result = judge_case(candidate, [round_])
        assert result.passed, (round_, result)
