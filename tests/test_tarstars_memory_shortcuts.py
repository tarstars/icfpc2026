"""Release gates for the bounded ``memory_13`` WRITE shortcuts."""

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
from littleman.sim import Machine
from littleman.tarstars_memory_shortcuts import (
    CANDIDATE_SHA256,
    PARENT_SHA256,
    apply_tarstars_memory_shortcuts,
    build_tarstars_memory_shortcuts,
)

REPO = Path(__file__).resolve().parents[1]
PARENT = REPO / "submissions/memory/memory_13.man"
ARTIFACT = REPO / "submissions/memory/tarstars_memory_14.man"
PROBLEM = json.loads((REPO / "data/small/problems/memory.json").read_text())


def oracle(tokens: list[int]) -> list[int]:
    cells = [0] * 100
    output = []
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
    return build_tarstars_memory_shortcuts()


def test_exact_transform_artifact_and_hash(program: str):
    parent = PARENT.read_text()
    assert hashlib.sha256(parent.encode()).hexdigest() == PARENT_SHA256
    assert hashlib.sha256(program.encode()).hexdigest() == CANDIDATE_SHA256
    assert apply_tarstars_memory_shortcuts(parent) == program
    assert ARTIFACT.read_text() == program


def test_layout_pipes_and_changed_bindings(program: str):
    parent = Machine.parse(PARENT.read_text())
    machine = Machine.parse(program)
    server_compat.validate_layout(program)
    pipe_check(program)
    assert footprint(program) == 900
    assert [pipe.cells for pipe in machine.pipes] == [
        pipe.cells for pipe in parent.pipes
    ]

    station = machine.rooms[4]

    class Probe:
        room = station

    command_receive = Probe()
    command_receive.r, command_receive.c = 26, 12
    ring_send = Probe()
    ring_send.r, ring_send.c = 27, 13
    assert machine.pipes.index(machine._nearest_incoming(command_receive)) == 3
    assert machine.pipes.index(machine._nearest_outgoing(ring_send)) == 5


def test_public_cases_clear_the_rank_target(program: str):
    report = server_compat.judge_problem(program, PROBLEM)
    assert (report.cases_passed, report.cases_total) == (7, 7)
    assert report.case_ticks == [286, 547, 1272, 969, 1264, 813, 17948]
    assert report.score == 2_969_871.428571428
    assert report.score < 3_044_442.8571428573 * 0.977


def distance_stream(tag: int) -> list[int]:
    tokens = []
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
def test_every_ring_distance(program: str, tag: int):
    tokens = distance_stream(tag)
    if tag:
        tokens.extend((0, 0, 0, 99))
    assert run(program, tokens) == oracle(tokens)


def random_stream(seed: int) -> list[int]:
    rng = random.Random(seed)
    limit = rng.randint(300, 1000)
    tokens = []
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
def test_random_streams(program: str, seed: int):
    tokens = random_stream(20260727 + seed)
    assert run(program, tokens) == oracle(tokens)
