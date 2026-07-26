"""Component gates for the Plotter combined-error racetrack prototype."""

from __future__ import annotations

import hashlib
import json
import pathlib
import random

from littleman.codex_plotter import bresenham_addresses, setup_constants
from littleman.judge import footprint, judge_case, judge_problem
from littleman.plotter_racetrack import (
    build_combined_error_harness,
    build_fused_plotter_harness,
    build_plotter_fused_candidate,
)
from littleman.server_compat import validate_layout
from littleman.sim import Machine

REPO = pathlib.Path(__file__).resolve().parent.parent
ARTIFACT = REPO / "submissions" / "plotter" / "plotter_08.man"
PROBLEM = json.loads(
    (REPO / "data" / "small" / "problems" / "plotter.json").read_text()
)
EXPECTED_SHA256 = "1614d73921d512f321cb1a1a10660e75258c1ae0346f2b77bd51207be3e5c3dd"
EXPECTED_TICKS = [23_091, 53_753, 1_173, 32_568, 77_959, 78_896]


def _expected_control(segment: tuple[int, int, int, int]) -> list[int]:
    x0, y0, x1, y1 = segment
    dx = abs(x1 - x0)
    # Match the established setup stream.  The equal-coordinate sign is
    # arbitrary because that axis is never stepped.
    sx = 1 if x0 <= x1 else -1
    dy = -abs(y1 - y0)
    sy_width = 32 if y0 <= y1 else -32
    error = dx + dy
    out = [sx, sy_width, 32 * y0 + x0]
    while x0 != x1 or y0 != y1:
        doubled = 2 * error
        c1 = doubled >= dy
        c2 = doubled <= dx
        out.append(int(c1) + 2 * int(c2))
        if c1:
            error += dy
            x0 += sx
        if c2:
            error += dx
            y0 += 1 if sy_width > 0 else -1
    out.append(-1)
    return out


def _frame(segment: tuple[int, int, int, int]) -> list[str]:
    frame = [["0"] * 32 for _ in range(24)]
    for address in bresenham_addresses(*segment):
        frame[address // 32][address % 32] = "f"
    return ["".join(row) for row in frame]


def test_combined_error_component_matches_bresenham_control_stream():
    rng = random.Random(20260727)
    segments = [
        (0, 0, 0, 0),
        (0, 0, 31, 23),
        (31, 23, 0, 0),
        (0, 23, 31, 0),
        (31, 0, 0, 23),
        (15, 11, 15, 23),
        (15, 11, 31, 11),
    ]
    while len(segments) < 64:
        segments.append(
            (
                rng.randrange(32),
                rng.randrange(24),
                rng.randrange(32),
                rng.randrange(24),
            )
        )
    rounds = [
        {
            "in": setup_constants(*segment),
            "out": _expected_control(segment),
        }
        for segment in segments
    ]
    result = judge_case(
        build_combined_error_harness(),
        rounds,
        max_ticks=5_000_000,
    )
    assert result.passed, result


def test_combined_error_component_is_server_compatible():
    assert validate_layout(build_combined_error_harness()) is None


def test_fused_worker_emits_exact_address_stream():
    rng = random.Random(20260728)
    segments = [
        (0, 0, 0, 0),
        (0, 0, 31, 23),
        (31, 23, 0, 0),
        (0, 23, 31, 0),
        (31, 0, 0, 23),
        (15, 11, 15, 23),
        (15, 11, 31, 11),
    ]
    while len(segments) < 64:
        segments.append(
            (
                rng.randrange(32),
                rng.randrange(24),
                rng.randrange(32),
                rng.randrange(24),
            )
        )
    rounds = [
        {
            "in": setup_constants(*segment),
            "out": bresenham_addresses(*segment) + [-1],
        }
        for segment in segments
    ]
    result = judge_case(
        build_fused_plotter_harness(),
        rounds,
        max_ticks=5_000_000,
    )
    assert result.passed, result
    assert validate_layout(build_fused_plotter_harness()) is None


def test_full_fused_candidate_is_frozen_and_strict():
    artifact = ARTIFACT.read_text()
    assert build_plotter_fused_candidate() == artifact
    assert hashlib.sha256(artifact.encode()).hexdigest() == EXPECTED_SHA256
    assert validate_layout(artifact) is None
    assert footprint(artifact) == 16_900

    machine = Machine.parse(artifact)
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
        49,
        56,
        57,
        106,
        134,
        220,
    ]


def test_full_fused_candidate_public_ticks():
    result = judge_problem(ARTIFACT.read_text(), PROBLEM, max_ticks=2_000_000)
    assert result.cases_passed == result.cases_total == 6
    assert [case.ticks for case in result.case_results] == EXPECTED_TICKS
    assert result.score == 753_289_333.3333334


def test_full_fused_candidate_multiround_frame_oracle():
    rng = random.Random(20260729)
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
    while len(segments) < 40:
        segments.append(
            (
                rng.randrange(32),
                rng.randrange(24),
                rng.randrange(32),
                rng.randrange(24),
            )
        )
    rounds = [
        {"in": list(segment), "frames": [_frame(segment)]} for segment in segments
    ]
    result = judge_case(ARTIFACT.read_text(), rounds, max_ticks=4_000_000)
    assert result.passed, result
