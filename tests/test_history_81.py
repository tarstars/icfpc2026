"""Release gates for the exact 81-square History Lesson archive."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from littleman import history_pack, server_compat
from littleman.alexey_pipecheck import check as pipe_check
from littleman.history_81 import (
    PAIR_WIDTH_PATTERNS,
    TOKENS,
    build_archive,
    build_history_81,
    reference_decode,
)
from littleman.judge import footprint
from littleman.sim import Machine

REPO = Path(__file__).resolve().parents[1]
ARTIFACT = REPO / "submissions/history/history_06.man"
PROBLEM = json.loads((REPO / "data/small/problems/history-lesson.json").read_text())
EXPECTED_SHA256 = "95cadc619fa745a5fe90ed6925079e932992c6dec8f2fac6c9338771b883b899"
LIMIT = (1 << 63) - 1


def unpack(words: tuple[int, ...]) -> list[int]:
    codes = []
    for word in words:
        while word:
            word, code = divmod(word, 128)
            codes.append(code)
    return codes


def test_joint_codec_hits_both_81_square_bounds():
    archive = build_archive()
    assert len(TOKENS) == 56
    assert len(archive.main_codes) == 1754
    assert len(archive.main_words) == 195
    assert [sum(row) for row in archive.lookup_width_rows] == [75] * 12
    assert [sum(pattern) for pattern in PAIR_WIDTH_PATTERNS] == [
        70,
        75,
        75,
        75,
        75,
        75,
    ]


def test_archive_is_exact_and_every_literal_is_parser_safe():
    archive = build_archive()
    assert reference_decode(archive) == history_pack.expected_text()
    assert unpack(archive.main_words) == list(archive.main_codes)
    assert all(
        word <= LIMIT and int(str(word)[::-1]) <= LIMIT for word in archive.main_words
    )


def test_generator_artifact_hash_and_strict_layout():
    generated = build_history_81()
    assert generated == build_history_81() == ARTIFACT.read_text()
    assert hashlib.sha256(generated.encode()).hexdigest() == EXPECTED_SHA256
    lines = generated.rstrip("\n").splitlines()
    assert (len(lines), max(map(len, lines)), footprint(generated)) == (
        81,
        81,
        6561,
    )
    machine = Machine.parse(generated)
    assert (len(machine.rooms), len(machine.pipes), len(machine.men)) == (6, 5, 5)
    assert sorted(len(pipe.cells) for pipe in machine.pipes) == [2, 2, 2, 2, 32]
    server_compat.validate_layout(generated)
    pipe_check(generated)


def test_public_history_is_exact():
    report = server_compat.judge_problem(build_history_81(), PROBLEM)
    assert (report.cases_passed, report.cases_total) == (1, 1)
    assert report.case_ticks == [1_667_288]
    assert report.score == 6561
