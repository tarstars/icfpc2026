"""Gates for the placement-only ``plotter_07`` successor."""

from __future__ import annotations

import hashlib
import json
import pathlib
import random

from littleman.codex_plotter import bresenham_addresses
from littleman.judge import footprint, judge_case, judge_problem
from littleman.plotter_press import (
    bindings,
    port_margins,
    resolution_by_offset,
    room_texts,
)
from littleman.plotter_route import SOURCE_SHA256, build_plotter_route
from littleman.server_compat import validate_layout
from littleman.sim import Machine

REPO = pathlib.Path(__file__).resolve().parent.parent
SOURCE = REPO / "submissions" / "plotter" / "plotter_06.man"
CANDIDATE = REPO / "submissions" / "plotter" / "plotter_07.man"
RESPONSE = REPO / "submissions" / "plotter" / "plotter_07-submit.json"
PROBLEM = json.loads(
    (REPO / "data" / "small" / "problems" / "plotter.json").read_text()
)
EXPECTED_SHA256 = "8e85252c84b2f89771642b823ecf38d9b49eb8a1eb6c2a09a4c687daedbb07e8"
EXPECTED_TICKS = [23_854, 56_010, 1_719, 36_052, 80_755, 85_504]


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _frame(segment: tuple[int, int, int, int]) -> list[str]:
    frame = [["0"] * 32 for _ in range(24)]
    for address in bresenham_addresses(*segment):
        frame[address // 32][address % 32] = "f"
    return ["".join(row) for row in frame]


def test_source_and_candidate_are_frozen_and_reproducible():
    source = SOURCE.read_text()
    candidate = CANDIDATE.read_text()
    assert _sha(source) == SOURCE_SHA256
    assert build_plotter_route() == candidate
    assert build_plotter_route() == build_plotter_route()
    assert _sha(candidate) == EXPECTED_SHA256


def test_only_placement_and_two_feed_forward_lengths_change():
    source = SOURCE.read_text()
    candidate = CANDIDATE.read_text()
    assert room_texts(candidate) == room_texts(source)
    assert resolution_by_offset(candidate) == resolution_by_offset(source)
    assert port_margins(candidate) == port_margins(source)

    old, new = bindings(source), bindings(candidate)
    changed = [(before, after) for before, after in zip(old, new) if before != after]
    assert len(changed) == 2
    assert sorted((before[2], after[2]) for before, after in changed) == [
        (111, 109),
        (295, 251),
    ]
    for before, after in changed:
        assert before[:2] + before[3:] == after[:2] + after[3:]


def test_structure_layout_and_hot_paths_are_preserved():
    source = SOURCE.read_text()
    candidate = CANDIDATE.read_text()
    old = Machine.parse(source)
    new = Machine.parse(candidate)
    assert (len(new.rooms), len(new.pipes), len(new.men)) == (14, 18, 12)
    assert validate_layout(candidate) is None
    assert footprint(source) == 24_025
    assert footprint(candidate) == 23_104

    def display_lengths(machine: Machine) -> list[int]:
        return sorted(
            len(pipe.cells)
            for pipe in machine.pipes
            if pipe.source.kind == "display" or pipe.dest.kind == "display"
        )

    assert display_lengths(old) == display_lengths(new) == [3, 19, 56]
    old_ring = max(
        len(pipe.cells)
        for pipe in old.pipes
        if pipe.source.top == 76 and pipe.dest.top == 2
    )
    new_ring = max(
        len(pipe.cells)
        for pipe in new.pipes
        if pipe.source.top == 76 and pipe.dest.top == 2
    )
    assert old_ring == new_ring == 193


def test_public_cases_pass_with_exact_improvement():
    source = judge_problem(SOURCE.read_text(), PROBLEM)
    candidate = judge_problem(CANDIDATE.read_text(), PROBLEM)
    assert candidate.cases_passed == candidate.cases_total == 6
    assert [case.ticks for case in candidate.case_results] == EXPECTED_TICKS
    assert candidate.score < source.score * 0.959


def test_deterministic_multiround_frame_oracle():
    rng = random.Random(20260727)
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
    while len(segments) < 32:
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
    result = judge_case(CANDIDATE.read_text(), rounds, max_ticks=2_500_000)
    assert result.passed, result


def test_terminal_live_response_matches_the_candidate():
    response = json.loads(RESPONSE.read_text())
    assert response["id"] == "c4e94257-0709-4eb4-bd4c-894721ec2294"
    assert response["status"] == "done"
    assert (response["casesPassed"], response["casesTotal"]) == (20, 20)
    assert (response["width"], response["height"], response["area2"]) == (
        152,
        145,
        23_104,
    )
    assert response["avgTicks"] == 69_221
    assert response["score"] == 1_599_281_984
