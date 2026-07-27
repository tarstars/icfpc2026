"""Release gates for the 29x28 Packet Reassembly repack."""

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
from littleman.tcp_repack import build_tcp_repack
from littleman.tcp_square import build_tcp_square

REPO = pathlib.Path(__file__).resolve().parent.parent
ARTIFACT = REPO / "submissions/tcp/tarstars_tcp_11.man"
PROBLEM = json.loads((REPO / "data/small/problems/tcp.json").read_text())
EXPECTED_SHA256 = "08b01eb131db4c42d7f076a3f4f4663a94a863a9452ff3f14c2dd637baf05dac"

BASELINE_ROOMS = {
    (0, 5): "E",
    (2, 0): "O",
    (6, 20): "I",
    (10, 11): "P",
    (16, 5): "C",
    (19, 25): "R",
}
CANDIDATE_ROOMS = {
    (0, 5): "E",
    (2, 0): "O",
    (6, 20): "I",
    (0, 23): "P",
    (14, 4): "C",
    (17, 24): "R",
}


@pytest.fixture(scope="module")
def baseline() -> str:
    return build_tcp_repack()


@pytest.fixture(scope="module")
def candidate() -> str:
    return build_tcp_square()


def _room_text(machine: Machine, room) -> str:
    return "\n".join(
        "".join(machine.grid[row][room.left : room.right + 1])
        for row in range(room.top, room.bottom + 1)
    )


def _binding_signature(
    program: str,
    room_labels: dict[tuple[int, int], str],
    *,
    rotated_p: bool = False,
) -> list[tuple]:
    machine = Machine.parse(program)
    labels = {
        id(room): room_labels[(room.top, room.left)] for room in machine.rooms
    }
    signature = []
    for man in machine.men:
        room = man.room
        owner = labels[id(room)]
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
                local_row = row - room.top - 1
                local_col = col - room.left - 1
                if rotated_p and owner == "P":
                    local_row, local_col = 3 - local_col, local_row
                signature.append(
                    (owner, local_row, local_col, op, labels[id(peer)])
                )
    return sorted(signature)


def test_generator_is_exact_and_deterministic(candidate):
    assert build_tcp_square() == build_tcp_square()
    assert candidate == ARTIFACT.read_text()
    assert hashlib.sha256(candidate.encode()).hexdigest() == EXPECTED_SHA256


def test_repack_preserves_rooms_and_bindings(baseline, candidate):
    old, new = Machine.parse(baseline), Machine.parse(candidate)
    old_rooms = {
        BASELINE_ROOMS[(room.top, room.left)]: _room_text(old, room)
        for room in old.rooms
    }
    new_rooms = {
        CANDIDATE_ROOMS[(room.top, room.left)]: _room_text(new, room)
        for room in new.rooms
    }
    assert old_rooms["E"] == new_rooms["E"]
    assert old_rooms["O"] == new_rooms["O"]
    assert old_rooms["I"] == new_rooms["I"]
    assert old_rooms["C"] == new_rooms["C"]
    assert old_rooms["R"] == new_rooms["R"]
    assert (len(old_rooms["P"].splitlines()), len(old_rooms["P"].splitlines()[0])) == (
        len(new_rooms["P"].splitlines()[0]),
        len(new_rooms["P"].splitlines()),
    )

    old_bindings = _binding_signature(baseline, BASELINE_ROOMS)
    new_bindings = _binding_signature(
        candidate, CANDIDATE_ROOMS, rotated_p=True
    )
    assert new_bindings == old_bindings
    assert len(new_bindings) == 35
    assert (len(new.rooms), len(new.pipes), len(new.men)) == (6, 7, 4)


def test_layout_is_strict_and_smaller(candidate):
    assert footprint(candidate) == 841
    assert len(candidate.splitlines()) == 28
    assert max(map(len, candidate.splitlines())) == 29
    server_compat.validate_layout(candidate)
    pipe_check(candidate)
    assert sorted(len(pipe.cells) for pipe in Machine.parse(candidate).pipes) == [
        2,
        2,
        2,
        2,
        5,
        5,
        12,
    ]


def test_public_ticks_and_score(baseline, candidate):
    old = judge_problem(baseline, PROBLEM)
    new = judge_problem(candidate, PROBLEM)
    assert (new.cases_passed, new.cases_total) == (6, 6)
    assert old.case_ticks == [432, 1326, 1212, 391, 32, 2440]
    assert new.case_ticks == [377, 1161, 1201, 470, 32, 2418]
    assert new.score == pytest.approx(793_203.1666666666)
    assert new.score < old.score * 0.91


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
def test_differential_fuzz_has_no_candidate_only_failure(
    baseline, candidate, seed
):
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
