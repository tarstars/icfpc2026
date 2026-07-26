"""Physical parity for normalized-state indexing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.canvas import Canvas
from littleman.lllm_fetch import build_relay
from littleman.llm_fetchjoin import fetchjoin_reference
from littleman.llm_fuzz import llm_corpus
from littleman.llm_maskmap import maskmap_reference
from littleman.llm_packraw import pack_reference
from littleman.llm_perimeter import perimeter_reference
from littleman.llm_pipestarts import pipestarts_reference
from littleman.llm_pipetrace import pipetrace_dest_reference
from littleman.llm_roomfind import roomfind_reference
from littleman.llm_scan import scan_reference
from littleman.llm_statebuild import statebuild_reference
from littleman.llm_stateindex import (
    INDEX_END,
    INDEX_SPLIT,
    _build_fsm,
    build_stateindex_room,
    stateindex_reference,
)
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/small/problems/little-little-man.json").read_text())[
    "publicTestData"
]
FUZZ = llm_corpus(20260726, 20)


def fetched_state(case):
    source = [int(value) for value in case["rounds"][0]["in"]]
    stream = pack_reference(scan_reference(source))
    stream = roomfind_reference(stream)
    stream = perimeter_reference(stream)
    stream = pipestarts_reference(stream)
    stream = pipetrace_dest_reference(stream)
    stream = statebuild_reference(stream)
    world, state = stream[:64], stream[64:]
    return fetchjoin_reference([*world, *maskmap_reference(state)])


def build_rig() -> str:
    room = build_stateindex_room()
    block_rows = __import__("littleman.lllm_scan", fromlist=["_layout"])._layout(
        _build_fsm()
    )[1]
    left = 5
    right = left + len(room[0]) - 1
    relay_left = right + 5
    far = relay_left + 17
    buffer_bottom = len(room) + 190
    input_row = 45
    output_row = 55
    cv = Canvas()
    cv.put(0, left, room)
    cv.put(buffer_bottom - 20, relay_left, build_relay().render())
    cv.put(input_row - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(output_row - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(input_row, 3), (input_row, left - 1)])
    cv.pipe([(output_row, left - 1), (output_row, 3)])
    # Center the scratch endpoint across every right-zone send, including
    # the late sentinel; otherwise the late state can bind to display O.
    out_row = block_rows["count_store"]
    in_row = block_rows["drain_r"]
    relay_row = buffer_bottom - 19
    cv.pipe(
        [
            (out_row, right + 1),
            (out_row, far),
            (relay_row, far),
            (relay_row, relay_left + 6),
        ]
    )
    cv.pipe(
        [
            (relay_row, relay_left - 1),
            (relay_row, right + 3),
            (in_row, right + 3),
            (in_row, right + 1),
        ]
    )
    return cv.render()


class Script:
    def __init__(self, stream):
        self.input = list(stream)
        self.expected = stateindex_reference(stream)
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_rig()


def test_generator_is_deterministic_and_server_safe(text):
    assert build_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


@pytest.mark.parametrize("case", [*CASES, *FUZZ[:10]], ids=lambda case: case["name"])
def test_physical_state_index(text, case):
    stream = fetched_state(case)
    script = Script(stream)
    result = Machine.parse(text).run(max_ticks=5_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected


def test_index_stream_has_explicit_table_boundaries():
    result = stateindex_reference(fetched_state(CASES[0]))
    split = result.index(INDEX_SPLIT)
    assert result[split - 1] == -1000
    assert result[-1] == INDEX_END
