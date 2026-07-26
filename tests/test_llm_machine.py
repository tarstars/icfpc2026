"""End-to-end gates for the complete raw-input physical LLM machine."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.judge import judge_case
from littleman.llm_machine import build_llm_machine, normalize_input_reference
from littleman.llm_roomfind import SETUP_END
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/small/problems/little-little-man.json").read_text())[
    "publicTestData"
]


@pytest.fixture(scope="module")
def text() -> str:
    return build_llm_machine()


@pytest.fixture(scope="module")
def machine(text) -> Machine:
    return Machine.parse(text)


def test_normalized_input_preserves_round_commands():
    case = CASES[1]
    raw = [int(value) for value in case["rounds"][0]["in"]]
    commands = [int(round_["in"][0]) for round_ in case["rounds"][1:]]
    stream = normalize_input_reference([*raw, *commands])
    end = stream.index(SETUP_END)
    assert stream[end + 1 :] == commands


def test_generator_is_deterministic_below_limit_and_server_safe(text, machine):
    assert build_llm_machine() == text
    assert len(text.encode()) < 10_000_000
    assert len(text.splitlines()) == 25_797
    assert max(map(len, text.splitlines())) == 749
    assert hashlib.sha256(text.encode()).hexdigest() == (
        "568d0b87937e9a41370d0b3434583d7109eb51ea9944b788e825e45c53e40ff6"
    )
    assert len(machine.rooms) == 145
    assert len(machine.pipes) == 231
    assert len(machine.men) == 143
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


def test_whole_machine_pipe_bindings_are_frozen_with_margin(machine):
    pipe_index = {id(pipe): index for index, pipe in enumerate(machine.pipes)}
    resolution = []
    margins = []
    for room in machine.rooms:
        incoming = machine.in_pipes.get(id(room), [])
        outgoing = machine.out_pipes.get(id(room), [])
        rows, cols = room.interior()
        for row in rows:
            for col in cols:
                op = machine.grid[row][col]
                if op in "srq":
                    pipes = outgoing if op == "s" else incoming
                    endpoint = 0 if op == "s" else -1
                    ranked = sorted(
                        (
                            abs(pipe.cells[endpoint][0] - row)
                            + abs(pipe.cells[endpoint][1] - col),
                            pipe.cells[endpoint],
                            pipe_index[id(pipe)],
                        )
                        for pipe in pipes
                    )
                    assert ranked, (row, col, op)
                    resolution.append((row, col, op, ranked[0][2]))
                    if len(ranked) > 1:
                        margins.append(ranked[1][0] - ranked[0][0])
                elif op in "SRU":
                    pipes = outgoing if op == "S" else incoming
                    endpoint = 0 if op == "S" else -1
                    ordered = sorted(pipes, key=lambda pipe: pipe.cells[endpoint])
                    assert ordered, (row, col, op)
                    resolution.append(
                        (
                            row,
                            col,
                            op,
                            [pipe_index[id(pipe)] for pipe in ordered],
                        )
                    )

    encoded = json.dumps(resolution, separators=(",", ":")).encode()
    assert len(resolution) == 13_299
    assert min(margins) == 3
    assert hashlib.sha256(encoded).hexdigest() == (
        "491f6e5f195c396bcc99c653c9433e1bba1cd02659a121624c14bb00f980cccf"
    )


def test_raw_first_steps_passes_all_four_rounds(text):
    result = judge_case(text, CASES[0]["rounds"], max_ticks=35_000_000)
    assert result.passed, result.reason
