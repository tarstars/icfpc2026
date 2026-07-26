"""Physical gates for indexed decision metadata reordering."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm_components import CLASS_RECV, CLASS_SEND
from littleman.llm_decisionprep import (
    build_decisionprep_rig,
    decisionprep_reference,
)
from littleman.llm_fetchjoin import fetchjoin_reference
from littleman.llm_fuzz import llm_corpus
from littleman.llm_indexcopy import indexcopy_reference
from littleman.llm_indexdecision import indexdecision_reference
from littleman.llm_maskmap import maskmap_reference
from littleman.llm_packraw import pack_reference
from littleman.llm_perimeter import perimeter_reference
from littleman.llm_pipestarts import pipestarts_reference
from littleman.llm_pipetrace import pipetrace_dest_reference
from littleman.llm_roomfind import roomfind_reference
from littleman.llm_scan import scan_reference
from littleman.llm_statebuild import statebuild_reference
from littleman.llm_stateindex import stateindex_reference
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/small/problems/little-little-man.json").read_text())[
    "publicTestData"
]
FUZZ = llm_corpus(20260726, 20)


def indexed_state(case):
    source = [int(value) for value in case["rounds"][0]["in"]]
    stream = pack_reference(scan_reference(source))
    stream = roomfind_reference(stream)
    stream = perimeter_reference(stream)
    stream = pipestarts_reference(stream)
    stream = pipetrace_dest_reference(stream)
    stream = statebuild_reference(stream)
    world, state = stream[:64], stream[64:]
    state = fetchjoin_reference([*world, *maskmap_reference(state)])
    return stateindex_reference(state)


def with_active_record(tokens, room_no, cls):
    result = list(tokens)
    result[room_no * 12 + 10] = cls * 16
    return result


class Script:
    def __init__(self, requests):
        self.input = [item for request in requests for item in request]
        self.expected = [
            item for request in requests for item in decisionprep_reference(request)
        ]
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_decisionprep_rig()


def test_generator_is_deterministic_and_server_safe(text):
    assert build_decisionprep_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


def test_physical_inactive_send_and_receive(text):
    states = [indexed_state(case) for case in [*CASES, *FUZZ]]
    piped = next(state for state in states if -3600 in state)
    states.extend(
        (
            with_active_record(piped, 0, CLASS_SEND),
            with_active_record(piped, 0, CLASS_RECV),
        )
    )
    requests = [
        indexdecision_reference(indexcopy_reference(state), 0) for state in states
    ]
    script = Script(requests)
    result = Machine.parse(text).run(max_ticks=100_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected
