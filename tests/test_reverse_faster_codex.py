"""Gates for the 14-square double-extraction Reverse machine."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from littleman import judge, rustexec
from littleman.judge import footprint, judge_case, judge_problem
from littleman.reverse_faster import build_reverse_faster
from littleman.reverse_faster_codex import build_reverse_faster_codex
from littleman.server_compat import validate_layout
from littleman.sim import Machine, Man

REPO = Path(__file__).resolve().parent.parent
ARTIFACT = REPO / "submissions/reverse-a-list/reverse_06.man"
PROBLEM = json.loads((REPO / "data/small/problems/reverse-a-list.json").read_text())


def _round(values):
    return {
        "in": [str(len(values)), *(str(value) for value in values)],
        "out": [str(value) for value in reversed(values)],
    }


def test_generator_is_deterministic_and_matches_artifact():
    generated = build_reverse_faster_codex()
    assert generated == build_reverse_faster_codex()
    assert ARTIFACT.read_text() == generated


def test_exact_geometry_structure_and_server_layout():
    source = build_reverse_faster_codex()
    assert len(source.splitlines()) == 14
    assert max(map(len, source.splitlines())) == 14
    assert footprint(source) == 196
    machine = Machine.parse(source)
    assert len(machine.rooms) == 4
    assert len(machine.pipes) == 4
    assert [len(pipe.cells) for pipe in machine.pipes] == [6, 15, 2, 2]
    validate_layout(source)


def test_no_pipe_grazes_an_unintended_room():
    machine = Machine.parse(build_reverse_faster_codex())
    neighbors = ((-1, 0), (1, 0), (0, -1), (0, 1))
    for pipe in machine.pipes:
        intended = (pipe.source, pipe.dest)
        for row, column in pipe.cells:
            for room in machine.rooms:
                if room in intended:
                    continue
                assert not any(
                    room.on_border(row + dr, column + dc) for dr, dc in neighbors
                )


def test_every_pipe_operation_keeps_its_protocol_role():
    machine = Machine.parse(build_reverse_faster_codex())
    expected = {
        (2, 11, "r"): 3,
        (3, 6, "s"): 1,
        (3, 8, "r"): 3,
        (3, 9, "s"): 2,
        (5, 10, "r"): 3,
        (6, 7, "s"): 1,
        (6, 12, "s"): 2,
        (7, 10, "s"): 2,
        (11, 2, "s"): 3,
    }
    actual = {}
    for room in machine.rooms:
        if room.kind != "room":
            continue
        for row in range(room.top + 1, room.bottom):
            for column in range(room.left + 1, room.right):
                operation = machine.grid[row][column]
                if operation not in "rs":
                    continue
                man = Man(row, column, room)
                pipe = (
                    machine._nearest_outgoing(man)
                    if operation == "s"
                    else machine._nearest_incoming(man)
                )
                actual[(row, column, operation)] = machine.pipes.index(pipe)
    assert actual == expected
    relay = machine.men[1]
    incoming = machine._incoming(relay)
    assert [
        machine.pipes.index(pipe)
        for pipe in sorted(incoming, key=lambda pipe: pipe.cells[-1])
    ] == [0, 1]


def test_public_cases_pass_and_beat_parent():
    parent = judge_problem(build_reverse_faster(), PROBLEM)
    compact = judge_problem(build_reverse_faster_codex(), PROBLEM)
    assert compact.cases_passed == compact.cases_total == 8
    assert compact.case_ticks == [99, 162, 172, 304, 130, 52, 548, 1382]
    assert compact.score == 69_800.5
    assert compact.score < parent.score * 0.95


def test_edge_shapes_multiround_and_fuzz():
    workloads = [
        [[7]],
        [[1, 2]],
        [[3, 1, 4]],
        [list(range(16))],
        [[-1_000_000, 1_000_000] * 8],
        [[5] * 16],
        [[9], [8, 7], [1] * 15],
        [[7], [7], [7]],
    ]
    generator = random.Random(20260726)
    for _ in range(300):
        workloads.append(
            [
                [
                    generator.randint(-1_000_000, 1_000_000)
                    for _ in range(generator.randint(1, 16))
                ]
                for _ in range(generator.randint(1, 4))
            ]
        )
    source = build_reverse_faster_codex()
    for lists in workloads:
        result = judge_case(source, [_round(values) for values in lists], 200_000)
        assert result.passed, (lists, result.reason)


def test_full_size_ring_reaches_exact_capacity():
    source = build_reverse_faster_codex()
    machine = Machine.parse(source)
    ring = machine.pipes[1]
    maximum = 0
    original_put = ring.put

    def tracked_put(index, value):
        nonlocal maximum
        original_put(index, value)
        maximum = max(maximum, ring.count)

    ring.put = tracked_put
    rounds = [_round(list(range(16)))]
    controller = judge.RoundController(rounds)
    result = machine.run(max_ticks=200_000, controller=controller)
    assert result.status == "passed"
    assert maximum == len(ring.cells) == 15


@pytest.mark.skipif(not rustexec.HAVE_RUST, reason="native executor is not built")
def test_complete_public_cases_match_rust():
    source = build_reverse_faster_codex()
    for case in PROBLEM["publicTestData"]:
        rounds = judge.normalize_case(case)
        reference_controller = judge.RoundController(rounds)
        rust_controller = judge.RoundController(rounds)
        reference = rustexec.ReferenceMachine.parse(source).run(
            max_ticks=PROBLEM["tickCap"] or 5_000_000,
            controller=reference_controller,
        )
        native = rustexec.Machine.parse(source).run(
            max_ticks=PROBLEM["tickCap"] or 5_000_000,
            controller=rust_controller,
        )
        assert (
            native.status,
            native.error,
            native.ticks,
            native.output,
            native.output_ticks,
        ) == (
            reference.status,
            reference.error,
            reference.ticks,
            reference.output,
            reference.output_ticks,
        )
