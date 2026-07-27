"""Regression and behavior gates for the solver-guided 25-square Brackets candidate."""

from __future__ import annotations

import hashlib
import itertools
import json
import random
from collections import Counter
from pathlib import Path

from littleman.alexey_pipecheck import check as check_pipe_lengths
from littleman.gpt_brackets_25 import build_gpt_brackets_14
from littleman.judge import judge_case, judge_problem
from littleman.server_compat import validate_layout
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "submissions" / "brackets" / "gpt_brackets_14.man"
BASELINE = ROOT / "submissions" / "brackets" / "brackets_11.man"
PROBLEM = json.loads((ROOT / "data" / "small" / "problems" / "brackets.json").read_text())
EXPECTED_SHA256 = "9aa12829131b7bd9c4771b4bbfd49eec9fe83374a01fee91227d58ca142b0875"
EXPECTED_TICKS = [249, 61, 109, 73, 146, 380, 136, 136, 2083]
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


def _topology_role_counts(text: str) -> Counter:
    machine = Machine.parse(text)
    room_index = {id(room): index for index, room in enumerate(machine.rooms)}
    topology = {
        id(pipe): (room_index[id(pipe.source)], room_index[id(pipe.dest)])
        for pipe in machine.pipes
    }
    roles = Counter()
    for room_number, room in enumerate(machine.rooms):
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
                roles[(room_number, char, topology[id(pipe)])] += 1
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
    return [{"in": [len(text), *(ord(char) for char in text)], "out": [_oracle(text)]}]


def test_generator_artifact_hash_and_box():
    candidate = ARTIFACT.read_text()
    assert build_gpt_brackets_14() == candidate
    assert hashlib.sha256(candidate.encode()).hexdigest() == EXPECTED_SHA256
    assert _box(candidate) == (25, 25)


def test_structure_layout_and_logical_roles():
    candidate = ARTIFACT.read_text()
    machine = Machine.parse(candidate)
    assert (len(machine.rooms), len(machine.pipes), len(machine.men)) == (5, 6, 3)
    assert [len(pipe.cells) for pipe in machine.pipes] == [2, 2, 2, 42, 13, 2]
    check_pipe_lengths(candidate)
    validate_layout(candidate)
    assert _topology_role_counts(candidate) == _topology_role_counts(BASELINE.read_text())

    close_room = machine.rooms[2]
    open_room = machine.rooms[3]
    assert (close_room.right - close_room.left + 1) == 23
    assert (open_room.bottom - open_room.top + 1) == 9


def test_exact_public_suite_and_score():
    report = judge_problem(ARTIFACT.read_text(), PROBLEM)
    assert report.cases_passed == report.cases_total == 9
    assert report.footprint == 625
    assert report.case_ticks == EXPECTED_TICKS
    assert report.score == 234236.1111111111


def test_exhaustive_strings_through_length_five():
    candidate = ARTIFACT.read_text()
    for length in range(6):
        for value in itertools.product(BRACKETS, repeat=length):
            result = judge_case(candidate, _round("".join(value)), max_ticks=100_000)
            assert result.passed, (value, result.reason)


def test_seeded_boundary_fuzz():
    candidate = ARTIFACT.read_text()
    rng = random.Random(2026072704)
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
