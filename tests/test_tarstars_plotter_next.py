"""Strict gates for the 125-square Tarstars Plotter successor."""

from __future__ import annotations

import hashlib
import json
import pathlib
import random

from littleman.codex_plotter import bresenham_addresses, setup_constants
from littleman.judge import footprint, judge_case, judge_problem
from littleman.server_compat import validate_layout
from littleman.sim import Machine
from littleman.tarstars_plotter_next import (
    build_reordered_fused_harness,
    build_tarstars_plotter_next,
)

REPO = pathlib.Path(__file__).resolve().parent.parent
ARTIFACT = REPO / "submissions" / "plotter" / "tarstars_plotter_09.man"
EXPECTED_SHA256 = "25a19f4cae8d40b73bf76afe2ef5dd51fba88d7df42005c58731cd33080f8a6a"
EXPECTED_TICKS = [22_996, 53_468, 1_078, 32_188, 77_579, 78_136]
PROBLEM = json.loads(
    (REPO / "data" / "small" / "problems" / "plotter.json").read_text()
)


def _frame(segment: tuple[int, int, int, int]) -> list[str]:
    frame = [["0"] * 32 for _ in range(24)]
    for address in bresenham_addresses(*segment):
        frame[address // 32][address % 32] = "f"
    return ["".join(row) for row in frame]


def _segments(seed: int, count: int) -> list[tuple[int, int, int, int]]:
    rng = random.Random(seed)
    segments = [
        (0, 0, 0, 0),
        (0, 0, 31, 23),
        (31, 23, 0, 0),
        (0, 23, 31, 0),
        (31, 0, 0, 23),
        (15, 11, 15, 23),
        (15, 11, 31, 11),
        (15, 11, 0, 11),
        (15, 11, 15, 0),
    ]
    while len(segments) < count:
        segments.append(
            (
                rng.randrange(32),
                rng.randrange(24),
                rng.randrange(32),
                rng.randrange(24),
            )
        )
    return segments


def test_reordered_worker_preserves_64_segment_protocol():
    rounds = [
        {
            "in": setup_constants(*segment),
            "out": bresenham_addresses(*segment) + [-1],
        }
        for segment in _segments(20260730, 64)
    ]
    candidate = build_reordered_fused_harness()
    result = judge_case(candidate, rounds, max_ticks=5_000_000)
    assert result.passed, result
    assert validate_layout(candidate) is None


def test_candidate_is_strict_125_square():
    candidate = build_tarstars_plotter_next()
    assert candidate == ARTIFACT.read_text()
    assert hashlib.sha256(candidate.encode()).hexdigest() == EXPECTED_SHA256
    assert validate_layout(candidate) is None
    assert footprint(candidate) == 15_625
    machine = Machine.parse(candidate)
    assert (len(machine.rooms), len(machine.pipes), len(machine.men)) == (12, 14, 10)
    assert sorted(len(pipe.cells) for pipe in machine.pipes) == [
        2,
        3,
        3,
        3,
        3,
        4,
        25,
        29,
        36,
        50,
        51,
        57,
        111,
        117,
    ]


def test_candidate_public_cases():
    result = judge_problem(
        build_tarstars_plotter_next(),
        PROBLEM,
        max_ticks=2_000_000,
    )
    assert result.cases_passed == result.cases_total == 6
    assert [case.ticks for case in result.case_results] == EXPECTED_TICKS
    assert result.score == 691_263_020.8333334


def test_candidate_40_round_frame_oracle():
    segments = _segments(20260731, 40)
    rounds = [
        {"in": list(segment), "frames": [_frame(segment)]} for segment in segments
    ]
    result = judge_case(
        build_tarstars_plotter_next(),
        rounds,
        max_ticks=4_000_000,
    )
    assert result.passed, result
