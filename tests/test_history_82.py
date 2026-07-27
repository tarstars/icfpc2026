"""Release gates for the 82-square History Lesson candidate."""

import hashlib
import json
from pathlib import Path

from littleman import alexey_pipecheck, history_pack, server_compat
from littleman.history_82 import (
    MAIN_PER_WORD,
    MAIN_RADIX,
    TOKENS,
    build_archive,
    build_history_82,
    build_lookup_room,
    build_main_room,
    reference_decode,
)
from littleman.history_archive import _unpack_nonzero_high
from littleman.judge import judge_problem
from littleman.sim import Machine


def _independent_minimum_piece_count(text: str, tokens: tuple[str, ...]) -> int:
    """Exhaustively solve every suffix for the fixed dictionary."""

    cost = [0] * (len(text) + 1)
    for position in range(len(text) - 1, -1, -1):
        cost[position] = 1 + cost[position + 1]
        for token in tokens:
            end = position + len(token)
            if text.startswith(token, position):
                cost[position] = min(cost[position], 1 + cost[end])
    return cost[0]


def _unpack_lookup_value(value: int) -> str:
    chars = []
    while value:
        value, char = divmod(value, 128)
        chars.append(chr(char))
    return "".join(chars)


def test_codec_exhaustively_round_trips_with_pinned_floor_measurements():
    archive = build_archive()
    alphabet = sorted(set(archive.text))

    assert len(TOKENS) == len(set(TOKENS)) == 56
    assert all(2 <= len(token) <= 5 for token in TOKENS)
    assert _independent_minimum_piece_count(archive.text, TOKENS) == 1763
    assert len(archive.main_codes) == 1763
    assert len(archive.main_words) == 196
    assert len(archive.lookup_values) == 128

    assert _unpack_nonzero_high(archive.main_words, MAIN_RADIX) == list(
        archive.main_codes
    )
    assert sorted(
        _unpack_lookup_value(value) for value in archive.lookup_values if value
    ) == sorted([*alphabet, *TOKENS])
    assert reference_decode(archive) == archive.text == history_pack.expected_text()

    # Every code and expansion exercised by the stream is a valid lookup.
    assert all(1 <= code < 128 for code in archive.main_codes)
    assert all(archive.lookup_values[code] for code in archive.main_codes)
    assert len(archive.main_codes) <= 66 * 3 * MAIN_PER_WORD


def test_all_archive_literals_are_signed64_safe_in_both_directions():
    archive = build_archive()
    limit = 1 << 63
    values = [*archive.main_words, *archive.lookup_values]
    assert all(0 <= value < limit for value in values)
    assert all(int(str(value)[::-1]) < limit for value in values)


def test_joint_slot_order_fills_the_82_square_geometry():
    archive = build_archive()
    assert list(map(sum, archive.lookup_width_rows[::2])) == [76] * 6
    assert list(map(sum, archive.lookup_width_rows[1::2])) == [76] * 6
    assert (len(build_main_room(archive)), len(build_main_room(archive)[0])) == (
        68,
        71,
    )
    assert (
        len(build_lookup_room(archive)),
        len(build_lookup_room(archive)[0]),
    ) == (14, 82)


def test_candidate_reproduces_exact_artifact_and_passes_strict_layout():
    generated = build_history_82()
    artifact = Path("submissions/history/history_05.man").read_text()
    assert generated == build_history_82() == artifact
    assert (
        hashlib.sha256(artifact.encode()).hexdigest()
        == "2c949d5b456dda5c72bd07970b4b0ca017cd2c01f8f72a32ee59189876a32d39"
    )
    assert (len(generated.splitlines()), max(map(len, generated.splitlines()))) == (
        82,
        82,
    )
    machine = Machine.parse(generated)
    assert len(machine.rooms) == 6
    assert len(machine.men) == 5
    assert len(machine.pipes) == 5
    assert alexey_pipecheck.report(generated) == [2, 2, 2, 2, 34]
    server_compat.validate_layout(generated)


def test_candidate_emits_the_exact_public_history():
    with open("data/small/problems/history-lesson.json") as problem_file:
        problem = json.load(problem_file)
    result = judge_problem(build_history_82(), problem)
    assert result.cases_passed == result.cases_total == 1
    assert result.case_ticks == [1_701_676]
    assert result.footprint == result.score == 6_724
