"""llm_lockstep must be byte-exact vs llm.LLM on every case, every tick."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import llm_fuzz
from littleman.llm import LLM, program_grid
from littleman.llm_lockstep import LockstepLLM

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


def replay_lockstep(case):
    """Step model and oracle one tick at a time; compare every frame."""
    rounds = case["rounds"]
    rows = program_grid([int(v) for v in rounds[0]["in"]])
    ours, ref = LockstepLLM.parse(rows), LLM.parse(rows)
    assert ours.render() == ref.render() == rounds[0]["frames"][0], "round 0"
    for index, rnd in enumerate(rounds[1:], 1):
        for tick in range(int(rnd["in"][0])):
            ours.run(1)
            ref.run(1)
            assert ours.render() == ref.render(), f"round {index} tick {tick}"
        assert ours.render() == rnd["frames"][0], f"round {index}"
    assert ours.halted() == ref.halted()


@pytest.mark.parametrize("case", LLM_CASES, ids=lambda c: c["name"])
def test_llm_public_byte_exact(case):
    replay_lockstep(case)


@pytest.mark.parametrize("case", LLLM_CASES, ids=lambda c: c["name"])
def test_lllm_public_byte_exact(case):
    replay_lockstep(case)


@pytest.mark.parametrize(
    "case", FUZZ, ids=[f"fuzz-{i:02d}" for i in range(len(FUZZ))]
)
def test_fuzz_byte_exact(case):
    replay_lockstep(case)


@pytest.mark.parametrize("case", LLM_CASES, ids=lambda c: c["name"])
def test_discovery_matches_sim(case):
    """Room/pipe discovery from the raw grid must equal sim.Machine.parse."""
    from littleman.sim import Machine

    rows = program_grid([int(v) for v in case["rounds"][0]["in"]])
    machine = Machine.parse("\n".join(rows))
    ours = LockstepLLM.parse(rows)
    assert ours.rooms == [
        (rm.top, rm.left, rm.bottom, rm.right) for rm in machine.rooms
    ]
    index = {id(rm): i for i, rm in enumerate(machine.rooms)}
    assert [
        (cells, src, dst)
        for cells, src, dst in zip(
            ours.pipe_cells, ours.pipe_src, ours.pipe_dst
        )
    ] == [
        (list(p.cells), index[id(p.source)], index[id(p.dest)])
        for p in machine.pipes
    ]
    assert len(ours.pipe_cells) <= 2
    assert sum(len(c) for c in ours.pipe_cells) <= 20


def _multiman_rows(rng):
    """Single room crammed with 2-3 men: collisions, trains, halted targets."""
    import random

    w, h = rng.randint(6, 14), rng.randint(5, 12)
    ops = " " * 8 + "><^v" * 3 + "0123456789M+-XH"
    grid = [[rng.choice(ops) for _ in range(w - 2)] for _ in range(h - 2)]
    spots = [(r, c) for r in range(h - 2) for c in range(w - 2)]
    for r, c in rng.sample(spots, rng.randint(2, 3)):
        grid[r][c] = "@"
    top = "+" + "-" * (w - 2) + "+"
    return [top] + ["|" + "".join(row) + "|" for row in grid] + [top]


@pytest.mark.parametrize("seed", range(40))
def test_multiman_collision_parity(seed):
    """Tick-by-tick parity vs llm.LLM with several men per room."""
    import random

    rows = _multiman_rows(random.Random(20260726 * 100 + seed))
    ours, ref = LockstepLLM.parse(rows), LLM.parse(rows)
    assert ours.render() == ref.render()
    for tick in range(60):
        ours.run(1)
        ref.run(1)
        assert ours.render() == ref.render(), f"tick {tick}"
        assert ours.man_halt == [int(m.halted) for m in ref.men], f"tick {tick}"
        assert ours.man_wall == [int(m.on_wall) for m in ref.men]
        if ours.halted():
            assert ref.halted()
            break
