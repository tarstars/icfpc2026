#!/usr/bin/env python3
"""Repository-native replay for the GPT 24x25 Brackets candidate."""

from __future__ import annotations

import itertools
import json
import random
import unittest
from pathlib import Path

from littleman.alexey_pipecheck import check as check_pipe_lengths
from littleman.gpt_brackets_25 import build_gpt_brackets_15
from littleman.server_compat import judge_case, judge_problem, validate_layout
from littleman.sim import Machine

from build_gpt_brackets_16 import (
    ARTIFACT,
    EXPECTED_PIPE_LENGTHS,
    SHA256,
    build_gpt_brackets_16,
)

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = json.loads((ROOT / "data/small/problems/brackets.json").read_text())

OPEN_TO_CLOSE = {40: 41, 91: 93, 123: 125}
CLOSE_TO_OPEN = {value: key for key, value in OPEN_TO_CLOSE.items()}
ALPHABET = tuple(OPEN_TO_CLOSE) + tuple(CLOSE_TO_OPEN)


def oracle(values: list[int]) -> int:
    stack: list[int] = []
    for position, value in enumerate(values, 1):
        if value in OPEN_TO_CLOSE:
            stack.append(value)
        elif not stack or stack[-1] != CLOSE_TO_OPEN[value]:
            return position
        else:
            stack.pop()
    return 0 if not stack else len(values) + 1


def valid_depth(values: list[int]) -> bool:
    stack: list[int] = []
    maximum = 0
    for value in values:
        if value in OPEN_TO_CLOSE:
            stack.append(value)
            maximum = max(maximum, len(stack))
        elif stack and stack[-1] == CLOSE_TO_OPEN[value]:
            stack.pop()
        elif value in CLOSE_TO_OPEN:
            stack.clear()
    return maximum <= 32


def round_for(values: list[int]) -> list[dict[str, list[str]]]:
    return [{
        "in": [str(len(values)), *map(str, values)],
        "out": [str(oracle(values))],
    }]


class GptBrackets16Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate = build_gpt_brackets_16()
        cls.baseline = build_gpt_brackets_15()

    def test_exact_artifact_and_static_gates(self) -> None:
        self.assertEqual(ARTIFACT.read_text(), self.candidate)
        import hashlib

        self.assertEqual(hashlib.sha256(self.candidate.encode()).hexdigest(), SHA256)
        rows = self.candidate.rstrip("\n").split("\n")
        self.assertEqual((max(map(len, rows)), len(rows)), (24, 25))
        machine = Machine.parse(self.candidate)
        self.assertEqual((len(machine.rooms), len(machine.men), len(machine.pipes)), (5, 3, 6))
        self.assertEqual([len(pipe.cells) for pipe in machine.pipes], EXPECTED_PIPE_LENGTHS)
        check_pipe_lengths(self.candidate)
        validate_layout(self.candidate)

    def test_public_ticks_and_score(self) -> None:
        baseline = judge_problem(self.baseline, PROBLEM)
        candidate = judge_problem(self.candidate, PROBLEM)
        self.assertEqual((baseline.cases_passed, baseline.cases_total), (9, 9))
        self.assertEqual((candidate.cases_passed, candidate.cases_total), (9, 9))
        self.assertEqual(baseline.case_ticks, [246, 58, 106, 70, 146, 380, 136, 136, 2082])
        self.assertEqual(candidate.case_ticks, [245, 57, 105, 69, 145, 379, 135, 135, 2081])
        self.assertEqual(candidate.footprint, 625)
        self.assertAlmostEqual(candidate.score, 232_708.3333333333)

    def test_exhaustive_strings_through_length_four(self) -> None:
        for length in range(5):
            for values_tuple in itertools.product(ALPHABET, repeat=length):
                values = list(values_tuple)
                with self.subTest(values=values):
                    result = judge_case(self.candidate, round_for(values))
                    self.assertTrue(result.passed, result.reason)

    def test_seeded_random_matches_oracle_and_beats_gpt15_by_one_tick(self) -> None:
        rng = random.Random(2026072706)
        checked = 0
        while checked < 512:
            values = [rng.choice(ALPHABET) for _ in range(rng.randrange(65))]
            if not valid_depth(values):
                continue
            rounds = round_for(values)
            baseline = judge_case(self.baseline, rounds)
            candidate = judge_case(self.candidate, rounds)
            self.assertTrue(baseline.passed, baseline.reason)
            self.assertTrue(candidate.passed, candidate.reason)
            self.assertEqual(candidate.ticks, baseline.ticks - 1)
            checked += 1


if __name__ == "__main__":
    unittest.main()
