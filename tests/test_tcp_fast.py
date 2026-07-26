"""Regression tests for the bit-packed Packet Reassembly machine."""

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
    build,
    fuzz_orders,
    in_order,
    model_rounds,
    reversed_block,
    ring_rounds,
)

REPO = pathlib.Path(__file__).resolve().parent.parent
ARTIFACT = REPO / "submissions" / "tcp" / "tcp_07.man"
PROBLEM = json.loads((REPO / "data" / "small" / "problems" / "tcp.json").read_text())


@pytest.fixture(scope="module")
def program() -> str:
    return build()


def test_generator_is_deterministic():
    assert build() == build()


def test_generator_reproduces_the_artifact(program):
    assert program == ARTIFACT.read_text()
    assert hashlib.sha256(program.encode()).hexdigest() == (
        "2009afe59f996856746901e527aa1d75be48bc7535255a0dcbc2c13af99f6cec"
    )


def test_ring_model_matches_the_specification_oracle():
    """The packing itself, not just the spec, is validated."""
    cases = [(48, in_order(48)), (48, reversed_block(48)), (1, [(0, 42)])]
    cases += [(n, o) for _, n, o in fuzz_orders(200, seed=3)]
    for n, order in cases:
        assert ring_rounds(n, order) == model_rounds(n, order)


def test_public_cases_and_score(program):
    report = judge_problem(program, PROBLEM)
    assert report.cases_passed == report.cases_total == 6
    # beats the live 37x37 machine (local score 1369 * 2505.83 = 3,431,381)
    assert report.score < 1_400_000


def test_layout_is_server_compatible(program):
    machine = Machine.parse(program)
    assert len(machine.rooms) == 6 and len(machine.men) == 4
    server_compat.validate_layout(program)
    pipe_check(program)
    assert footprint(program) == max(
        len(program.rstrip("\n").split("\n")),
        max(len(line) for line in program.split("\n")),
    ) ** 2


def test_boundary_streams(program):
    """n=1, a full window, an instant loss and fully reversed traffic."""
    cases = [
        (1, [(0, 999)]),
        (16, [(15, 900)] + [(i, i + 1) for i in range(15)]),
        (48, [(16, 5)]),                       # first packet 16 ahead: lost
        (48, in_order(48)),
        (48, reversed_block(48)),
        (32, reversed_block(32)),
    ]
    for n, order in cases:
        result = judge_case(program, model_rounds(n, order), max_ticks=60_000)
        assert result.passed, (n, order[:3], result.reason)


@pytest.mark.parametrize("seed", [11, 12, 13, 14])
def test_fuzz_streams(program, seed):
    """>= 40 randomised streams per seed: reordering, bursts, losses."""
    orders = fuzz_orders(12, seed=seed)
    assert len(orders) == 12
    for _, n, order in orders:
        result = judge_case(program, model_rounds(n, order), max_ticks=60_000)
        assert result.passed, (seed, n, result.reason)
