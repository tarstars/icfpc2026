"""The component-pipeline decomposition must reproduce the monolith exactly.

`littleman.llm_components.LLMPipeline` re-expresses the validated reference
interpreter (`littleman.llm.LLM`) as seven components wired by integer-only
FIFO queues (see the module docstring there for the full netlist). These
tests are the contract validation claude_07 calls for: if the decomposition
cannot reproduce the monolith frame-for-frame on the full public + fuzz
corpus, the decomposition is wrong, however plausible it looks.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman.llm import LLM, program_grid
from littleman.llm_components import LLMPipeline, Q
from littleman.llm_fuzz import corpus

ROOT = Path(__file__).resolve().parents[1]
LLM_PROBLEM = json.loads((ROOT / "data/small/problems/little-little-man.json").read_text())
LLLM_PROBLEM = json.loads(
    (ROOT / "data/small/problems/little-little-little-man.json").read_text()
)

LLM_CASES = LLM_PROBLEM["publicTestData"]
LLLM_CASES = LLLM_PROBLEM["publicTestData"]
FUZZ_CASES = corpus(20260725, 200)


def _replay_monolith(rounds) -> list[list[str]]:
    """The same replay `tests/test_llm.py::replay` performs, frames only."""
    machine = LLM.parse(program_grid([int(v) for v in rounds[0]["in"]]))
    frames = [machine.render()]
    for rnd in rounds[1:]:
        machine.run(int(rnd["in"][0]))
        frames.append(machine.render())
    return frames


# --------------------------------------------------------- acceptance (1)
@pytest.mark.parametrize("case", LLM_CASES, ids=lambda c: c["name"])
def test_llm_public_cases_match_monolith(case):
    expected = _replay_monolith(case["rounds"])
    got = LLMPipeline().run_case(case["rounds"])
    assert got == expected


@pytest.mark.parametrize("case", LLLM_CASES, ids=lambda c: c["name"])
def test_lllm_public_cases_match_monolith(case):
    expected = _replay_monolith(case["rounds"])
    got = LLMPipeline().run_case(case["rounds"])
    assert got == expected


@pytest.mark.parametrize("case", FUZZ_CASES, ids=lambda c: c["name"])
def test_fuzz_corpus_matches_monolith(case):
    expected = _replay_monolith(case["rounds"])
    got = LLMPipeline().run_case(case["rounds"])
    assert got == expected


def test_public_and_fuzz_counts():
    """Guard the acceptance scope itself: 14 LLM + 10 LLLM + 200 fuzz."""
    assert len(LLM_CASES) == 14
    assert len(LLLM_CASES) == 10
    assert len(FUZZ_CASES) == 200


# --------------------------------------------------------- acceptance (2)
def test_queue_rejects_non_int_records():
    q = Q("test")
    q.put(5)
    q.put(-1)
    assert q.get() == 5
    assert q.get() == -1
    for bad in ("x", 1.0, (1, 2), [1], {1: 2}, None, True, False):
        with pytest.raises(TypeError):
            q.put(bad)


def test_every_queue_in_a_real_run_carried_only_int():
    case = next(c for c in LLM_CASES if c["name"] == "first steps")
    pipeline = LLMPipeline(trace=True)
    pipeline.run_case(case["rounds"])
    traces = pipeline.traces()
    assert traces  # at least one queue was created
    for name, values in traces.items():
        assert all(type(v) is int for v in values), name


# --------------------------------------------------------- acceptance (3)
def test_trace_retrieval_and_determinism():
    case = next(c for c in LLM_CASES if c["name"] == "first steps")

    p1 = LLMPipeline(trace=True)
    frames1 = p1.run_case(case["rounds"])
    trace1 = p1.traces()

    p2 = LLMPipeline(trace=True)
    frames2 = p2.run_case(case["rounds"])
    trace2 = p2.traces()

    expected = _replay_monolith(case["rounds"])
    assert frames1 == expected
    assert frames2 == expected

    assert set(trace1) == set(trace2)
    assert trace1 == trace2  # deterministic across two independent runs

    assert trace1["delta"], "EXEC -> DELTA_DRAW stream should be nonempty (the man moves)"
