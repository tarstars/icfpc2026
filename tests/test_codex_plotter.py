"""End-to-end and protocol tests for the generated Plotter machine."""

from __future__ import annotations

import json
import random
from itertools import pairwise
from pathlib import Path

import pytest

from littleman.canvas import Canvas
from littleman.codex_plotter import (
    BASELINE_LAYOUT,
    COMPACT_LAYOUT,
    _compile_streams,
    _vertical_pipe,
    bresenham_addresses,
    build_plotter,
    build_plotter_compact,
    setup_constants,
)
from littleman.judge import judge_case, judge_problem

REPO = Path(__file__).resolve().parent.parent
PROBLEM = json.loads(
    (REPO / "data" / "small" / "problems" / "plotter.json").read_text()
)
SUBMISSIONS = REPO / "submissions" / "plotter"


def _setup_pipeline_harness() -> str:
    rooms = _compile_streams()
    canvas = Canvas()
    left = 20
    top = 7
    io_x = left + rooms[0].zones["io"]
    canvas.put(0, io_x - 1, ["+-+", "|I|", "+-+"])

    placed = []
    for room in rooms:
        canvas.put(top, left, room.rows)
        placed.append((top, room))
        top += room.height + 12

    canvas.pipe([(3, io_x), (placed[0][0] - 1, io_x)])
    for (source_top, source), (destination_top, destination) in pairwise(placed):
        _vertical_pipe(
            canvas,
            source_top + source.height + 1,
            left + source.zones["io"],
            destination_top,
            left + destination.zones["io"],
        )

    last_top, last = placed[-1]
    canvas.put(top, io_x - 1, ["+-+", "|O|", "+-+"])
    _vertical_pipe(
        canvas,
        last_top + last.height + 1,
        left + last.zones["io"],
        top,
        io_x,
    )
    return canvas.render()


def _frame_for_segment(segment: tuple[int, int, int, int]) -> list[str]:
    frame = [["0"] * 32 for _ in range(24)]
    for address in bresenham_addresses(*segment):
        frame[address // 32][address % 32] = "f"
    return ["".join(row) for row in frame]


def test_setup_pipeline_emits_exact_constants():
    segments = [
        (0, 0, 31, 23),
        (9, 5, 9, 5),
        (8, 4, 0, 0),
        (15, 11, 3, 22),
    ]
    inputs = [value for segment in segments for value in segment]
    expected = [value for segment in segments for value in setup_constants(*segment)]
    result = judge_case(
        _setup_pipeline_harness(),
        [{"in": inputs, "out": expected}],
        max_ticks=200_000,
    )
    assert result.passed, result


def test_plotter_passes_public_cases():
    report = judge_problem(build_plotter(), PROBLEM)
    assert report.cases_passed == report.cases_total == 6, report.case_results


def test_checked_in_candidates_match_their_generators():
    assert (SUBMISSIONS / "plotter_00.man").read_text() == build_plotter()
    assert (SUBMISSIONS / "plotter_01.man").read_text() == build_plotter_compact()


def test_compact_plotter_passes_public_cases():
    report = judge_problem(build_plotter_compact(), PROBLEM)
    assert report.cases_passed == report.cases_total == 6, report.case_results


@pytest.mark.parametrize("layout", [BASELINE_LAYOUT, COMPACT_LAYOUT])
def test_plotter_matches_reference_for_twenty_deterministic_segments(layout):
    rng = random.Random(20260724)
    segments = [
        (0, 0, 0, 0),
        (0, 0, 31, 23),
        (31, 23, 0, 0),
        (0, 23, 31, 0),
        (31, 0, 0, 23),
        (15, 11, 15, 23),
        (15, 11, 31, 11),
        (15, 11, 0, 11),
    ]
    while len(segments) < 20:
        segments.append(
            (
                rng.randrange(32),
                rng.randrange(24),
                rng.randrange(32),
                rng.randrange(24),
            )
        )
    rounds = [
        {"in": list(segment), "frames": [_frame_for_segment(segment)]}
        for segment in segments
    ]
    result = judge_case(build_plotter(layout), rounds, max_ticks=5_000_000)
    assert result.passed, result
