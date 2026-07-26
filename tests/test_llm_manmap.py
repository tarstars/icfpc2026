"""Physical parity for the fetched-op man-state map stage."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm_fetchjoin import fetchjoin_reference
from littleman.llm_fuzz import llm_corpus
from littleman.llm_manmap import build_manmap_rig, manmap_reference
from littleman.llm_packraw import pack_reference
from littleman.llm_perimeter import perimeter_reference
from littleman.llm_pipestarts import pipestarts_reference
from littleman.llm_pipetrace import pipetrace_reference
from littleman.llm_roomfind import roomfind_reference
from littleman.llm_scan import scan_reference
from littleman.llm_statebuild import statebuild_reference
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/small/problems/little-little-man.json").read_text())[
    "publicTestData"
]
FUZZ = llm_corpus(20260726, 20)


def fetched_stream(case):
    source = [int(value) for value in case["rounds"][0]["in"]]
    stream = pack_reference(scan_reference(source))
    stream = roomfind_reference(stream)
    stream = perimeter_reference(stream)
    stream = pipestarts_reference(stream)
    stream = pipetrace_reference(stream)
    return fetchjoin_reference(statebuild_reference(stream))


class Script:
    def __init__(self, stream):
        self.input = list(stream)
        self.expected = manmap_reference(stream)
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_manmap_rig()


def test_generator_is_deterministic_and_server_safe(text):
    assert build_manmap_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


@pytest.mark.parametrize("case", [*CASES, *FUZZ[:10]], ids=lambda case: case["name"])
def test_physical_state_cycles(text, case):
    stream = fetched_stream(case)
    script = Script(stream)
    result = Machine.parse(text).run(max_ticks=2_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected
