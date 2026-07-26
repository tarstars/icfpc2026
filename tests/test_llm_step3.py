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
LLM_PIPED = [c for c in LLM_CASES if not pipeless(c)]


# ------------------------------------------------------------ phase C gate
@pytest.mark.parametrize("case", LLM_PIPED, ids=lambda c: c["name"])
def test_phase_c_llm_piped_public(case):
    check_case3(*case_rows_ks(case))


def test_phase_c_fuzz_piped():
    bad, ran = [], 0
    for i, case in enumerate(llm_fuzz.llm_corpus(20260727, 60)):
        rows, ks = case_rows_ks(case)
        if machine_stream(rows)[67] == 0:
            continue
        ran += 1
        try:
            check_case3(rows, ks)
        except AssertionError:
            bad.append(i)
    assert bad == [] and ran >= 30


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


# ------------------------------------------------- room phase A: the chain
def test_chain_room_classifies_all_records():
    from littleman.llm_step3 import build_chain_rig, classify_record
    from littleman.sim import Machine

    recs = [c + w for c in range(32, 127) if c != 58 for w in (0, 256)]
    recs += [0, 32 + 512, 32 + 768]          # padding cells
    res = Machine.parse(build_chain_rig()).run(max_ticks=300_000, inputs=recs)
    assert res.output == [classify_record(r) for r in recs]


def intake_words(stream):
    """The 64 packed claude_09 words the model hands FETCH."""
    from littleman.lllm_step import ScriptedFetch
    from littleman.llm_step3 import Step3Model

    model = Step3Model(ScriptedFetch())
    model.intake(stream)
    return [
        sum(model.fetch.records[4 * j + i] << (13 * i) for i in range(4))
        for j in range(64)
    ], list(model.ring)


def test_intake_room_feeds_fetch_words():
    import random

    from littleman.llm_step3 import build_intake_rig
    from littleman.sim import Machine

    rig = build_intake_rig()
    cases = [case_rows_ks(LLLM_CASES[i])[0] for i in (0, 5)]
    for i in (2, 7, 11):
        rng = random.Random(20260726 * 1000 + i)
        cases.append(multiman_program(rng))
    for rows in cases:
        stream = machine_stream(rows)
        words, _ = intake_words(stream)
        res = Machine.parse(rig).run(max_ticks=600_000, inputs=stream[:68])
        assert res.output == words, rows


def test_emit_rig_first_frame():
    import random

    from littleman.lllm_step import ScriptedFetch
    from littleman.llm_step3 import Step3Model, build_step3_rig
    from littleman.sim import Machine

    rig = build_step3_rig()
    cases = [case_rows_ks(LLLM_CASES[i])[0] for i in (0, 5)]
    for i in (2, 7):
        cases.append(multiman_program(random.Random(20260726000 + i)))
    for rows in cases:
        stream = machine_stream(rows)
        model = Step3Model(ScriptedFetch())
        model.intake(stream)
        model.emit_frame()
        res = Machine.parse(rig).run(max_ticks=600_000, inputs=stream[:68])
        assert res.output == model.deltas, rows


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


# ------------------------------------------------- room: the tick loop top
def loop_top_case(ctrls, k):
    """Seed ring1 = [C,A,I,B]x3 + [MARK, SP, SHIFTM, K]; run the model."""
    from littleman.llm_step3 import MARK, Step3Model
    from littleman.lllm_step import ScriptedFetch

    seed = []
    for i, c in enumerate(ctrls):
        seed += [c, 3 * i + 1, 3 * i + 2, 3 * i + 3]
    seed += [MARK, 0, 4, k]
    model = Step3Model(ScriptedFetch())
    model.ring = list(seed)
    tag = {"emit": 1, "idle": 2, "tick": 3}[model._loop_top()]
    return seed, [tag] + list(model.ring)


def test_loop_top_rig_matches_model():
    from littleman.llm_step3 import build_loop_top_rig
    from littleman.sim import Machine

    rig = build_loop_top_rig()
    cases = [([18, 5, 1], 3),        # walled found -> global freeze, emit
             ([5, 6, 7], 2),         # all frozen, k > 0 -> idle
             ([5, 1, 6], 2),         # a live man, k > 0 -> tick
             ([5, 6, 7], 0),         # countdown done -> emit
             ([5, 18, 1], 2),        # walled at man 1: A1 -> drain entry 1
             ([5, 5, 18], 2),        # walled at man 2: A2 -> drain entry 2
             ([1, 5, 18], 2),        # live then walled: B2 -> drain entry 2
             ([5, 1, 6], 0)]         # live but k == 0 -> emit off the tick
    for ctrls, k in cases:
        seed, want = loop_top_case(ctrls, k)
        res = Machine.parse(rig).run(max_ticks=120_000, inputs=seed)
        assert res.output == want, (ctrls, k, res.output)
