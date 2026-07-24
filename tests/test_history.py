import json
from pathlib import Path

from littleman.history import (
    PROBLEM_PATH,
    build_history,
    build_history_unsafe,
    history_output,
    pack_history_words,
    pack_history_words_fixed,
    unpack_history_words,
)
from littleman.judge import judge_problem
from littleman.sim import Machine


def test_history_radix_rows_round_trip():
    expected = history_output()
    rows = pack_history_words(expected)
    assert len(rows) == 75
    assert unpack_history_words(rows) == expected


def test_history_program_emits_exact_text():
    source = build_history()
    Machine.parse(source)
    problem = json.loads(Path(PROBLEM_PATH).read_text())
    report = judge_problem(source, problem)
    assert report.cases_passed == report.cases_total == 1, report.case_results[0]
    assert report.footprint <= 89**2
    assert report.score == report.footprint


def test_checked_in_history_variant_matches_generator():
    submission = Path(__file__).resolve().parent.parent / "submissions/history"
    assert (submission / "history_00.man").read_text() == build_history_unsafe()
    assert (submission / "history_01.man").read_text() == build_history()


def test_history_fixed_words_are_dense_and_round_trip():
    expected = history_output()
    words = pack_history_words_fixed(expected)
    assert len(words) == 308
    assert len(words) % 4 == 0
    assert all(value < 10**18 for value in words)
    assert unpack_history_words([words]) == expected
