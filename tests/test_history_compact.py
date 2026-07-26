"""Release gates for the 84-square History Lesson archive."""

import hashlib
import json
from pathlib import Path

from littleman import alexey_pipecheck, server_compat
from littleman.history_compact import (
    build_archive,
    build_history_compact,
    build_lookup_room,
    build_main_room,
    build_rotated_selector_room,
    reference_decode,
)
from littleman.history_archive import _unpack_nonzero_high
from littleman.judge import judge_problem
from littleman.sim import Machine


def test_compact_archive_round_trips_with_pinned_measurements():
    archive = build_archive()
    assert len(archive.tokens) == 56
    assert all(2 <= len(token) <= 5 for token in archive.tokens)
    assert len(archive.main_codes) == 1809
    assert len(archive.main_words) == 201
    assert len(archive.lookup_values) == 128
    assert len(archive.lookup_rows) == 12
    assert list(map(sum, archive.lookup_width_rows[::2])) == [
        73,
        74,
        77,
        77,
        77,
        77,
    ]
    assert all(
        len(_unpack_nonzero_high((word,), 128)) == 9
        for word in archive.main_words
    )
    assert _unpack_nonzero_high(archive.main_words, 128) == list(
        archive.main_codes
    )
    assert reference_decode(archive) == archive.text


def test_compact_rooms_have_the_planned_geometry_and_parse():
    archive = build_archive()
    rooms = (
        (build_main_room(archive), (69, 71)),
        (build_lookup_room(archive), (14, 83)),
        (build_rotated_selector_room(), (22, 9)),
    )
    for room, dimensions in rooms:
        assert (len(room), len(room[0])) == dimensions
        parsed = Machine.parse("\n".join(room))
        assert len(parsed.rooms) == 1
        assert len(parsed.men) == 1


def test_complete_candidate_is_deterministic_and_server_safe():
    first = build_history_compact()
    assert first == build_history_compact()
    artifact = Path("submissions/history/history_04.man").read_text()
    assert artifact == first
    assert (
        hashlib.sha256(artifact.encode()).hexdigest()
        == "d0b7083ffb78ceaa2b22bddc208a01b6ab1bceba0ebcbde8a8899b9ba35378ea"
    )
    assert (len(first.splitlines()), max(map(len, first.splitlines()))) == (83, 83)
    machine = Machine.parse(first)
    assert len(machine.rooms) == 6
    assert len(machine.men) == 5
    assert alexey_pipecheck.report(first) == [2, 2, 2, 2, 35]
    server_compat.validate_layout(first)


def test_complete_candidate_emits_the_canonical_history_under_tick_cap():
    program = build_history_compact()
    with open("data/small/problems/history-lesson.json") as problem_file:
        problem = json.load(problem_file)
    result = judge_problem(program, problem)
    assert result.cases_passed == result.cases_total == 1
    assert result.case_ticks == [1_758_189]
    assert result.footprint == result.score == 6_889
