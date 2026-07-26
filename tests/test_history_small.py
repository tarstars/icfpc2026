import json
from pathlib import Path

from littleman.history_small import (
    CHAIN_BOUNDS,
    CHAIN_GAPS,
    PROBLEM_PATH,
    RADIX,
    TOKEN_BASE_VALUE,
    build_encoding,
    build_history_small,
    history_output,
    history_text,
)
from littleman.judge import judge_problem
from littleman.sim import Machine

SUBMISSION = Path(__file__).resolve().parent.parent / "submissions/history/history_02.man"


def test_encoding_packs_288_words_and_round_trips():
    _, mapping, tokens, symbols, words = build_encoding()
    assert len(tokens) == 3
    assert max(mapping.values()) + 1 == TOKEN_BASE_VALUE - 49
    assert len(symbols) == 2578
    assert len(words) == 288 and len(words) % 4 == 0
    assert all(value < 10**17 for value in words)
    assert max(symbols) < RADIX


def test_decoder_chain_reproduces_every_ascii_code():
    """The conditional-add chain baked into the mapper room must be exact."""

    _, mapping, tokens, _, _ = build_encoding()
    for code, index in mapping.items():
        accumulator = index + 31
        for bound, gap in zip(CHAIN_BOUNDS, CHAIN_GAPS):
            if accumulator < bound:
                break
            accumulator += gap
        assert accumulator < TOKEN_BASE_VALUE
        assert accumulator == code
    for offset in range(len(tokens)):
        accumulator = max(mapping.values()) + 1 + offset + 31
        for bound, gap in zip(CHAIN_BOUNDS, CHAIN_GAPS):
            if accumulator < bound:
                break
            accumulator += gap
        assert accumulator - TOKEN_BASE_VALUE == offset


def test_program_is_an_85_square():
    lines = build_history_small().rstrip("\n").split("\n")
    assert len(lines) == 85
    assert max(len(line) for line in lines) == 85


def test_program_emits_the_expected_history_text():
    source = build_history_small()
    machine = Machine.parse(source)
    result = machine.run(max_ticks=500_000)
    expected = history_output()
    assert result.error is None
    assert result.output == expected
    assert "".join(chr(value) for value in result.output) == history_text()
    assert len(result.output) == 2810


def test_judge_passes_and_scores_the_smaller_footprint():
    source = build_history_small()
    problem = json.loads(Path(PROBLEM_PATH).read_text())
    report = judge_problem(source, problem)
    assert report.cases_passed == report.cases_total == 1, report.case_results[0]
    assert report.footprint == 85**2
    assert report.footprint <= 87**2
    assert report.score == report.footprint


def test_generator_is_deterministic_and_matches_the_artifact():
    assert build_history_small() == build_history_small()
    assert SUBMISSION.read_text() == build_history_small()
