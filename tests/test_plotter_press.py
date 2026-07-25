"""Gates for the pressed Plotter (`plotter_05.man`).

The press is a pure placement change: same rooms, same ports, same pipe
lengths -- except one deliberately broken weld, EUPD -> ADDRESS.  Every test
here pins one of those claims against the live artifact `plotter_04.man`.
"""

from __future__ import annotations

import json
import pathlib
import random

import pytest

from littleman.judge import footprint, judge_case, judge_problem
from littleman.plotter_press import (
    BROKEN_WELD,
    bindings,
    build_pressed_plotter,
    port_margins,
    resolution_by_offset,
    room_texts,
)
from littleman.sim import Machine

REPO = pathlib.Path(__file__).resolve().parent.parent
LIVE = REPO / "submissions" / "plotter" / "plotter_04.man"
PRESSED = REPO / "submissions" / "plotter" / "plotter_05.man"
PROBLEM = json.loads((REPO / "data" / "small" / "problems" / "plotter.json").read_text())


@pytest.fixture(scope="module")
def pressed() -> str:
    return build_pressed_plotter()


@pytest.fixture(scope="module")
def live() -> str:
    return LIVE.read_text()


def test_generator_is_deterministic_and_matches_the_artifact(pressed):
    assert build_pressed_plotter() == pressed
    assert PRESSED.read_text() == pressed


def test_rooms_are_byte_identical(pressed, live):
    assert room_texts(pressed) == room_texts(live)


def test_every_pipe_keeps_its_ports_and_only_one_keeps_a_new_length(pressed, live):
    new, old = bindings(pressed), bindings(live)
    assert len(new) == len(old) == 18
    changed = [(a, b) for a, b in zip(new, old) if a != b]
    assert len(changed) == 1, changed
    (src, dst, length, head, tail), (osrc, odst, olength, ohead, otail) = changed[0]
    assert (src, dst, head, tail) == (osrc, odst, ohead, otail)
    assert (olength, length) == BROKEN_WELD


def test_display_path_lengths_are_untouched(pressed, live):
    def driver_lengths(text):
        machine = Machine.parse(text)
        return sorted(
            len(pipe.cells)
            for pipe in machine.pipes
            if pipe.dest.kind == "display" or pipe.source.kind == "display"
        )

    assert driver_lengths(pressed) == driver_lengths(live) == [3, 19, 56]


def test_every_instruction_binds_to_the_same_pipe_role(pressed, live):
    new, old = resolution_by_offset(pressed), resolution_by_offset(live)
    assert len(new) == 181
    assert new == old


def test_port_margins_are_unchanged_and_positive(pressed, live):
    new = port_margins(pressed)
    assert new == port_margins(live)
    assert all(m is None or m >= 2 for m in new.values()), new


def test_the_box_is_pressed(pressed):
    rows = pressed.rstrip("\n").split("\n")
    height, width = len(rows), max(len(row) for row in rows)
    assert (height, width) == (185, 175)
    assert max(height, width) < 326
    assert footprint(pressed) == 34_225 < footprint(LIVE.read_text())


def test_public_cases_pass(pressed):
    report = judge_problem(pressed, PROBLEM)
    assert report.cases_passed == report.cases_total == 6, report.case_results
    assert report.score < judge_problem(LIVE.read_text(), PROBLEM).score


def _frame_for_segment(segment: tuple[int, int, int, int]) -> list[str]:
    from littleman.codex_plotter import bresenham_addresses

    frame = [["0"] * 32 for _ in range(24)]
    for address in bresenham_addresses(*segment):
        frame[address // 32][address % 32] = "f"
    return ["".join(row) for row in frame]


def test_twenty_deterministic_segments_match_the_reference(pressed):
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
        segments.append((
            rng.randrange(32), rng.randrange(24),
            rng.randrange(32), rng.randrange(24),
        ))
    rounds = [
        {"in": list(segment), "frames": [_frame_for_segment(segment)]}
        for segment in segments
    ]
    result = judge_case(pressed, rounds, max_ticks=5_000_000)
    assert result.passed, result
