"""Regression and behavior gates for the solver-guided 26-square Brackets candidate."""

from __future__ import annotations

import hashlib
import itertools
import json
import random
from collections import Counter
from pathlib import Path

from littleman.alexey_pipecheck import check as check_pipe_lengths
from littleman.gpt_brackets_26 import build_gpt_brackets_26
from littleman.judge import judge_case, judge_problem
from littleman.server_compat import validate_layout
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "submissions" / "brackets" / "gpt_brackets_12.man"
BASELINE = ROOT / "submissions" / "brackets" / "brackets_11.man"
PROBLEM = json.loads((ROOT / "data" / "small" / "problems" / "brackets.json").read_text())
EXPECTED_SHA256 = "8cc306772304f39e21f6b140586844419b55103cec575834228dc9350bc2c4a5"
EXPECTED_TICKS = [248, 60, 108, 72, 150, 384, 140, 140, 2086]
BRACKETS = "()[]{}"
MATCH = {"(": ")", "[": "]", "{": "}"}


class _Probe:
    __slots__ = ("r", "c", "room")

    def __init__(self, row, column, room):
        self.r = row
        self.c = column
        self.room = room


def _box(text: str) -> tuple[int, int]:
    occupied = [
        (row, column)
        for row, line in enumerate(text.splitlines())
        for column, char in enumerate(line)
        if char != " "
    ]
    rows = [row for row, _ in occupied]
    columns = [column for _, column in occupied]
    return max(columns) - min(columns) + 1, max(rows) - min(rows) + 1


def _role_counts(text: str) -> Counter:
    machine = Machine.parse(text)
    pipe_index = {id(pipe): index for index, pipe in enumerate(machine.pipes)}
    roles = Counter()
    for room_index, room in enumerate(machine.rooms):
        for row in range(room.top + 1, room.bottom):
            for column in range(room.left + 1, room.right):
                char = machine.grid[row][column]
                if char not in "srq":
                    continue
                probe = _Probe(row, column, room)
                pipe = (
                    machine._nearest_outgoing(probe)
                    if char == "s"
                    else machine._nearest_incoming(probe)
                )
                roles[(room_index, char, pipe_index[id(pipe)])] += 1
    return roles


def _oracle(text: str) -> int:
    stack = []
    for position, char in enumerate(text, 1):
        if char in MATCH:
            stack.append(char)
        elif not stack or MATCH[stack[-1]] != char:
            return position
        else:
            stack.pop()
    return 0 if not stack else len(text) + 1


def _round(text: str) -> list[dict]:
    return [
        {
            "in": [len(text), *(ord(char) for char in text)],
            "out": [_oracle(text)],
        }
    ]


def test_generator_artifact_parity_and_hash():
    generated = build_gpt_brackets_26()
    assert generated == ARTIFACT.read_text()
    assert hashlib.sha256(generated.encode()).hexdigest() == EXPECTED_SHA256
    assert _box(generated) == (26, 26)


def test_structure_layout_and_pipe_roles():
    candidate = ARTIFACT.read_text()
    machine = Machine.parse(candidate)
    assert (len(machine.rooms), len(machine.pipes), len(machine.men)) == (5, 6, 3)
    assert [len(pipe.cells) for pipe in machine.pipes] == [2, 2, 2, 13, 47, 2]
    check_pipe_lengths(candidate)
    validate_layout(candidate)
    assert _role_counts(candidate) == _role_counts(BASELINE.read_text())


def test_exact_public_suite_and_score():
    report = judge_problem(ARTIFACT.read_text(), PROBLEM)
    assert report.cases_passed == report.cases_total == 9
    assert report.footprint == 676
    assert report.case_ticks == EXPECTED_TICKS
    assert report.score == 254476.44444444444


def test_exhaustive_short_strings():
    candidate = ARTIFACT.read_text()
    for length in range(5):
        for value in itertools.product(BRACKETS, repeat=length):
            result = judge_case(candidate, _round("".join(value)), max_ticks=100_000)
            assert result.passed, (value, result.reason)


def test_seeded_boundary_fuzz():
    candidate = ARTIFACT.read_text()
    rng = random.Random(20260727)
    corpus = {
        "",
        "(" * 32 + ")" * 32,
        "()" * 32,
        "[]" * 32,
        "{}" * 32,
        "([{" * 10 + "([" + "])}" * 10 + "])",
    }
    for position in range(1, 65):
        prefix = "()" * ((position - 1) // 2)
        if len(prefix) < position - 1:
            prefix += "("
        corpus.add((prefix + "]")[:64])
    for _ in range(500):
        length = rng.randrange(65)
        chars = []
        open_count = 0
        for _ in range(length):
            choices = ")]}" if open_count >= 32 else BRACKETS
            char = rng.choice(choices)
            chars.append(char)
            if char in MATCH:
                open_count += 1
            elif open_count:
                open_count -= 1
        corpus.add("".join(chars))
    for value in sorted(corpus, key=lambda item: (len(item), item)):
        result = judge_case(candidate, _round(value), max_ticks=300_000)
        assert result.passed, (value, _oracle(value), result.reason)
