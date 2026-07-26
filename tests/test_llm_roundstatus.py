"""Physical gates for the LLM pre-tick stop predicate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm_fulltick import fulltick_reference
from littleman.llm_machine import normalize_input_reference
from littleman.llm_perimeter import ROOM_END
from littleman.llm_pipetrace import PIPE_END
from littleman.llm_roomfind import SETUP_END, WORLD_WORDS
from littleman.llm_roundstatus import (
    build_roundstatus_rig,
    room_statuses_reference,
    roundstatus_reference,
)
from littleman.llm_statebuild import PIPE_MASK, PIPE_VALUES
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/small/problems/little-little-man.json").read_text())[
    "publicTestData"
]


def runtime_state(case) -> list[int]:
    raw = [int(value) for value in case["rounds"][0]["in"]]
    return normalize_input_reference(raw)[WORLD_WORDS:]


def header_indices(state: list[int]) -> list[int]:
    out = []
    index = 0
    while state[index] != SETUP_END:
        out.append(index)
        index += 10
        while state[index] != ROOM_END:
            index += 1
            while state[index] != PIPE_MASK:
                index += 2
            index += 2
            assert state[index] == PIPE_VALUES
            index += 2 + state[index + 1]
            assert state[index] == PIPE_END
            index += 1
        index += 1
    assert index + 1 == len(state)
    return out


def on_left_wall(state: list[int], header: int) -> None:
    row = state[header + 6] // 16
    state[header + 6] = row * 16 + state[header + 1] % 16


def directed_states() -> list[list[int]]:
    base = next(
        runtime_state(case)
        for case in CASES
        if len(header_indices(runtime_state(case))) > 1
    )
    headers = header_indices(base)

    all_halted = list(base)
    for header in headers:
        all_halted[header + 5] |= 4

    live_wall = list(base)
    on_left_wall(live_wall, headers[0])

    halted_wall_with_live_peer = list(base)
    on_left_wall(halted_wall_with_live_peer, headers[0])
    halted_wall_with_live_peer[headers[0] + 5] |= 4

    return [all_halted, live_wall, halted_wall_with_live_peer]


class Script:
    def __init__(self, states: list[list[int]]):
        self.input = [token for state in states for token in state]
        self.expected = [roundstatus_reference(state) for state in states]
        self.output: list[int] = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text() -> str:
    return build_roundstatus_rig()


def test_reference_semantics_on_directed_states():
    all_halted, live_wall, halted_wall_with_live_peer = directed_states()
    assert roundstatus_reference(all_halted) == 0
    assert 2 in room_statuses_reference(live_wall)
    assert roundstatus_reference(live_wall) == 0
    assert room_statuses_reference(halted_wall_with_live_peer)[0] == 0
    assert roundstatus_reference(halted_wall_with_live_peer) == 1


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_reference_matches_room_model_across_ticks(case):
    state = runtime_state(case)
    world = normalize_input_reference(
        [int(value) for value in case["rounds"][0]["in"]]
    )[:WORLD_WORDS]
    for _ in range(4):
        statuses = room_statuses_reference(state)
        assert roundstatus_reference(state) == int(1 in statuses and 2 not in statuses)
        state = fulltick_reference([*world, *state])


def test_generator_is_deterministic_and_server_safe(text):
    assert build_roundstatus_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


def test_physical_predicate_for_public_and_directed_states(text):
    states = [*(runtime_state(case) for case in CASES), *directed_states()]
    script = Script(states)
    result = Machine.parse(text).run(max_ticks=5_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected


def test_physical_prefix_is_skipped_once_then_runtime_streams_continue():
    normalized = normalize_input_reference(
        [int(value) for value in CASES[0]["rounds"][0]["in"]]
    )
    world = normalized[:WORLD_WORDS]
    states = [normalized[WORLD_WORDS:]]
    for _ in range(2):
        states.append(fulltick_reference([*world, *states[-1]]))
    script = Script(states)
    script.input[:0] = world
    text = build_roundstatus_rig(prefix_world=True)
    result = Machine.parse(text).run(max_ticks=5_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected
