"""Acceptance tests for the frozen LLLM LOADER stream and two-pipe rig."""

from __future__ import annotations

import gc
import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.lllm_loader import (
    GLYPH_RECORD,
    WALL,
    build_loader_rig,
    reference_stream,
)
from littleman.llm_fuzz import corpus, program_tokens
from littleman.sim import Machine, Man, Pipe

ROOT = Path(__file__).resolve().parents[1]
PROBLEM = json.loads(
    (ROOT / "data/small/problems/little-little-little-man.json").read_text()
)
MAX_TICKS = int(PROBLEM["tickCap"])


def _program(
    width: int,
    height: int,
    *,
    man: tuple[int, int],
    interior: str = " ",
) -> list[str]:
    """Build one rectangular LLLM program with adversarial border glyphs."""

    rows: list[list[str]] = []
    for y in range(height):
        row: list[str] = []
        for x in range(width):
            if y in (0, height - 1):
                row.append("+" if x % 2 == 0 else "-")
            elif x in (0, width - 1):
                row.append("-" if y % 2 == 0 else "+")
            else:
                row.append(interior)
        rows.append(row)
    x, y = man
    rows[y][x] = "@"
    return ["".join(row) for row in rows]


def _with_glyphs(
    width: int,
    height: int,
    *,
    man: tuple[int, int],
) -> list[str]:
    rows = [list(row) for row in _program(width, height, man=man)]
    glyphs = " ^>v<0123456789M+-XH"
    cells = [
        (x, y)
        for y in range(1, height - 1)
        for x in range(1, width - 1)
        if (x, y) != man
    ]
    for (x, y), glyph in zip(cells, glyphs, strict=False):
        rows[y][x] = glyph
    return ["".join(row) for row in rows]


def _unpack_records(stream: list[int]) -> list[int]:
    records: list[int] = []
    for token in stream[:64]:
        records.extend((token >> (13 * offset)) & 0x1FFF for offset in range(4))
    return records


def test_reference_directed_edges_and_every_glyph():
    rows = _with_glyphs(16, 16, man=(14, 14))
    tokens = program_tokens(rows) + [1, -9, 2**63 - 1]
    stream = reference_stream(tokens)
    records = _unpack_records(stream)

    assert stream[64:] == [14 * 16 + 14, 1, -9, 2**63 - 1]
    for x in range(16):
        assert records[x] == WALL
        assert records[15 * 16 + x] == WALL
    for y in range(16):
        assert records[y * 16] == WALL
        assert records[y * 16 + 15] == WALL

    for y, row in enumerate(rows):
        for x, glyph in enumerate(row):
            if x in (0, 15) or y in (0, 15):
                continue
            expected = 0 if glyph == "@" else GLYPH_RECORD[ord(glyph)]
            assert records[y * 16 + x] == expected


@pytest.mark.parametrize("man", [(1, 1), (2, 1), (1, 2), (2, 2)])
def test_reference_minimum_room_and_interior_corners(man):
    rows = _program(4, 4, man=man)
    stream = reference_stream(program_tokens(rows))
    records = _unpack_records(stream)
    assert stream[64] == man[1] * 16 + man[0]
    assert records[man[1] * 16 + man[0]] == 0
    for y in range(16):
        for x in range(16):
            if x >= 4 or y >= 4:
                assert records[y * 16 + x] == 0


@pytest.fixture(scope="module")
def rig_text() -> str:
    return build_loader_rig()


def test_rig_is_deterministic(rig_text):
    assert build_loader_rig() == rig_text


def test_rig_layout_gates(rig_text):
    machine = Machine.parse(rig_text)
    assert len(machine.rooms) == 3
    assert len(machine.men) == 1
    assert len(machine.pipes) == 2
    assert [len(pipe.cells) for pipe in machine.pipes] == [3, 3]
    del machine
    gc.collect()

    server_compat.validate_layout(rig_text)
    alexey_pipecheck.check(rig_text)


@pytest.fixture(scope="module")
def parsed_rig(rig_text) -> Machine:
    return Machine.parse(rig_text)


def _fresh_machine(template: Machine) -> Machine:
    """Clone mutable runtime state while sharing the parsed immutable grid."""

    machine = Machine(
        template.grid,
        template.rooms,
        [Man(man.r, man.c, man.room, direction=man.direction) for man in template.men],
        [
            Pipe(list(pipe.cells), pipe.source, pipe.dest, side=pipe.side)
            for pipe in template.pipes
        ],
    )
    for attribute in ("hpairs", "vpairs", "hdigits", "vdigits"):
        setattr(machine, attribute, getattr(template, attribute))
    return machine


class _ExactStreamController:
    def __init__(self, inputs: list[int], expected: list[int]):
        self.inputs = inputs.copy()
        self.expected = expected
        self.index = 0

    def pop_input(self) -> int | None:
        return self.inputs.pop(0) if self.inputs else None

    def on_output(self, value: int, _tick: int) -> str | None:
        if self.index >= len(self.expected):
            return "failed"
        if value != self.expected[self.index]:
            return "failed"
        self.index += 1
        return "passed" if self.index == len(self.expected) else None


def _run_exact(template: Machine, inputs: list[int]):
    expected = reference_stream(inputs)
    controller = _ExactStreamController(inputs, expected)
    result = _fresh_machine(template).run(
        max_ticks=MAX_TICKS,
        controller=controller,
    )
    assert result.status == "passed", (
        result.status,
        result.error,
        result.ticks,
        controller.index,
        len(expected),
    )
    assert result.output == expected
    return result


def _case_inputs(case: dict) -> list[int]:
    rounds = case["rounds"]
    setup = [int(value) for value in rounds[0]["in"]]
    return setup + [int(round_["in"][0]) for round_ in rounds[1:]]


def _all_rig_cases() -> list:
    return PROBLEM["publicTestData"] + corpus(20260726, 50)


# Parametrised rather than looped so `pytest -n auto` can spread these across
# cores. As one test it was 199s of a 476s suite -- 42% of the whole run, and
# an Amdahl floor no amount of parallelism could get under.
@pytest.mark.parametrize(
    "case", _all_rig_cases(), ids=lambda c: str(c.get("name", "fuzz"))
)
def test_rig_matches_all_public_and_fifty_fuzz_cases(parsed_rig, case):
    _run_exact(parsed_rig, _case_inputs(case))


@pytest.mark.parametrize(
    "rows",
    [
        _program(4, 4, man=(1, 1)),
        _program(4, 4, man=(2, 2)),
        _with_glyphs(16, 16, man=(1, 1)),
        _with_glyphs(16, 16, man=(14, 14)),
    ],
    ids=["4x4-nw", "4x4-se", "16x16-nw", "16x16-se"],
)
def test_directed_rig_extremes_and_man_positions(parsed_rig, rows):
    _run_exact(parsed_rig, program_tokens(rows) + [7, -3])


def test_prologue_ticks_to_first_relayed_value(parsed_rig):
    measured = {}
    for label, rows in (
        ("4x4", _program(4, 4, man=(1, 1))),
        ("16x16", _with_glyphs(16, 16, man=(14, 14))),
    ):
        result = _run_exact(parsed_rig, program_tokens(rows) + [17])
        measured[label] = result.output_ticks[65]

    assert measured == {"4x4": 3028168, "16x16": 4107204}
