"""Release gates for the 30x30 tcp_09 repack."""

from __future__ import annotations

import hashlib
import json
import pathlib

import pytest

from littleman import server_compat
from littleman.alexey_pipecheck import check as pipe_check
from littleman.judge import footprint, judge_case, judge_problem
from littleman.sim import Machine
from littleman.tcp_fast import fuzz_orders, in_order, model_rounds, reversed_block
from littleman.tcp_hotpath import build_tcp_hotpath
from littleman.tcp_repack import build_tcp_repack

REPO = pathlib.Path(__file__).resolve().parent.parent
ARTIFACT = REPO / "submissions/tcp/tarstars_tcp_10.man"
PROBLEM = json.loads((REPO / "data/small/problems/tcp.json").read_text())
EXPECTED_SHA256 = "6cf6a21d6b38d12214c628aa614570a2dc4ec136b27e12ecff359b9bdb244765"


@pytest.fixture(scope="module")
def baseline() -> str:
    return build_tcp_hotpath()


@pytest.fixture(scope="module")
def candidate() -> str:
    return build_tcp_repack()


def _room_text(machine: Machine, room) -> str:
    return "\n".join(
        "".join(machine.grid[row][room.left : room.right + 1])
        for row in range(room.top, room.bottom + 1)
    )


def _binding_signature(program: str) -> list[tuple]:
    machine = Machine.parse(program)
    room_names = {
        id(room): (
            room.kind,
            room.bottom - room.top - 1,
            room.right - room.left - 1,
        )
        for room in machine.rooms
    }
    signature = []
    for man in machine.men:
        room = man.room
        owner = room_names[id(room)]
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
                peer = pipe.source if op == "r" else pipe.dest
                signature.append(
                    (
                        owner,
                        row - room.top - 1,
                        col - room.left - 1,
                        op,
                        room_names[id(peer)],
                    )
                )
    return sorted(signature)


def test_generator_is_exact_and_deterministic(candidate):
    assert build_tcp_repack() == build_tcp_repack()
    assert candidate == ARTIFACT.read_text()
    assert hashlib.sha256(candidate.encode()).hexdigest() == EXPECTED_SHA256


def test_repack_preserves_rooms_and_bindings(baseline, candidate):
    old, new = Machine.parse(baseline), Machine.parse(candidate)
    assert sorted(_room_text(old, room) for room in old.rooms) == sorted(
        _room_text(new, room) for room in new.rooms
    )
    assert _binding_signature(baseline) == _binding_signature(candidate)
    assert len(_binding_signature(candidate)) == 35
    assert (len(new.rooms), len(new.pipes), len(new.men)) == (6, 7, 4)


def test_layout_is_strict_and_smaller(candidate):
    assert footprint(candidate) == 900
    assert len(candidate.splitlines()) == 30
    assert max(map(len, candidate.splitlines())) == 30
    server_compat.validate_layout(candidate)
    pipe_check(candidate)


def test_public_ticks_and_score(baseline, candidate):
    old = judge_problem(baseline, PROBLEM)
    new = judge_problem(candidate, PROBLEM)
    assert (new.cases_passed, new.cases_total) == (6, 6)
    assert old.case_ticks == [406, 1240, 1210, 474, 36, 2432]
    assert new.case_ticks == [432, 1326, 1212, 391, 32, 2440]
    assert new.score == pytest.approx(874_950.0)
    assert new.score < old.score * 0.95


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
