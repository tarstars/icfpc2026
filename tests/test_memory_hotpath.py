"""Release and adversarial gates for the geometry-only ``memory_12``."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

from littleman import server_compat
from littleman.alexey_pipecheck import check as pipe_check
from littleman.fastsim import Machine as FastMachine
from littleman.judge import footprint
from littleman.memory_hotpath import (
    CANDIDATE_SHA256,
    PARENT_SHA256,
    PATCHES,
    apply_memory11_hotpath,
    build_memory_hotpath,
)
from littleman.sim import Machine

REPO = Path(__file__).resolve().parents[1]
PARENT = REPO / "submissions/memory/memory_11.man"
ARTIFACT = REPO / "submissions/memory/memory_12.man"
PROBLEM = json.loads((REPO / "data/small/problems/memory.json").read_text())


def oracle(tokens: list[int]) -> list[int]:
    cells = [0] * 100
    output: list[int] = []
    cursor = 0
    while cursor < len(tokens):
        op, address = tokens[cursor : cursor + 2]
        cursor += 2
        if op == 0:
            output.append(cells[address])
        else:
            cells[address] = tokens[cursor]
            cursor += 1
    return output


def run(program: str, tokens: list[int]) -> list[int]:
    result = FastMachine.parse(program).run(inputs=tokens, max_ticks=5_000_000)
    assert result.error is None, result.error
    return result.output


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


def stride_stream(stride: int) -> list[int]:
    tokens: list[int] = []
    for index in range(100):
        address = (index * stride) % 100
        value = (-1_000_000, -1, 0, 1, 1_000_000)[index % 5]
        tokens.extend((1, address, value, 0, address))
    return tokens


def test_exact_parent_transform_and_artifact_identity():
    parent = PARENT.read_text()
    candidate = ARTIFACT.read_text()
    assert hashlib.sha256(parent.encode()).hexdigest() == PARENT_SHA256
    assert hashlib.sha256(candidate.encode()).hexdigest() == CANDIDATE_SHA256
    assert apply_memory11_hotpath(parent) == candidate
    assert build_memory_hotpath() == candidate
    assert len(parent.encode()) == len(candidate.encode()) == 794


def test_only_the_six_guarded_station_cells_change():
    parent = PARENT.read_text().splitlines()
    candidate = ARTIFACT.read_text().splitlines()
    differences = {
        (row, column, parent[row][column], candidate[row][column])
        for row in range(len(parent))
        for column in range(len(parent[row]))
        if parent[row][column] != candidate[row][column]
    }
    assert differences == set(PATCHES)


def test_layout_pipe_geometry_and_bindings_are_preserved():
    parent = Machine.parse(PARENT.read_text())
    candidate_text = ARTIFACT.read_text()
    candidate = Machine.parse(candidate_text)
    server_compat.validate_layout(candidate_text)
    pipe_check(candidate_text)
    assert footprint(candidate_text) == 841
    assert (len(candidate.rooms), len(candidate.pipes), len(candidate.men)) == (7, 7, 5)
    assert [len(pipe.cells) for pipe in candidate.pipes] == [2, 10, 2, 4, 10, 13, 21]
    assert [pipe.cells for pipe in candidate.pipes] == [
        pipe.cells for pipe in parent.pipes
    ]

    station = candidate.rooms[4]

    class Probe:
        room = station

    outgoing = []
    for row, column in ((21, 6), (26, 13)):
        probe = Probe()
        probe.r, probe.c = row, column
        chosen = candidate._nearest_outgoing(probe)
        ranked = sorted(
            abs(pipe.cells[0][0] - row) + abs(pipe.cells[0][1] - column)
            for pipe in candidate._outgoing(probe)
        )
        outgoing.append(candidate.pipes.index(chosen))
        assert ranked[1] > ranked[0]
    assert outgoing == [4, 5]  # READ -> O; WRITE -> ring


def test_public_cases_and_exact_ticks():
    report = server_compat.judge_problem(ARTIFACT.read_text(), PROBLEM)
    assert (report.cases_passed, report.cases_total) == (7, 7)
    assert report.case_ticks == [292, 608, 1510, 1082, 1512, 908, 20656]
    assert report.score == 3_191_955.4285714286


def test_live_response_matches_exact_artifact():
    response = json.loads(ARTIFACT.with_name("memory_12-submit.json").read_text())
    assert response["id"] == "397eaeb4-1236-4e0f-8b2d-b2ac089050f4"
    assert response["casesPassed"] == response["casesTotal"] == 24
    assert (response["width"], response["height"], response["area2"]) == (29, 29, 841)
    assert response["avgTicks"] == 18372.291666666668
    assert response["score"] == 15451097.291666668


def test_one_hundred_maximal_random_streams_match_oracle():
    program = ARTIFACT.read_text()
    for seed in range(100):
        tokens = random_stream(20260727 + seed)
        assert len(tokens) <= 1000
        assert run(program, tokens) == oracle(tokens)


def test_directed_stride_and_extreme_streams_match_oracle():
    program = ARTIFACT.read_text()
    for stride in (1, 3, 17, 33, 49, 67, 97, 99):
        tokens = stride_stream(stride)
        assert len(tokens) == 500
        assert run(program, tokens) == oracle(tokens)
