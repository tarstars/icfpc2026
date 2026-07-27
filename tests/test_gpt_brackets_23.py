"""Release gates for the solver-guided 23-square Brackets candidate."""

from __future__ import annotations

import hashlib
import itertools
import json
import random
from pathlib import Path

from littleman.alexey_pipecheck import check as check_pipe_lengths
from littleman.gpt_brackets_23 import ROOMS, build_gpt_brackets_18
from littleman.server_compat import judge_case, judge_problem, validate_layout
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "submissions" / "brackets" / "gpt_brackets_18.man"
PROBLEM = json.loads((ROOT / "data" / "small" / "problems" / "brackets.json").read_text())
SHA256 = "50e85872d47e81c90f1205f0ae4c0341b62626630b1a1efb66552d357425320c"
TICKS = [256, 78, 114, 78, 158, 382, 140, 140, 2088]
BRACKETS = "()[]{}"
MATCH = {"(": ")", "[": "]", "{": "}"}
EXPECTED_TOPOLOGY = sorted(
    [
        ("classify", "close"),
        ("close", "classify"),
        ("close", "output"),
        ("open", "close"),
        ("open", "classify"),
        ("input", "open"),
    ]
)
EXPECTED_BINDINGS = {
    "classify": [
        ("s", ("classify", "close")),
        ("s", ("classify", "close")),
        ("r", ("open", "classify")),
        ("r", ("close", "classify")),
        ("s", ("classify", "close")),
        ("r", ("close", "classify")),
        ("s", ("classify", "close")),
        ("r", ("close", "classify")),
        ("s", ("classify", "close")),
        ("s", ("classify", "close")),
        ("r", ("close", "classify")),
    ],
    "close": [
        ("r", ("classify", "close")),
        ("s", ("close", "output")),
        ("r", ("open", "close")),
        ("r", ("classify", "close")),
        ("s", ("close", "classify")),
        ("r", ("classify", "close")),
        ("s", ("close", "classify")),
        ("r", ("classify", "close")),
        ("r", ("classify", "close")),
        ("r", ("classify", "close")),
        ("s", ("close", "output")),
        ("s", ("close", "classify")),
        ("r", ("classify", "close")),
        ("s", ("close", "classify")),
        ("r", ("classify", "close")),
        ("s", ("close", "output")),
    ],
    "open": [
        ("s", ("open", "close")),
        ("s", ("open", "classify")),
        ("q", ("input", "open")),
        ("r", ("input", "open")),
        ("r", ("input", "open")),
        ("s", ("open", "close")),
        ("s", ("open", "classify")),
        ("s", ("open", "close")),
        ("s", ("open", "classify")),
    ],
}


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


def _named_topology(text: str):
    machine = Machine.parse(text)
    by_origin = {(room.top, room.left): room for room in machine.rooms}
    semantic = {id(by_origin[origin]): name for name, origin in ROOMS.items()}
    topology = {
        id(pipe): (semantic[id(pipe.source)], semantic[id(pipe.dest)])
        for pipe in machine.pipes
    }
    return machine, by_origin, topology


def _binding_signature(text: str):
    machine, by_origin, topology = _named_topology(text)
    result = {}
    for name in ("classify", "close", "open"):
        room = by_origin[ROOMS[name]]
        rows = []
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
                rows.append((char, topology[id(pipe)]))
        result[name] = rows
    return result


def test_artifact_structure_hash_bindings_and_public_score():
    candidate = ARTIFACT.read_text()
    assert build_gpt_brackets_18() == candidate
    assert hashlib.sha256(candidate.encode()).hexdigest() == SHA256
    assert _box(candidate) == (23, 23)

    machine, _by_origin, topology = _named_topology(candidate)
    assert (len(machine.rooms), len(machine.pipes), len(machine.men)) == (5, 6, 3)
    assert [len(pipe.cells) for pipe in machine.pipes] == [4, 14, 2, 8, 4, 2]
    assert sorted(topology.values()) == EXPECTED_TOPOLOGY
    assert _binding_signature(candidate) == EXPECTED_BINDINGS
    check_pipe_lengths(candidate)
    validate_layout(candidate)

    report = judge_problem(candidate, PROBLEM)
    assert report.cases_passed == report.cases_total == 9
    assert report.footprint == 529
    assert report.case_ticks == TICKS
    assert report.score == 201842.88888888888


def test_exhaustive_strings_through_length_five():
    candidate = ARTIFACT.read_text()
    for length in range(6):
        for value in itertools.product(BRACKETS, repeat=length):
            text = "".join(value)
            result = judge_case(candidate, _round(text), max_ticks=100_000)
            assert result.passed, (text, _oracle(text), result.reason)


def test_seeded_random_length_64():
    candidate = ARTIFACT.read_text()
    rng = random.Random(2026072708)
    directed = [
        "",
        "(" * 32 + ")" * 32,
        "[" * 32 + "]" * 32,
        "{" * 32 + "}" * 32,
        "()" * 32,
        "[]" * 32,
        "{}" * 32,
    ]
    for text in directed:
        result = judge_case(candidate, _round(text), max_ticks=300_000)
        assert result.passed, (text, _oracle(text), result.reason)
    for index in range(1_000):
        text = "".join(rng.choice(BRACKETS) for _ in range(rng.randrange(65)))
        result = judge_case(candidate, _round(text), max_ticks=300_000)
        assert result.passed, (index, text, _oracle(text), result.reason)
