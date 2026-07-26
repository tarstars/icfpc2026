"""LLLM CLASSIFY room acceptance (work order claude_17 B).

The load-bearing test composes a LOCAL model of SCAN's frozen semantics with
`classify_reference` and demands the result equal Codex's ACCEPTED
`lllm_loader.reference_stream`.  SCAN's own module is deliberately NOT
imported: the interface is the contract, not the other agent's file.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from littleman import llm_fuzz
from littleman.lllm_classify import (
    build_classify_rig,
    build_classify_room,
    GLYPH_RECORD,
    SPACE,
    WALL,
    classify_record,
    classify_reference,
)
from littleman.lllm_step import case_rounds

ROOT = Path(__file__).resolve().parents[1]
PROBLEM = json.loads(
    (ROOT / "data/small/problems/little-little-little-man.json").read_text()
)
CASES = PROBLEM["publicTestData"]
FUZZ = llm_fuzz.corpus(20260726, 30)


def _loader():
    """Codex's frozen oracle, from this tree or a sibling loader worktree."""
    try:
        return __import__("littleman.lllm_loader", fromlist=["*"])
    except ImportError:
        pass
    for base in (ROOT / "lr", ROOT.parent / "icfpc2026-codex-lllm-loader"):
        path = base / "src/littleman/lllm_loader.py"
        if not path.exists():
            continue
        spec = importlib.util.spec_from_file_location(
            "littleman.lllm_loader", path
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    return None


LOADER = _loader()


# ------------------------------------------------- SCAN's frozen semantics
def scan_semantics(tokens: list[int]) -> list[int]:
    """Local model of work order A: 256 cell tokens, man token, then relay."""
    width, height = tokens[:2]
    chars = iter(tokens[2 : 2 + width * height])
    out: list[int] = []
    man_addr = 0
    for y in range(16):
        for x in range(16):
            padding = int(x >= width or y >= height)
            perimeter = int(x in (0, width - 1) or y in (0, height - 1))
            char = 32
            if not padding:
                char = next(chars)
                if char == ord("@"):
                    man_addr = y * 16 + x
                    char = 32
            out.append(char + 256 * perimeter + 512 * padding)
    return out + [man_addr] + list(tokens[2 + width * height :])


def _streams(case):
    rows, ks, _ = case_rounds(case)
    return llm_fuzz.program_tokens(rows) + ks


class _Feeder:
    """Feed a stream and stop the run once the expected outputs have left."""

    def __init__(self, tokens, expected):
        self.tokens = list(tokens)
        self.expected = expected
        self.output: list[int] = []
        self.ticks: list[int] = []

    def pop_input(self):
        return self.tokens.pop(0) if self.tokens else None

    def on_output(self, value, tick):
        self.output.append(value)
        self.ticks.append(tick)
        if len(self.output) >= self.expected:
            return "passed"
        return None


def run_rig(scan_tokens: list[int], expected: int) -> _Feeder:
    from littleman.sim import Machine

    feeder = _Feeder(scan_tokens, expected)
    machine = Machine.parse(build_classify_rig())
    result = machine.run(controller=feeder, max_ticks=2_000_000)
    assert result.status in ("passed", "tick-cap"), (result.status, result.error)
    assert result.error is None, result.error
    return feeder


def check_rig(scan_tokens: list[int]) -> _Feeder:
    expected = classify_reference(scan_tokens)
    feeder = run_rig(scan_tokens, len(expected))
    assert feeder.output == expected
    return feeder


# ---------------------------------------------------- acceptance 1 (gate)
@pytest.mark.skipif(LOADER is None, reason="frozen loader oracle unavailable")
@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_split_preserves_frozen_contract_public(case):
    tokens = _streams(case)
    assert classify_reference(scan_semantics(tokens)) == LOADER.reference_stream(
        tokens
    )


@pytest.mark.skipif(LOADER is None, reason="frozen loader oracle unavailable")
def test_split_preserves_frozen_contract_fuzz():
    for case in FUZZ:
        tokens = _streams(case)
        assert classify_reference(
            scan_semantics(tokens)
        ) == LOADER.reference_stream(tokens)


# --------------------------------------------------- reference unit checks
def test_padding_outranks_perimeter_and_glyph():
    for char in GLYPH_RECORD:
        assert classify_record(char + 512) == SPACE
        assert classify_record(char + 256 + 512) == SPACE
        assert classify_record(char + 256) == WALL
        assert classify_record(char) == GLYPH_RECORD[char]


def test_packing_is_little_endian_base_8192():
    stream = [ord("H")] * 4 + [32] * 252 + [7]
    packed = classify_reference(stream)
    record = GLYPH_RECORD[ord("H")]
    assert packed[0] == sum(record << (13 * i) for i in range(4))
    assert packed[1:64] == [0] * 63
    assert packed[64:] == [7]


# ------------------------------------------------ acceptance 2: rig equality
@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_rig_matches_reference_public(case):
    check_rig(scan_semantics(_streams(case)))


@pytest.mark.parametrize("index", range(30))
def test_rig_matches_reference_fuzz(index):
    check_rig(scan_semantics(_streams(FUZZ[index])))


# -------------------------------------------------- acceptance 2: directed
def synthetic(cells: dict[int, int], tail: list[int]) -> list[int]:
    """A raw SCAN stream: ``cells`` overrides addresses, the rest is padding."""
    stream = [32 + 512] * 256
    for addr, token in cells.items():
        stream[addr] = token
    return stream + tail


def test_every_glyph_and_both_digit_extremes():
    """One cell per interior glyph, including digits 0 and 9."""
    glyphs = sorted(GLYPH_RECORD)
    feeder = check_rig(
        synthetic({addr: char for addr, char in enumerate(glyphs)}, [200, 1, 2])
    )
    assert feeder.output[64] == 200
    for char in (ord("0"), ord("9")):
        assert char in glyphs


def test_border_operator_is_a_wall_not_an_op():
    for char in (ord("+"), ord("-"), ord("M"), ord("X")):
        stream = synthetic({0: char + 256, 1: char}, [0])
        expected = classify_reference(stream)
        assert expected[0] % (1 << 13) == WALL
        assert (expected[0] >> 13) % (1 << 13) == GLYPH_RECORD[char]
        check_rig(stream)


def test_padding_bit_beats_a_set_perimeter_bit_in_the_rig():
    """SCAN may set both bits on a padded border cell; padding must win."""
    check_rig(synthetic({4: ord("+") + 256 + 512, 5: ord("H") + 512}, [17]))


# ----------------------------------------- acceptance 3/4: determinism, gates
def test_build_is_deterministic():
    assert build_classify_rig() == build_classify_rig()
    assert build_classify_room() == build_classify_room()


def test_layout_gates():
    from littleman import alexey_pipecheck, server_compat
    from littleman.sim import Machine

    text = build_classify_rig()
    machine = Machine.parse(text)
    assert len(machine.men) == 1
    assert len(machine.pipes) == 2
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


def test_room_shape_and_pass_ticks(capsys):
    room = build_classify_room()
    assert len({len(row) for row in room}) == 1
    feeder = check_rig(scan_semantics(_streams(CASES[0])))
    with capsys.disabled():
        print(
            f"\nCLASSIFY room {len(room)}x{len(room[0])}; "
            f"64th packed token at tick {feeder.ticks[63]}; "
            f"man token at tick {feeder.ticks[64]}"
        )
    assert feeder.ticks[63] < 200_000
