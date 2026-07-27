"""Regression and behavior gates for solver-guided 25-square Brackets candidates."""

from __future__ import annotations

import hashlib
import itertools
import json
import random
from collections import Counter
from pathlib import Path

from littleman.alexey_pipecheck import check as check_pipe_lengths
from littleman.gpt_brackets_25 import build_gpt_brackets_14, build_gpt_brackets_15
from littleman.judge import judge_case, judge_problem
from littleman.server_compat import validate_layout
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_14 = ROOT / "submissions" / "brackets" / "gpt_brackets_14.man"
ARTIFACT_15 = ROOT / "submissions" / "brackets" / "gpt_brackets_15.man"
BASELINE = ROOT / "submissions" / "brackets" / "brackets_11.man"
PROBLEM = json.loads((ROOT / "data" / "small" / "problems" / "brackets.json").read_text())
SHA_14 = "9aa12829131b7bd9c4771b4bbfd49eec9fe83374a01fee91227d58ca142b0875"
SHA_15 = "826553c4a58fd1ef83f81e8b05e9c3d54b575f2030d89c566cd5d9a99c09e605"
TICKS_15 = [246, 58, 106, 70, 146, 380, 136, 136, 2082]
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


def test_generators_artifacts_hashes_and_boxes():
    candidate_14 = ARTIFACT_14.read_text()
    candidate_15 = ARTIFACT_15.read_text()
    assert build_gpt_brackets_14() == candidate_14
    assert build_gpt_brackets_15() == candidate_15
    assert hashlib.sha256(candidate_14.encode()).hexdigest() == SHA_14
    assert hashlib.sha256(candidate_15.encode()).hexdigest() == SHA_15
    assert _box(candidate_14) == _box(candidate_15) == (25, 25)


def test_structure_layout_roles_and_state_route_floor():
    candidate = ARTIFACT_15.read_text()
    machine = Machine.parse(candidate)
    assert (len(machine.rooms), len(machine.pipes), len(machine.men)) == (5, 6, 3)
    assert [len(pipe.cells) for pipe in machine.pipes] == [2, 2, 2, 10, 42, 2]
    check_pipe_lengths(candidate)
    validate_layout(candidate)
    assert _topology_role_counts(candidate) == _topology_role_counts(BASELINE.read_text())

    open_room = machine.rooms[3]
    close_room = machine.rooms[2]
    state_pipe = next(
        pipe for pipe in machine.pipes
        if pipe.source is open_room and pipe.dest is close_room
    )
    assert state_pipe.cells[0] == (open_room.top + 1, open_room.left - 1)
    assert state_pipe.cells[-1] == (close_room.top + 2, close_room.left - 1)
    distance = sum(abs(a - b) for a, b in zip(state_pipe.cells[0], state_pipe.cells[-1]))
    assert len(state_pipe.cells) == distance + 1 == 10


def test_exact_public_suite_and_score():
    report = judge_problem(ARTIFACT_15.read_text(), PROBLEM)
    assert report.cases_passed == report.cases_total == 9
    assert report.footprint == 625
    assert report.case_ticks == TICKS_15
    assert report.score == 233333.3333333333


def test_exhaustive_strings_through_length_five():
    candidate = ARTIFACT_15.read_text()
    for length in range(6):
        for value in itertools.product(BRACKETS, repeat=length):
            result = judge_case(candidate, _round("".join(value)), max_ticks=100_000)
            assert result.passed, (value, result.reason)


def test_seeded_boundary_fuzz():
    candidate = ARTIFACT_15.read_text()
    rng = random.Random(2026072705)
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
