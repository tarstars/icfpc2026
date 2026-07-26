"""Reference and physical gates for the rich-stream initial-frame stage."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm_geometry_assemble import build_geometry_pipeline
from littleman.llm_initframe import FRAME_END, build_initframe_rig, initframe_reference
from littleman.llm_packraw import pack_reference
from littleman.llm_perimeter import perimeter_reference
from littleman.llm_pipestarts import pipestarts_reference
from littleman.llm_pipetrace import pipetrace_reference
from littleman.llm_roomfind import roomfind_reference
from littleman.llm_scan import scan_reference
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/small/problems/little-little-man.json").read_text())[
    "publicTestData"
]


def rich_stream(case):
    source = [int(value) for value in case["rounds"][0]["in"]]
    source.extend(int(round_["in"][0]) for round_ in case["rounds"][1:])
    stream = pack_reference(scan_reference(source))
    stream = roomfind_reference(stream)
    stream = perimeter_reference(stream)
    stream = pipestarts_reference(stream)
    return pipetrace_reference(stream)


def frame_from(deltas):
    pixels = [0] * 256
    for token in deltas:
        if token == FRAME_END:
            break
        addr, color = divmod(token, 16)
        pixels[addr] = color
    return [
        "".join(f"{pixels[row * 16 + col]:x}" for col in range(16)) for row in range(16)
    ]


class Script:
    def __init__(self, stream):
        self.input = list(stream)
        self.expected = initframe_reference(stream)
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if value == FRAME_END else None


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_reference_matches_initial_frame(case):
    deltas = initframe_reference(rich_stream(case))
    assert frame_from(deltas) == case["rounds"][0]["frames"][0]


@pytest.fixture(scope="module")
def text():
    return build_initframe_rig()


def test_generator_is_deterministic_and_server_safe(text):
    assert build_initframe_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


@pytest.mark.parametrize("index", range(len(CASES)))
def test_physical_public_cases(text, index):
    case = CASES[index]
    stream = rich_stream(case)
    script = Script(stream)
    result = Machine.parse(text).run(max_ticks=10_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected
    assert frame_from(script.output) == case["rounds"][0]["frames"][0]


def test_geometry_source_is_server_safe():
    text = build_geometry_pipeline()
    server_compat.validate_layout(text)
