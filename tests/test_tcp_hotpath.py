"""Release gates for the tcp_09 controller-return shortcut."""

from __future__ import annotations

import hashlib
import json
import pathlib

import pytest

from littleman import server_compat
from littleman.alexey_pipecheck import check as pipe_check
from littleman.judge import footprint, judge_case, judge_problem
from littleman.sim import Machine
from littleman.tcp_fast import (
    build_compact,
    fuzz_orders,
    in_order,
    model_rounds,
    reversed_block,
)
from littleman.tcp_hotpath import build_tcp_hotpath

REPO = pathlib.Path(__file__).resolve().parent.parent
ARTIFACT = REPO / "submissions" / "tcp" / "tcp_09.man"
PROBLEM = json.loads((REPO / "data/small/problems/tcp.json").read_text())
EXPECTED_SHA256 = "9b90f6e8684abd5fa27db830e45956b7bc927421f457e5fe516e7ac26ea39457"


@pytest.fixture(scope="module")
def baseline() -> str:
    return build_compact()


@pytest.fixture(scope="module")
def candidate() -> str:
    return build_tcp_hotpath()


def _binding_signature(program: str) -> list[tuple]:
    machine = Machine.parse(program)
    signature = []
    for man in machine.men:
        room = man.room
        for row in range(room.top + 1, room.bottom):
            for col in range(room.left + 1, room.right):
                op = machine.grid[row][col]
                if op not in "rs":
                    continue
                man.r, man.c = row, col
                pipe = (
                    machine._nearest_incoming(man)
                    if op == "r"
                    else machine._nearest_outgoing(man)
                )
                signature.append(
                    (room.top, room.left, row, col, op, machine.pipes.index(pipe))
                )
    return signature


def test_generator_is_deterministic_and_reproduces_artifact(candidate):
    assert build_tcp_hotpath() == build_tcp_hotpath()
    assert candidate == ARTIFACT.read_text()
    assert hashlib.sha256(candidate.encode()).hexdigest() == EXPECTED_SHA256


def test_only_the_two_safe_cells_change(baseline, candidate):
    assert len(baseline) == len(candidate)
    diffs = [
        (row, col, old, new)
        for row, (old_row, new_row) in enumerate(
            zip(baseline.splitlines(), candidate.splitlines(), strict=True)
        )
        for col, (old, new) in enumerate(zip(old_row, new_row, strict=True))
        if old != new
    ]
    assert diffs == [(22, 3, " ", ">"), (28, 3, " ", "^")]


def test_layout_and_every_pipe_binding_are_unchanged(baseline, candidate):
    old, new = Machine.parse(baseline), Machine.parse(candidate)
    assert (len(new.rooms), len(new.pipes), len(new.men)) == (6, 7, 4)
    assert [pipe.cells for pipe in old.pipes] == [pipe.cells for pipe in new.pipes]
    assert _binding_signature(baseline) == _binding_signature(candidate)
    bindings = _binding_signature(candidate)
    assert len(bindings) == 35
    assert (
        sum(room_top == 17 and room_left == 0 for room_top, room_left, *_ in bindings)
        == 18
    )
    assert footprint(candidate) == 961
    server_compat.validate_layout(candidate)
    pipe_check(candidate)


def test_public_cases_save_more_than_the_next_rank_threshold(baseline, candidate):
    old = judge_problem(baseline, PROBLEM)
    new = judge_problem(candidate, PROBLEM)
    assert (new.cases_passed, new.cases_total) == (6, 6)
    assert old.case_ticks == [406, 1244, 1270, 474, 36, 2552]
    assert new.case_ticks == [406, 1240, 1210, 474, 36, 2432]
    assert new.score == pytest.approx(928_646.3333333334)
    assert new.score < old.score * 0.97


@pytest.mark.parametrize(
    ("n", "order"),
    [
        (1, [(0, 999)]),
        (16, [(15, 900)] + [(i, i + 1) for i in range(15)]),
        (48, [(16, 5)]),
        (48, in_order(48)),
        (48, reversed_block(48)),
        (32, reversed_block(32)),
    ],
)
def test_boundary_streams(candidate, n, order):
    result = judge_case(candidate, model_rounds(n, order), max_ticks=60_000)
    assert result.passed, (n, order[:3], result.reason)


@pytest.mark.parametrize("seed", [0, 83, 20260727])
def test_differential_fuzz_has_no_candidate_only_failure(baseline, candidate, seed):
    for name, n, order in fuzz_orders(256, seed=seed):
        rounds = model_rounds(n, order)
        old = judge_case(baseline, rounds, max_ticks=60_000)
        new = judge_case(candidate, rounds, max_ticks=60_000)
        assert not (old.passed and not new.passed), (
            seed,
            name,
            n,
            old.reason,
            new.reason,
        )
