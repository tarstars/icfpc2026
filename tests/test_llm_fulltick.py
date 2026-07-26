"""End-to-end gates for the physical LLM runtime tick."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm_fetchjoin import fetchjoin_reference
from littleman.llm_fulltick import build_fulltick_rig, fulltick_reference
from littleman.llm_fuzz import llm_corpus
from littleman.llm_maskmap import maskmap_reference
from littleman.llm_packraw import pack_reference
from littleman.llm_perimeter import perimeter_reference
from littleman.llm_pipeaction import parse_fetched_state
from littleman.llm_pipestarts import pipestarts_reference
from littleman.llm_pipetrace import pipetrace_dest_reference
from littleman.llm_ring_exec import parse_state_stream
from littleman.llm_roomfind import roomfind_reference
from littleman.llm_scan import scan_reference
from littleman.llm_statebuild import statebuild_reference
from littleman.llm_tick_assemble import full_statecycle_reference
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/small/problems/little-little-man.json").read_text())[
    "publicTestData"
]
FUZZ = llm_corpus(20260726, 20)


def state_stream(case):
    source = [int(value) for value in case["rounds"][0]["in"]]
    stream = pack_reference(scan_reference(source))
    stream = roomfind_reference(stream)
    stream = perimeter_reference(stream)
    stream = pipestarts_reference(stream)
    stream = pipetrace_dest_reference(stream)
    return statebuild_reference(stream)


def cycle_session(stream, ticks):
    world = stream[:64]
    state = stream[64:]
    inputs = list(stream)
    expected = []
    states = []
    for tick in range(ticks):
        _raw, rooms, _pipes, _tail = parse_state_stream([*world, *state])
        if any(room.on_border(room.addr) for room in rooms if not room.ctrl & 4):
            break
        if all(room.ctrl & 4 for room in rooms):
            break
        got = fulltick_reference([*world, *state])
        oracle = full_statecycle_reference(world, state)
        assert got == oracle
        expected.extend(got)
        states.append(got)
        state = got
        if tick + 1 < ticks:
            inputs.extend(got)
    return inputs, expected, states


class Script:
    def __init__(self, inputs, expected):
        self.input = list(inputs)
        self.expected = list(expected)
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_fulltick_rig()


@pytest.mark.parametrize("case", [*CASES, *FUZZ], ids=lambda case: case["name"])
def test_reference_matches_frozen_action_oracle(case):
    stream = state_stream(case)
    _inputs, _expected, states = cycle_session(stream, 12)
    for state in states:
        rooms, _pipes = parse_fetched_state(
            # Re-fetching is performed by the next cycle; this assertion only
            # proves every emitted runtime stream remains parseable there.
            fetchjoin_reference([*stream[:64], *maskmap_reference(state)])
        )
        assert 1 <= len(rooms) <= 3


def test_generator_is_deterministic_and_server_safe(text):
    assert build_fulltick_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


def test_physical_two_cycle_state_only_recirculation(text):
    inputs, expected, states = cycle_session(state_stream(CASES[0]), 2)
    assert len(states) == 2
    script = Script(inputs, expected)
    result = Machine.parse(text).run(max_ticks=10_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected


def test_physical_nonempty_pipe_queue_regression(text):
    inputs, expected, states = cycle_session(state_stream(CASES[1]), 8)
    assert len(states) == 8
    assert any(-3600 in state and state[state.index(-3600) + 1] > 0 for state in states)
    script = Script(inputs, expected)
    result = Machine.parse(text).run(max_ticks=20_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected
