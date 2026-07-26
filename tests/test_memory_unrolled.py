"""Correctness and performance gates for the two-word ``memory_13`` STATION."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

import pytest

from littleman import server_compat
from littleman.alexey_pipecheck import check as pipe_check
from littleman.fastsim import Machine as FastMachine
from littleman.judge import footprint
from littleman.memory_unrolled import (
    CANDIDATE_SHA256,
    PARENT_SHA256,
    apply_memory12_unroll,
    build_memory_unrolled,
)
from littleman.sim import Machine

REPO = Path(__file__).resolve().parents[1]
PARENT = REPO / "submissions/memory/memory_12.man"
ARTIFACT = REPO / "submissions/memory/memory_13.man"
PROBLEM = json.loads((REPO / "data/small/problems/memory.json").read_text())


def oracle(tokens: list[int]) -> list[int]:
    cells = [0] * 100
    output: list[int] = []
    cursor = 0
    while cursor < len(tokens):
        tag, address = tokens[cursor : cursor + 2]
        cursor += 2
        if tag == 0:
            output.append(cells[address])
        else:
            cells[address] = tokens[cursor]
            cursor += 1
    return output


def run(program: str, tokens: list[int]) -> list[int]:
    result = FastMachine.parse(program).run(inputs=tokens, max_ticks=5_000_000)
    assert result.error is None, result.error
    return result.output


@pytest.fixture(scope="module")
def program() -> str:
    return build_memory_unrolled()


def test_exact_parent_transform_and_artifact(program: str):
    parent = PARENT.read_text()
    assert hashlib.sha256(parent.encode()).hexdigest() == PARENT_SHA256
    assert hashlib.sha256(program.encode()).hexdigest() == CANDIDATE_SHA256
    assert apply_memory12_unroll(parent) == program
    assert ARTIFACT.read_text() == program


def test_layout_and_unchanged_pipes(program: str):
    parent = Machine.parse(PARENT.read_text())
    machine = Machine.parse(program)
    server_compat.validate_layout(program)
    pipe_check(program)
    assert footprint(program) == 900
    assert (len(machine.rooms), len(machine.pipes), len(machine.men)) == (7, 7, 5)
    assert (machine.rooms[4].bottom, machine.rooms[4].right) == (29, 21)
    assert [pipe.cells for pipe in machine.pipes] == [
        pipe.cells for pipe in parent.pipes
    ]


def test_public_cases_and_exact_ticks(program: str):
    report = server_compat.judge_problem(program, PROBLEM)
    assert (report.cases_passed, report.cases_total) == (7, 7)
    assert report.case_ticks == [286, 557, 1302, 989, 1284, 813, 18448]
    assert report.score == 3_044_442.8571428573


def _ports(machine: Machine, glyph: str) -> dict[tuple[int, int], int]:
    station = machine.rooms[4]
    result = {}

    class Probe:
        room = station

    for row in range(station.top + 1, station.bottom):
        for column in range(station.left + 1, station.right):
            if machine.grid[row][column] != glyph:
                continue
            probe = Probe()
            probe.r, probe.c = row, column
            pipe = (
                machine._nearest_incoming(probe)
                if glyph == "r"
                else machine._nearest_outgoing(probe)
            )
            result[(row, column)] = machine.pipes.index(pipe)
    return result


def test_every_station_pipe_instruction_has_the_intended_binding(program: str):
    machine = Machine.parse(program)
    assert _ports(machine, "r") == {
        (18, 5): 3,
        (18, 7): 3,
        (18, 9): 3,
        (18, 13): 6,
        (19, 7): 3,
        (19, 9): 3,
        (20, 18): 6,
        (21, 15): 6,
        (22, 19): 6,
        (26, 11): 3,
        (26, 19): 6,
    }
    assert _ports(machine, "s") == {
        (17, 19): 5,
        (19, 14): 5,
        (21, 18): 5,
        (21, 19): 5,
        (22, 15): 5,
        (25, 8): 4,
        (27, 17): 5,
    }


def distance_stream(tag: int) -> list[int]:
    """Exercise every ring distance k=0..33 exactly once."""

    tokens: list[int] = []
    head = 0
    for distance in range(34):
        word = (head + distance) % 34
        address = 3 * word
        if tag:
            tokens.extend((1, address, distance * 101 - 1700))
        else:
            tokens.extend((0, address))
        head = (word + 1) % 34
    return tokens


@pytest.mark.parametrize("tag", (0, 1))
def test_every_even_and_odd_ring_distance(program: str, tag: int):
    tokens = distance_stream(tag)
    if tag:
        tokens.extend((0, 0, 0, 99))
    assert run(program, tokens) == oracle(tokens)


def random_stream(seed: int) -> list[int]:
    rng = random.Random(seed)
    limit = rng.randint(300, 1000)
    tokens: list[int] = []
    reads = 0
    while len(tokens) + 3 <= limit:
        address = rng.randrange(100)
        if rng.randrange(2):
            tokens.extend((1, address, rng.randint(-1_000_000, 1_000_000)))
        else:
            tokens.extend((0, address))
            reads += 1
    if not reads and len(tokens) + 2 <= 1000:
        tokens.extend((0, 0))
    return tokens


@pytest.mark.parametrize("seed", range(100))
def test_one_hundred_maximal_random_streams(program: str, seed: int):
    tokens = random_stream(20260727 + seed)
    assert run(program, tokens) == oracle(tokens)


@pytest.mark.parametrize("stride", (1, 3, 17, 33, 49, 67, 97, 99))
def test_directed_stride_and_extreme_streams(program: str, stride: int):
    tokens: list[int] = []
    values = (-1_000_000, -1, 0, 1, 1_000_000)
    for index in range(100):
        address = (index * stride) % 100
        tokens.extend((1, address, values[index % len(values)], 0, address))
    assert len(tokens) == 500
    assert run(program, tokens) == oracle(tokens)
