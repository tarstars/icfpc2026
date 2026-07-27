"""Regression gates for chatgpt_2's complete two-pump Sort experiment."""
from __future__ import annotations

import hashlib
import json
import math
import random
from pathlib import Path

from littleman.chatgpt2_sort_kring import build_chatgpt2_sort_00
from littleman.judge import footprint
from littleman.server_compat import judge_case, judge_problem, validate_layout
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "experiments/chatgpt_2-sort-kring/chatgpt2_sort_00.man"
PROBLEM = json.loads((ROOT / "data/small/problems/sort-numbers.json").read_text())
SHA256 = "8bc7495136458e5caf9bf8f46ded00df22c2d6de84558e879ba8967cbd83fdbe"
TICKS = [2195, 2132, 1895, 1391, 1980, 2828, 5639]


def test_exact_artifact_structure_and_public_result():
    text = ARTIFACT.read_text()
    assert build_chatgpt2_sort_00() == text
    assert hashlib.sha256(text.encode()).hexdigest() == SHA256
    machine = Machine.parse(text)
    assert (len(machine.rooms), len(machine.pipes), len(machine.men)) == (9, 12, 7)
    assert sorted(len(pipe.cells) for pipe in machine.pipes) == [
        12, 12, 12, 13, 14, 14, 69, 70, 74, 76, 93, 107
    ]
    validate_layout(text)
    assert min(len(pipe.cells) for pipe in machine.pipes) >= 2
    report = judge_problem(text, PROBLEM)
    assert report.cases_passed == report.cases_total == 7
    assert report.case_ticks == TICKS
    assert report.footprint == 23716
    assert report.score == 61187280.0
    assert footprint(text) == 23716


def test_seeded_multi_round_differential():
    text = ARTIFACT.read_text()
    rng = random.Random(2026072709)
    for index in range(100):
        rounds = []
        for _ in range(rng.randint(1, 4)):
            length = rng.randint(1, 16)
            values = [rng.randint(-1000, 1000) for _ in range(length)]
            rounds.append({"in": [length, *values], "out": sorted(values)})
        result = judge_case(text, rounds, max_ticks=200_000)
        assert result.passed, (index, rounds, result.reason)


def test_current_component_family_has_no_score_path():
    # Measured isolated pump completion ticks for m=1..8, including a minimal
    # two-cell input/output and the exact 12/14-cell relay ring.
    pump = {1: 84, 2: 134, 3: 196, 4: 270, 5: 356, 6: 454, 7: 564, 8: 686}
    lengths = [
        [3, 4, 5], [1, 5, 4], [4, 7], [6, 2], [5, 8],
        [1, 16, 2], [16, 3, 12, 16],
    ]
    pump_only_case_ticks = [
        sum(pump[(n + 1) // 2] for n in case) for case in lengths
    ]
    pump_only_average = sum(pump_only_case_ticks) / len(pump_only_case_ticks)
    assert pump_only_average == 691.7142857142857

    # Even after deleting the prefixer entirely, the current concrete room
    # family occupies 1,110 rectangle cells before adding any pipe cells:
    # splitter 27x20, two pumps 12x15, two relays 6x4, merger 18x8, two I/O 3x3.
    room_area_without_prefixer = 27 * 20 + 2 * 12 * 15 + 2 * 6 * 4 + 18 * 8 + 2 * 3 * 3
    assert room_area_without_prefixer == 1110
    minimum_square = math.ceil(math.sqrt(room_area_without_prefixer))
    assert minimum_square == 34
    lower_bound_score = minimum_square**2 * pump_only_average

    accepted_public_score = 18**2 * (sum([755, 617, 772, 544, 928, 2137, 5282]) / 7)
    assert accepted_public_score == 510762.8571428571
    assert lower_bound_score == 799621.7142857142
    assert lower_bound_score > accepted_public_score
