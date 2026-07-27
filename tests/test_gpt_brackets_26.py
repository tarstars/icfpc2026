"""Regression and behavior gates for solver-guided 26-square Brackets candidates."""

from __future__ import annotations

import hashlib
import itertools
import json
import random
from collections import Counter
from pathlib import Path

from littleman.alexey_pipecheck import check as check_pipe_lengths
from littleman.gpt_brackets_26 import (
    build_gpt_brackets_12,
    build_gpt_brackets_13,
    build_gpt_brackets_26,
)
from littleman.judge import judge_case, judge_problem
from littleman.server_compat import validate_layout
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_12 = ROOT / "submissions" / "brackets" / "gpt_brackets_12.man"
ARTIFACT_13 = ROOT / "submissions" / "brackets" / "gpt_brackets_13.man"
BASELINE = ROOT / "submissions" / "brackets" / "brackets_11.man"
PROBLEM = json.loads((ROOT / "data" / "small" / "problems" / "brackets.json").read_text())
SHA_12 = "8cc306772304f39e21f6b140586844419b55103cec575834228dc9350bc2c4a5"
SHA_13 = "c4f5449b830f72f5529e82aa7034d580956aa83baffd162e4a36ebb6219e4eed"
TICKS_13 = [248, 60, 108, 72, 147, 381, 137, 137, 2083]
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
    for room_index_value, room in enumerate(machine.rooms):
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
                roles[(room_index_value, char, topology[id(pipe)])] += 1
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


def test_generators_artifacts_and_hashes():
    candidate_12 = ARTIFACT_12.read_text()
    candidate_13 = ARTIFACT_13.read_text()
    assert build_gpt_brackets_12() == candidate_12
    assert build_gpt_brackets_26() == candidate_12
    assert build_gpt_brackets_13() == candidate_13
    assert hashlib.sha256(candidate_12.encode()).hexdigest() == SHA_12
    assert hashlib.sha256(candidate_13.encode()).hexdigest() == SHA_13
    assert _box(candidate_12) == _box(candidate_13) == (26, 26)


def test_structure_layout_roles_and_endpoint_floor():
    candidate = ARTIFACT_13.read_text()
    machine = Machine.parse(candidate)
    assert (len(machine.rooms), len(machine.pipes), len(machine.men)) == (5, 6, 3)
    assert [len(pipe.cells) for pipe in machine.pipes] == [2, 2, 2, 44, 13, 2]
    check_pipe_lengths(candidate)
    validate_layout(candidate)
    assert _topology_role_counts(candidate) == _topology_role_counts(BASELINE.read_text())

    open_room = machine.rooms[3]
    long_pipe = next(
        pipe for pipe in machine.pipes
        if pipe.source is open_room and pipe.dest is machine.rooms[0]
    )
    assert long_pipe.cells[0] == (open_room.top + 1, open_room.right + 1)
    assert len(long_pipe.cells) == 44


def test_exact_public_suite_and_score():
    report = judge_problem(ARTIFACT_13.read_text(), PROBLEM)
    assert report.cases_passed == report.cases_total == 9
    assert report.footprint == 676
    assert report.case_ticks == TICKS_13
    assert report.score == 253349.77777777778


def test_exhaustive_strings_through_length_five():
    candidate = ARTIFACT_13.read_text()
    for length in range(6):
        for value in itertools.product(BRACKETS, repeat=length):
            result = judge_case(candidate, _round("".join(value)), max_ticks=100_000)
            assert result.passed, (value, result.reason)


def test_seeded_boundary_fuzz():
    candidate = ARTIFACT_13.read_text()
    rng = random.Random(2026072703)
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
