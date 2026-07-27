"""Release gates for the solver-guided 24-square Brackets candidate."""

from __future__ import annotations

import hashlib
import itertools
import json
import random
from pathlib import Path

from littleman.alexey_pipecheck import check as check_pipe_lengths
from littleman.gpt_brackets_24 import build_gpt_brackets_17
from littleman.server_compat import judge_case, judge_problem, validate_layout
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "submissions" / "brackets" / "gpt_brackets_17.man"
PROBLEM = json.loads((ROOT / "data" / "small" / "problems" / "brackets.json").read_text())
SHA256 = "51a6219ee527d5607720a99a1401cba9d94de9579021d32f1a1ed79adbc72325"
TICKS = [242, 64, 100, 64, 144, 376, 132, 132, 2078]
BRACKETS = "()[]{}"
MATCH = {"(": ")", "[": "]", "{": "}"}


def _box(text: str) -> tuple[int, int]:
    occupied = [
        (row, column)
        for row, line in enumerate(text.splitlines())
        for column, char in enumerate(line)
        if char != " "
    ]
    return (
        max(column for _, column in occupied) - min(column for _, column in occupied) + 1,
        max(row for row, _ in occupied) - min(row for row, _ in occupied) + 1,
    )


def _oracle(text: str) -> int:
    stack: list[str] = []
    for position, char in enumerate(text, 1):
        if char in MATCH:
            stack.append(char)
        elif not stack or MATCH[stack[-1]] != char:
            return position
        else:
            stack.pop()
    return 0 if not stack else len(text) + 1


def _round(text: str) -> list[dict]:
    return [{"in": [len(text), *(ord(char) for char in text)], "out": [_oracle(text)]}]


def test_artifact_structure_hash_and_public_score():
    candidate = ARTIFACT.read_text()
    assert build_gpt_brackets_17() == candidate
    assert hashlib.sha256(candidate.encode()).hexdigest() == SHA256
    assert _box(candidate) == (24, 24)
    machine = Machine.parse(candidate)
    assert (len(machine.rooms), len(machine.pipes), len(machine.men)) == (5, 6, 3)
    assert [len(pipe.cells) for pipe in machine.pipes] == [2, 2, 2, 5, 39, 3]
    check_pipe_lengths(candidate)
    validate_layout(candidate)
    report = judge_problem(candidate, PROBLEM)
    assert report.cases_passed == report.cases_total == 9
    assert report.footprint == 576
    assert report.case_ticks == TICKS
    assert report.score == 213248.0


def test_exhaustive_strings_through_length_five():
    candidate = ARTIFACT.read_text()
    for length in range(6):
        for value in itertools.product(BRACKETS, repeat=length):
            text = "".join(value)
            result = judge_case(candidate, _round(text), max_ticks=100_000)
            assert result.passed, (text, _oracle(text), result.reason)


def test_seeded_random_length_64():
    candidate = ARTIFACT.read_text()
    rng = random.Random(2026072707)
    for index in range(1_000):
        text = "".join(rng.choice(BRACKETS) for _ in range(rng.randrange(65)))
        result = judge_case(candidate, _round(text), max_ticks=300_000)
        assert result.passed, (index, text, _oracle(text), result.reason)
