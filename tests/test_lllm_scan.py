"""LLLM SCAN station acceptance (work order A, claude_17).

Model first: :func:`littleman.lllm_scan.scan_reference` is the oracle and the
rig must equal it token for token.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, llm_fuzz, lllm_step, server_compat
from littleman.lllm_scan import CELLS, build_scan_rig, scan_reference
from littleman.sim import Machine


def stream_of(rows: list[str], tail: list[int] | None = None) -> list[int]:
    """``W H`` then the row-major chars, then any later round tokens."""
    height, width = len(rows), len(rows[0])
    chars = [ord(ch) for row in rows for ch in row]
    return [width, height, *chars, *(tail or [])]


TINY = ["+--+", "|@ |", "| +|", "+--+"]


def test_reference_on_hand_computed_4x4():
    """Every 4x4 cell is on the program border except (1,1) and (1,2)."""
    out = scan_reference(stream_of(TINY, [7]))
    assert len(out) == CELLS + 2
    assert out[-2:] == [17, 7]                    # man at y=1,x=1; relayed 7
    # row 0: four border cells, then twelve padding cells on y == 0.
    assert out[0:4] == [ord("+") + 256, ord("-") + 256, ord("-") + 256,
                        ord("+") + 256]
    assert out[4:16] == [32 + 256 + 512] * 12     # padding, but still y == 0
    # row 1: '|' border, '@' -> plain space, ' ', '|' border, then padding.
    assert out[16:20] == [ord("|") + 256, 32, 32, ord("|") + 256]
    assert out[20:32] == [32 + 512] * 12
    # row 2 interior holds the '+' at x == 2 with no perimeter bit.
    assert out[34] == ord("+")
    # rows 4..15 are padding throughout, but x in {0, W-1} still sets the
    # perimeter bit: the two flags are independent by the frozen definition.
    assert out[64:CELLS] == [
        32 + 512 + (256 if addr % 16 in (0, 3) else 0)
        for addr in range(64, CELLS)
    ]


class Script:
    """Feed the rig its stream; stop the run on the last expected token."""

    def __init__(self, tokens, expected):
        self.tokens = list(tokens)
        self.expected = list(expected)
        self.got: list[int] = []
        self.last_tick = 0

    def pop_input(self):
        return self.tokens.pop(0) if self.tokens else None

    def on_output(self, value, tick):
        self.got.append(value)
        self.last_tick = tick
        return "passed" if len(self.got) >= len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_scan_rig()


def run_rig(text, stream, max_ticks=1_000_000):
    expected = scan_reference(stream)
    script = Script(stream, expected)
    result = Machine.parse(text).run(max_ticks=max_ticks, controller=script)
    assert result.error is None, result.error
    assert result.status == "passed", (result.status, len(script.got))
    return script.got, script.last_tick


def check(text, rows, tail=None):
    stream = stream_of(rows, tail)
    got, ticks = run_rig(text, stream)
    assert got == scan_reference(stream)
    return ticks


# ------------------------------------------------------------ layout gates
def test_generator_is_deterministic(text):
    assert build_scan_rig() == text


def test_layout_passes_server_compatibility(text):
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)
    for pipe in Machine.parse(text).pipes:
        assert len(pipe.cells) >= 2      # the server rejects 1-cell pipes


def test_rooms_and_pipes(text):
    machine = Machine.parse(text)
    assert len(machine.rooms) == 4       # I, SCAN, RELAY, O
    assert len(machine.men) == 2         # SCAN and the ring relay
    ring = [p for p in machine.pipes if p.source.kind == p.dest.kind == "room"]
    assert len(ring) == 2
    # all five ring tokens must be able to park between rotations
    assert sum(len(p.cells) for p in ring) >= 5


# ------------------------------------------------------------- corpora
PROBLEM = json.loads(
    (
        Path(__file__).resolve().parents[1]
        / "data/small/problems/little-little-little-man.json"
    ).read_text()
)
CASES = PROBLEM["publicTestData"]
FUZZ = llm_fuzz.corpus(20260727, 30)


def rows_of(case):
    return lllm_step.case_rounds(case)[0]


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_public_case(text, case):
    check(text, rows_of(case), [3, 5])


@pytest.mark.parametrize("seed", range(len(FUZZ)))
def test_fuzz_world(text, seed):
    check(text, rows_of(FUZZ[seed]))


# --------------------------------------------------------------- directed
def world(width: int, height: int, *, man=None, border=None) -> list[str]:
    """A blank program of the given size, optionally with a placed man and
    an operator glyph written over one top-border cell."""
    rows = [
        "+" + "-" * (width - 2) + "+"
        if y in (0, height - 1)
        else "|" + " " * (width - 2) + "|"
        for y in range(height)
    ]
    if border is not None:
        rows[0] = rows[0][:border] + "+" + rows[0][border + 1 :]
    if man is not None:
        y, x = man
        rows[y] = rows[y][:x] + "@" + rows[y][x + 1 :]
    return rows


@pytest.mark.parametrize("size", [(4, 4), (16, 16), (4, 16), (16, 4), (5, 9)])
def test_directed_extremes(text, size):
    check(text, world(*size, man=(1, 1)))


@pytest.mark.parametrize("man", [(1, 1), (1, 6), (5, 1), (6, 6), (3, 4)])
def test_directed_man_positions(text, man):
    rows = world(8, 8, man=man)
    stream = stream_of(rows)
    got, _ = run_rig(text, stream)
    assert got == scan_reference(stream)
    assert got[CELLS] == man[0] * 16 + man[1]


def test_operator_on_the_border_keeps_its_glyph(text):
    """The perimeter bit is set but the char is relayed untouched -- it is
    CLASSIFY, not SCAN, that turns a border cell into a wall record."""
    rows = world(10, 6, man=(2, 2), border=4)
    stream = stream_of(rows)
    got, _ = run_rig(text, stream)
    assert got == scan_reference(stream)
    assert got[4] == ord("+") + 256


def test_relays_every_later_token_forever(text):
    check(text, world(6, 5, man=(2, 2)), [0, 1, 2, 3, 99, -7, 12345])


def test_reported_ticks(record_property, text):
    """Prologue cost (the tick of the first cell token) and whole-scan cost,
    measured on the smallest and the largest program."""
    for width, height in ((4, 4), (16, 16)):
        rows = world(width, height, man=(1, 1))
        stream = stream_of(rows)
        script = Script(stream, scan_reference(stream)[:1])
        Machine.parse(text).run(max_ticks=1_000_000, controller=script)
        prologue = script.last_tick
        _, total = run_rig(text, stream)
        record_property(f"prologue_ticks_{width}x{height}", prologue)
        record_property(f"total_ticks_{width}x{height}", total)
        assert prologue < 2000
        assert total < 400_000


def test_round_trip_is_deterministic(text):
    """Two runs of one world agree, and so do two builds of the room."""
    rows = world(9, 7, man=(3, 4))
    first, _ = run_rig(text, stream_of(rows))
    second, _ = run_rig(build_scan_rig(), stream_of(rows))
    assert first == second == scan_reference(stream_of(rows))
