"""Lockstep STEP (claude_24): model must be byte-exact vs from_stream.

Phase A: the 10 LLLM public programs (single man, no pipes).
Phase B: every no-pipe LLM public case (pileup, bounce house, ...) and a
no-pipe fuzz corpus with up to 3 men, collisions and the global freeze.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import llm_fuzz
from littleman.llm import program_grid
from littleman.llm_lockstep import machine_stream
from littleman.llm_step3 import check_case3

DATA = Path(__file__).resolve().parents[1] / "data/small/problems"
LLLM_CASES = json.loads(
    (DATA / "little-little-little-man.json").read_text()
)["publicTestData"]
LLM_CASES = json.loads(
    (DATA / "little-little-man.json").read_text()
)["publicTestData"]


def case_rows_ks(case):
    rounds = case["rounds"]
    rows = program_grid([int(v) for v in rounds[0]["in"]])
    return rows, [int(rnd["in"][0]) for rnd in rounds[1:]]


def pipeless(case):
    rows, _ = case_rows_ks(case)
    return machine_stream(rows)[67] == 0


# ------------------------------------------------------------ phase A gate
@pytest.mark.parametrize("case", LLLM_CASES, ids=lambda c: c["name"])
def test_phase_a_lllm_public(case):
    check_case3(*case_rows_ks(case))


# ------------------------------------------------------------ phase B gate
LLM_NOPIPE = [c for c in LLM_CASES if pipeless(c)]


@pytest.mark.parametrize("case", LLM_NOPIPE, ids=lambda c: c["name"])
def test_phase_b_llm_nopipe_public(case):
    check_case3(*case_rows_ks(case))


OPS = " " * 8 + "^>v<^>v<0123456789M+-XH"


def _fill(rng, rows, top, left, bottom, right):
    for r in range(top + 1, bottom):
        for c in range(left + 1, right):
            rows[r][c] = rng.choice(OPS)


def _box(rows, top, left, bottom, right):
    for c in range(left, right + 1):
        rows[top][c] = rows[bottom][c] = "-"
    for r in range(top, bottom + 1):
        rows[r][left] = rows[r][right] = "|"
    for r, c in ((top, left), (top, right), (bottom, left), (bottom, right)):
        rows[r][c] = "+"


def multiman_program(rng) -> list[str]:
    """1 room with 2-3 men, or 2 shared/near-wall rooms with a man each."""
    kind = rng.randrange(3)
    w, h = rng.randrange(8, 16), rng.randrange(6, 12)
    rows = [[" "] * 16 for _ in range(16)]
    if kind == 0:                       # one room, 2-3 men: collisions
        _box(rows, 0, 0, h, w)
        _fill(rng, rows, 0, 0, h, w)
        spots = [(r, c) for r in range(1, h) for c in range(1, w)]
        for r, c in rng.sample(spots, rng.randrange(2, 4)):
            rows[r][c] = "@"
    else:                               # two rooms; kind 1 shares the wall
        mid = rng.randrange(5, 10)
        _box(rows, 0, 0, h, mid)
        _box(rows, 0, mid if kind == 1 else mid + 1, h, 15)
        _fill(rng, rows, 0, 0, h, mid)
        _fill(rng, rows, 0, mid if kind == 1 else mid + 1, h, 15)
        rows[rng.randrange(1, h)][rng.randrange(1, mid)] = "@"
        rows[rng.randrange(1, h)][
            rng.randrange((mid if kind == 1 else mid + 1) + 1, 15)] = "@"
    return ["".join(r).rstrip() for r in rows[: h + 1]]


def test_phase_b_fuzz_multiman():
    import random

    bad, ran = [], 0
    for i in range(160):
        rng = random.Random(20260726 * 1000 + i)
        rows = multiman_program(rng)
        ks = [rng.randrange(0, 9) for _ in range(rng.randrange(1, 7))]
        try:
            stream = machine_stream(rows)
        except ValueError:
            continue                    # interior arrow parses as a pipe head
        if stream[67] != 0:
            continue
        ran += 1
        try:
            check_case3(rows, ks)
        except AssertionError:
            bad.append(i)
    assert bad == [] and ran >= 60


def test_phase_b_fuzz_nopipe():
    bad = []
    corpus = llm_fuzz.llm_corpus(20260726, 40) + llm_fuzz.corpus(
        20260726, 10, tick_cap=100
    )
    for i, case in enumerate(corpus):
        rows, ks = case_rows_ks(case)
        if machine_stream(rows)[67] != 0:
            continue
        try:
            check_case3(rows, ks)
        except AssertionError:
            bad.append(i)
    assert bad == []
