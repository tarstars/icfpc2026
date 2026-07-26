"""Persistent physical LLM state-to-display composition gates."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.judge import judge_case
from littleman.llm_fulltick import fulltick_reference
from littleman.llm_framerender import build_framerender_rig
from littleman.llm_packraw import pack_reference
from littleman.llm_perimeter import perimeter_reference
from littleman.llm_pipestarts import pipestarts_reference
from littleman.llm_pipetrace import pipetrace_dest_reference
from littleman.llm_roomfind import roomfind_reference
from littleman.llm_scan import scan_reference
from littleman.llm_statebuild import statebuild_reference

ROOT = Path(__file__).resolve().parents[1]
CASE = json.loads(
    (ROOT / "data/small/problems/little-little-man.json").read_text()
)["publicTestData"][0]


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
    return build_framerender_rig()


def test_generator_is_deterministic_compact_and_server_safe(text):
    assert build_framerender_rig() == text
    assert len(text.splitlines()) == 452
    assert max(map(len, text.splitlines())) == 394
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


def test_two_consecutive_states_render_exact_frames(text):
    initial = state_stream()
    next_state = fulltick_reference(initial)
    rounds = [
        {"in": initial, "frames": CASE["rounds"][0]["frames"]},
        {"in": next_state, "frames": CASE["rounds"][1]["frames"]},
    ]
    result = judge_case(text, rounds, max_ticks=12_000_000)
    assert result.passed, result.reason

