"""End-to-end gates for the complete raw-input physical LLM machine."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.judge import judge_case
from littleman.llm_machine import build_llm_machine, normalize_input_reference
from littleman.llm_roomfind import SETUP_END
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads(
    (ROOT / "data/small/problems/little-little-man.json").read_text()
)["publicTestData"]


@pytest.fixture(scope="module")
def text() -> str:
    return build_llm_machine()


def test_normalized_input_preserves_round_commands():
    case = CASES[1]
    raw = [int(value) for value in case["rounds"][0]["in"]]
    commands = [int(round_["in"][0]) for round_ in case["rounds"][1:]]
    stream = normalize_input_reference([*raw, *commands])
    end = stream.index(SETUP_END)
    assert stream[end + 1 :] == commands


def test_generator_is_deterministic_below_limit_and_server_safe(text):
    assert build_llm_machine() == text
    assert len(text.encode()) < 10_000_000
    assert len(text.splitlines()) == 25_207
    assert max(map(len, text.splitlines())) == 749
    machine = Machine.parse(text)
    assert len(machine.rooms) == 135
    assert len(machine.pipes) == 217
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


def test_raw_first_steps_passes_all_four_rounds(text):
    result = judge_case(text, CASES[0]["rounds"], max_ticks=35_000_000)
    assert result.passed, result.reason
