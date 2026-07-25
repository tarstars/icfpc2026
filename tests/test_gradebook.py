"""Grade Book generated-machine tests."""

import json
import random
from pathlib import Path

import pytest

from littleman.gradebook import (
    GradebookLayout,
    build_gradebook,
    build_gradebook_compact,
)
from littleman.judge import footprint, judge_case, judge_problem
from littleman.sim import Machine

PROBLEMS = Path(__file__).resolve().parent.parent / "data" / "small" / "problems"
SUBMISSIONS = Path(__file__).resolve().parent.parent / "submissions" / "gradebook"


def test_program_loads():
    Machine.parse(build_gradebook())


def test_preserved_candidate_matches_generator():
    assert (SUBMISSIONS / "gradebook_00.man").read_text() == build_gradebook()


def test_compact_candidate_matches_generator():
    assert (SUBMISSIONS / "gradebook_01.man").read_text() == build_gradebook_compact()


def test_passes_public_cases():
    problem = json.loads((PROBLEMS / "gradebook.json").read_text())
    report = judge_problem(build_gradebook(), problem)
    assert report.cases_passed == report.cases_total == 7, report.case_results


def test_compact_passes_public_cases_and_reduces_footprint():
    problem = json.loads((PROBLEMS / "gradebook.json").read_text())
    report = judge_problem(build_gradebook_compact(), problem)
    assert report.cases_passed == report.cases_total == 7, report.case_results
    assert report.footprint == 454**2
    assert report.footprint < footprint(build_gradebook())


@pytest.mark.parametrize(
    "layout",
    [
        GradebookLayout(command_left_clearance=0),
        GradebookLayout(worker_gap=3, command_left_clearance=4),
        GradebookLayout(margin=4, command_left_clearance=4),
        GradebookLayout(ack_right_clearance=1),
        GradebookLayout(fsm_right_padding=-1),
        GradebookLayout(worker_vertical_gap=1),
    ],
)
def test_layout_rejects_unsafe_route_clearances(layout):
    with pytest.raises(ValueError):
        layout.validate()


def test_compact_data_rings_keep_full_roster_capacity():
    machine = Machine.parse(build_gradebook_compact())
    worker_rooms = [
        room
        for room in machine.rooms
        if room.right - room.left + 1 == 111 and room.bottom - room.top + 1 >= 199
    ]
    assert len(worker_rooms) == 4
    data_pipes = [
        pipe
        for room in worker_rooms
        for pipe in machine.in_pipes[id(room)]
        if pipe.cells[-1][1] == room.left + 22
    ]
    assert len(data_pipes) == 4
    assert min(len(pipe.cells) for pipe in data_pipes) > 33


def _generated_rounds(seed: int = 20260724) -> list[dict[str, list[int]]]:
    rng = random.Random(seed)
    count = 16
    subjects = 4
    student_ids = rng.sample(range(1000, 10_000), count)
    grades = {
        student_id: [rng.randrange(101) for _ in range(subjects)]
        for student_id in student_ids
    }
    grades[student_ids[0]][0] = 100
    grades[student_ids[1]][0] = 100
    grades[student_ids[2]][1] = 0

    roster = [count, subjects]
    for student_id in student_ids:
        roster.extend([student_id, *grades[student_id]])
    rounds = [{"in": roster, "out": []}]

    for batch_index in range(6):
        encoded = [8]
        expected = []
        for operation_index in range(8):
            operation = (batch_index * 8 + operation_index) % 4 + 1
            subject = rng.randrange(subjects)
            student_id = rng.choice(student_ids)
            if operation == 1:
                encoded.extend([operation, student_id, subject + 1])
                expected.append(grades[student_id][subject])
            elif operation == 2:
                value = rng.choice([0, 100, rng.randrange(101)])
                encoded.extend([operation, student_id, subject + 1, value])
                grades[student_id][subject] = value
            elif operation == 3:
                encoded.extend([operation, subject + 1])
                expected.append(
                    sum(values[subject] for values in grades.values()) // count
                )
            else:
                encoded.extend([operation, subject + 1])
                top_grade = max(values[subject] for values in grades.values())
                expected.append(
                    min(
                        candidate
                        for candidate, values in grades.items()
                        if values[subject] == top_grade
                    )
                )
        rounds.append({"in": encoded, "out": expected})
    return rounds


def test_compact_matches_generated_gradebook_oracle():
    result = judge_case(
        build_gradebook_compact(),
        _generated_rounds(),
        max_ticks=5_000_000,
    )
    assert result.passed, result.reason
