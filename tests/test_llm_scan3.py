"""SCAN v3 acceptance: model == machine_stream, then the rooms == model.

The model gate runs the whole chain (v2 reference -> s2_pack ->
p1_stream) against ``llm_lockstep.machine_stream`` byte for byte; the
tail after the first-round tokens must be relayed verbatim.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import llm_fuzz
from littleman.llm import program_grid
from littleman.llm_lockstep import machine_stream
from littleman.llm_scan3 import pack64, scan3_reference

DATA = Path(__file__).resolve().parents[1] / "data/small/problems"
LLM_CASES = json.loads(
    (DATA / "little-little-man.json").read_text()
)["publicTestData"]
LLLM_CASES = json.loads(
    (DATA / "little-little-little-man.json").read_text()
)["publicTestData"]
FUZZ = llm_fuzz.llm_corpus(20260726, 20) + llm_fuzz.corpus(
    20260726, 15, tick_cap=100
)
ADV = [
    ["+---+     +---+", "|>@v|>--->|>@v|", "|  5|     |  1|",
     "|  s|   v<|  r|", "|   |   | |   |", "|^r<|   | |^s<|",
     "+---+   | +---+", "  ^-----<      "],
    ["+----+", "|>@7v|", "|^rs<|", "+----+", "  v^  ", "  v^  ",
     "+----+", "|>@rv|", "|^ s<|", "+----+"],
]
TAIL = [3, 1, 64, 5]


def rows_of(case):
    return program_grid([int(v) for v in case["rounds"][0]["in"]])


def tokens_of(rows):
    width = max(len(r) for r in rows)
    grid = [r.ljust(width) for r in rows]
    return [width, len(rows)] + [ord(ch) for row in grid for ch in row]


def model_check(rows):
    got = scan3_reference(tokens_of(rows) + TAIL)
    assert got == machine_stream(rows) + TAIL


@pytest.mark.parametrize("case", LLM_CASES, ids=lambda c: c["name"])
def test_model_llm_public(case):
    model_check(rows_of(case))


@pytest.mark.parametrize("case", LLLM_CASES, ids=lambda c: c["name"])
def test_model_lllm_public(case):
    model_check(rows_of(case))


@pytest.mark.parametrize(
    "case", FUZZ, ids=[f"fuzz-{i:02d}" for i in range(len(FUZZ))]
)
def test_model_fuzz(case):
    model_check(rows_of(case))


@pytest.mark.parametrize("rows", ADV, ids=["snake", "stacked"])
def test_model_adversarial_bidirectional(rows):
    model_check(rows)


def test_pack64_is_pure_bit_surgery():
    """Four fields per word, everything after cell 255 relayed."""
    fields = [43, 45, 32 + 512, 64 + 256] * 64
    packed = pack64(fields + [17, 0, 0, 1, 9])
    word = 43 + (45 << 13) + ((32 + 512) << 26) + ((64 + 256) << 39)
    assert packed[:64] == [word] * 64
    assert packed[64:] == [17, 0, 0, 1, 9]


class _Script:
    def __init__(self, tokens, want):
        self.tokens, self.want, self.got = list(tokens), want, []

    def pop_input(self):
        return self.tokens.pop(0) if self.tokens else None

    def on_output(self, value, tick):
        self.got.append(value)
        if value != self.want[len(self.got) - 1]:
            return "failed"
        return "passed" if len(self.got) >= len(self.want) else None


CHAIN_ROOMS = [
    ["+--+", "|@ |", "|  |", "+--+"],
    ["+--+ +--+", "|@ |>|  |", "+--+ +--+"],          # one-cell pipe
    ["+--+--+", "|@ |  |", "+--+--+"],                # shared wall column
]


@pytest.mark.parametrize(
    "rows", CHAIN_ROOMS, ids=["tiny", "pipe1", "shared"]
)
def test_scan3_machine_room(rows):
    """The composed chain emits machine_stream + relayed tail, in sim.

    The full 61-case corpus and 35-case fuzz run of this gate lives in
    the session gate scripts (worst observed 14.5M ticks, cap 50M).
    """
    from littleman.fastsim import Machine
    from littleman.llm_scan3 import build_scan3_machine

    want = machine_stream(rows) + TAIL
    sc = _Script(tokens_of(rows) + TAIL, want)
    res = Machine.parse(build_scan3_machine()).run(
        max_ticks=30_000_000, controller=sc
    )
    assert res.error is None and res.status == "passed", (
        res.error, res.status, len(sc.got), len(want))
