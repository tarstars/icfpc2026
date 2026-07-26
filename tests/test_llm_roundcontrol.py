"""Persistent physical round-loop gates for the LLM machine."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.judge import judge_case
from littleman.llm_packraw import pack_reference
from littleman.llm_perimeter import perimeter_reference
from littleman.llm_pipestarts import pipestarts_reference
from littleman.llm_pipetrace import pipetrace_dest_reference
from littleman.llm_roomfind import SETUP_END, roomfind_reference
from littleman.llm_roundcontrol import (
    build_runtime_loop_rig,
    copydemux_reference,
    round_states_reference,
    setupdemux_reference,
)
from littleman.llm_scan import scan_reference
from littleman.llm_statebuild import statebuild_reference
from littleman.llm_statecopy import COPY_END, COPY_SPLIT, statecopy_reference
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASE = json.loads((ROOT / "data/small/problems/little-little-man.json").read_text())[
    "publicTestData"
][0]


def state_stream() -> list[int]:
    source = [int(value) for value in CASE["rounds"][0]["in"]]
    stream = pack_reference(scan_reference(source))
    stream = roomfind_reference(stream)
    stream = perimeter_reference(stream)
    stream = pipestarts_reference(stream)
    stream = pipetrace_dest_reference(stream)
    return statebuild_reference(stream)


@pytest.fixture(scope="module")
def text() -> str:
    return build_runtime_loop_rig()


def test_reference_demultiplexers_preserve_the_frozen_stream():
    state = state_stream()
    setup, commands = setupdemux_reference([*state, 1, 3])
    assert setup[-1] == SETUP_END
    assert setup == state
    assert commands == [1, 3]

    copied = statecopy_reference(state)
    assert copied[-1] == COPY_END
    assert copied.count(COPY_SPLIT) == 1
    assert copydemux_reference(copied) == (state, state)


def test_reference_round_loop_advances_each_command():
    states = round_states_reference([*state_stream(), 1, 1, 1])
    assert len(states) == 4
    assert states[0][-1] == SETUP_END
    assert all(state[-1] == SETUP_END for state in states[1:])


def test_generator_is_deterministic_below_limit_and_server_safe(text):
    assert build_runtime_loop_rig() == text
    assert len(text.encode()) < 10_000_000
    machine = Machine.parse(text)
    assert len(machine.rooms) == 128
    assert len(machine.pipes) == 204
    assert len(machine.men) == 126
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


def test_first_steps_persists_for_all_four_rounds(text):
    rounds = [
        {"in": state_stream(), "frames": CASE["rounds"][0]["frames"]},
        *[
            {
                "in": [int(value) for value in round_["in"]],
                "frames": round_["frames"],
            }
            for round_ in CASE["rounds"][1:]
        ],
    ]
    result = judge_case(text, rounds, max_ticks=30_000_000)
    assert result.passed, result.reason
