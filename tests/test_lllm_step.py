"""LLLM STEP station: MODEL-FIRST acceptance (work order claude_11b).

`StepModel` + the scripted claude_11a FETCH stub must reproduce the
`littleman.llm` oracle's frames, expressed through the claude_10 delta
grammar, on every public case and a 100-case fuzz corpus.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import llm_fuzz
from littleman.llm import LLM
from littleman.lllm_step import (
    CLASS_HALT,
    CLASS_WALL,
    ScriptedFetch,
    StepModel,
    case_rounds,
    frames_from_deltas,
    loader_stream,
    oracle_frames,
    pack_world,
    run_case,
)

PROBLEM = json.loads(
    (
        Path(__file__).resolve().parents[1]
        / "data/small/problems/little-little-little-man.json"
    ).read_text()
)
CASES = PROBLEM["publicTestData"]
FUZZ = llm_fuzz.corpus(20260726, 100)


def rows_of(case):
    return case_rounds(case)[0]


def check(rows, ks):
    """Run the model and assert its delta stream renders the oracle frames."""
    model = run_case(rows, ks)
    assert frames_from_deltas(model.deltas) == oracle_frames(rows, ks)
    return model


# ------------------------------------------------------- hard gate (acc. 1)
@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_public_case_frames(case):
    rows, ks, frames = case_rounds(case)
    model = run_case(rows, ks)
    assert frames_from_deltas(model.deltas) == frames


def test_fuzz_corpus_frames():
    bad = []
    for i, case in enumerate(FUZZ):
        rows, ks, frames = case_rounds(case)
        if frames_from_deltas(run_case(rows, ks).deltas) != frames:
            bad.append(i)
    assert bad == []


# --------------------------------------------------------- frozen grammars
@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_delta_grammar(case):
    """claude_10: pixels in [0,4095], one negative sentinel per round."""
    rows, ks, _ = case_rounds(case)
    deltas = run_case(rows, ks).deltas
    rounds = [[]]
    for token in deltas:
        if token < 0:
            rounds.append([])
        else:
            assert 0 <= token <= 4095
            rounds[-1].append(token)
    assert rounds.pop() == []                      # stream ends on a commit
    assert len(rounds) == 1 + len(ks)
    assert len(rounds[0]) == 257                   # 256 static + the man
    assert [t // 16 for t in rounds[0][:256]] == list(range(256))
    assert rounds[0][256] % 16 == 9
    assert all(len(r) == 2 and r[1] % 16 == 9 for r in rounds[1:])


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_fetch_request_grammar(case):
    """claude_11a: 64 setup tokens verbatim, then only legal requests."""
    rows, ks, _ = case_rounds(case)
    fetch = ScriptedFetch()
    run_case(rows, ks, fetch=fetch)
    assert loader_stream(rows)[:64] == [
        sum(fetch.records[4 * j + i] << (13 * i) for i in range(4))
        for j in range(64)
    ]
    assert fetch.setup_left == 0
    assert fetch.requests[0] == -1                 # round 1 asks for the frame
    assert fetch.requests.count(-1) == 1
    assert all(-1 <= t <= 511 for t in fetch.requests)
    colour_fetches = [t for t in fetch.requests if t >= 256]
    assert len(colour_fetches) == len(ks)          # exactly one per later round


def test_setup_seeds_control_state():
    rows = rows_of(CASES[1])
    _, man_addr = pack_world(rows)
    model = StepModel(ScriptedFetch())
    model.setup(loader_stream(rows))
    assert model.ring == [man_addr, 1, 0, 0, man_addr]   # heading East, live


def test_determinism():
    rows, ks, _ = case_rounds(CASES[0])
    assert run_case(rows, ks).deltas == run_case(rows, ks).deltas


# ------------------------------------------------------- directed (acc. 3)
HALT = ["+----+", "|@ H |", "|    |", "+----+"]
WALL = ["+---+", "|@  |", "|   |", "+---+"]
# a closed 8-tick racetrack; each lap runs `M` then `+`, so A_i doubles
RING = ["+----+", "|@9v |", "|vM< |", "|    |", "|>+^ |", "+----+"]
X_ZERO = ["+----+", "|@X  |", "|    |", "+----+"]
X_POS = ["+----+", "|@1X |", "|    |", "+----+"]
X_NEG = ["+------+", "|@1M--X|", "|      |", "+------+"]


def test_halt_mid_round():
    """H at tick 3 of a k=10 round: the rest of the round is skipped."""
    model = check(HALT, [10, 5])
    assert model.ticks == 3
    assert model._read("CTRL") & 4                 # frozen
    assert len(model.deltas) == 257 + 1 + 2 * 3    # both rounds still emit


def test_wall_freeze_then_sentinel_only_rounds():
    """The wall is found by the NEXT fetch; later rounds are no-ops."""
    model = check(WALL, [8, 4, 4])
    assert model.ticks == 4                        # 3 moves + the discovery
    rounds = "".join("|" if t < 0 else "." for t in model.deltas).split("|")
    assert [len(r) for r in rounds[1:-1]] == [2, 2, 2]
    tail = model.deltas[-6:]
    assert tail[0] == tail[3] and tail[1] == tail[4]   # frame stops changing


def test_branch_all_three_arms():
    for rows in (X_ZERO, X_POS, X_NEG):
        check(rows, [6, 6])
    ends = [run_case(rows, [6])._read("ADDR") for rows in (X_ZERO, X_POS, X_NEG)]
    assert len(set(ends)) == 3                     # straight / cw / ccw differ


def test_old_equals_addr_round():
    """A full lap of the racetrack ends where it began; still emits."""
    model = run_case(RING, [3, 8])
    assert frames_from_deltas(model.deltas) == oracle_frames(RING, [3, 8])
    assert model.trace[-1][3] == model.trace[-1][4]
    assert len(model.deltas) == 257 + 1 + 2 * 3


def test_wrap64_loop_and_k64():
    """8 rounds of k=64: 61 doublings from 9 push A_i past 2**63."""
    ks = [64] * 8
    model = check(RING, ks)
    assert model.ticks == 512
    reference = LLM.parse(RING)
    reference.run(512)
    assert model._read("AI") < 0                   # native 64-bit wrap
    assert model._read("AI") == reference.men[0].A


def test_thirty_rounds():
    ks = [1] * 29
    model = check(RING, ks)
    assert len(model.trace) == 30
    assert model.deltas.count(-1) == 30


# ------------------------------------------------------ counts / invariant
def oracle_ticks(rows, ks):
    machine = LLM.parse(rows)
    count = 0
    for k in ks:
        for _ in range(k):
            if machine.halted():
                break
            machine.step()
            count += 1
    return count


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_interpreted_tick_counts(case):
    """STEP runs at most one extra tick: the one that *discovers* a wall."""
    rows, ks, _ = case_rounds(case)
    model = run_case(rows, ks)
    assert model.ticks <= sum(ks)
    assert model.ticks - oracle_ticks(rows, ks) in (0, 1)


# -------------------------------------------- phase 2 hooks (auto-arming)
def _module(name):
    try:
        return __import__(f"littleman.{name}", fromlist=["*"])
    except ImportError:
        return None


@pytest.mark.skipif(_module("lllm_loader") is None, reason="claude_09 not landed")
def test_local_packer_matches_real_loader():
    loader = _module("lllm_loader")
    for case in CASES:
        rows = rows_of(case)
        expected = list(loader.reference_stream(llm_fuzz.program_tokens(rows)))
        assert expected[:65] == loader_stream(rows)


@pytest.mark.skipif(_module("lllm_fetch") is None, reason="claude_11a not landed")
def test_integration_rig_with_real_fetch():
    from littleman.lllm_step import ReferenceFetch

    for case in CASES + FUZZ[:30]:
        rows, ks, _ = case_rounds(case)
        assert (
            run_case(rows, ks, fetch=ReferenceFetch()).deltas
            == run_case(rows, ks).deltas
        )


def test_build_step_room_reports_its_blocker():
    from littleman.lllm_step import build_step_room

    if _module("lllm_fetch") is not None:
        pytest.skip("claude_11a landed: transcription is now unblocked")
    with pytest.raises(NotImplementedError, match="lllm_fetch"):
        build_step_room()


def test_class_table_is_the_frozen_one():
    """Wall and halt are the only two freezing classes."""
    rows = ["+---+", "|@H |", "|   |", "+---+"]
    fetch = ScriptedFetch()
    for token in loader_stream(rows)[:64]:
        fetch.send(token)
    assert fetch.send(0) == [CLASS_WALL << 4]
    assert fetch.send(18) == [CLASS_HALT << 4]
    assert fetch.send(0 + 256) == [4] and fetch.send(18 + 256) == [3]
