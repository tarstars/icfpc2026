"""brackets_03: the fast classifier machine must agree with a Python model."""

import json
import random
from pathlib import Path

import pytest

from littleman.brackets_fast import build, ROOMS_04, ROOMS_05, PIPES_04
from littleman.judge import judge_case, judge_problem

ROOT = Path(__file__).resolve().parents[1]
MAN = ROOT / "submissions" / "brackets" / "brackets_03.man"
MAN4 = ROOT / "submissions" / "brackets" / "brackets_04.man"
TYPE = {40: 1, 41: 1, 91: 2, 93: 2, 123: 3, 125: 3}
OPENERS = (40, 91, 123)
CLOSE_OF = {40: 41, 91: 93, 123: 125}


def model(chars):
    """0 if balanced, else the 1-based position of the first offence."""
    stack = []
    for i, c in enumerate(chars, 1):
        if c in OPENERS:
            stack.append(TYPE[c])
        elif not stack or stack.pop() != TYPE[c]:
            return i
    return 0 if not stack else len(chars) + 1


def corpus():
    rnd = random.Random(20260726)
    out = [[], [40], [41], [40, 41], [41, 40], [91, 41], [123, 125] * 32]
    out.append([40] * 32 + [41] * 32)                      # depth exactly 32
    out.append([91] * 32 + [93] * 32)
    out.append([40, 41] * 16 + [40, 91, 123] * 10 + [125, 93])  # 32 left unclosed
    out.append([125] + [40, 41] * 31)                      # offence at 1
    out.append([40, 41] * 31 + [93])                       # offence at 63
    for _ in range(30):                                    # random balanced
        stack, s = [], []
        while len(s) < rnd.randrange(0, 65):
            if stack and (len(stack) >= 32 or rnd.random() < 0.5):
                s.append(CLOSE_OF[stack.pop()])
            else:
                op = rnd.choice(OPENERS)
                stack.append(op)
                s.append(op)
        s.extend(CLOSE_OF[c] for c in reversed(stack))
        out.append(s[:64])
    for _ in range(20):                                    # random junk
        out.append([rnd.choice(list(TYPE)) for _ in range(rnd.randrange(1, 65))])
    return out


@pytest.fixture(scope="module")
def text():
    assert MAN.read_text() == build(ROOMS_04, PIPES_04), "brackets_03.man is stale"
    return MAN.read_text()


def test_public_cases(text):
    problem = json.loads((ROOT / "data/small/problems/brackets.json").read_text())
    report = judge_problem(text, problem)
    assert report.cases_passed == report.cases_total
    assert report.footprint == 1225


def test_fuzz(text):
    cases = corpus()
    assert len(cases) >= 50
    for chars in cases:
        rounds = [{"in": [len(chars)] + list(chars), "out": [model(chars)]}]
        res = judge_case(text, rounds)
        assert res.passed, (chars, res.reason)


# ------------------------- brackets_04: CLOSE with the detour folded


@pytest.fixture(scope="module")
def text4():
    assert MAN4.read_text() == build(ROOMS_05, PIPES_04), "brackets_04.man is stale"
    return MAN4.read_text()


def test_public_cases_04(text4):
    problem = json.loads((ROOT / "data/small/problems/brackets.json").read_text())
    report = judge_problem(text4, problem)
    assert report.cases_passed == report.cases_total
    assert report.footprint == 1225
    assert report.score < 490_000  # brackets_03 scores 548,800 locally


def test_fuzz_04(text4):
    for chars in corpus():
        rounds = [{"in": [len(chars)] + list(chars), "out": [model(chars)]}]
        res = judge_case(text4, rounds)
        assert res.passed, (chars, res.reason)


def test_directed_offences_04(text4):
    """Paths specific to the folded CLOSE: floored '/' on S-t < 0, arms."""
    cases = [
        [40, 93], [40, 125], [91, 125],           # t_top < t: S-t negative
        [91, 41], [123, 41], [123, 93],           # t_top > t
        [41] * 64,                                # empty-stack arm, offence 1
        [40] * 32 + [93] + [41] * 31,             # deep mismatch at 33
        [123] * 32 + [125] * 31,                  # unclosed end arm, 64
        [40, 41, 40, 41, 40, 93],                 # offence on last char
    ]
    for chars in cases:
        rounds = [{"in": [len(chars)] + list(chars), "out": [model(chars)]}]
        res = judge_case(text4, rounds)
        assert res.passed, (chars, res.reason)


def test_close_bindings_04(text4):
    """Every s/r in CLOSE keeps its role; port margins stay >= 2."""
    from littleman.ir_export import machine_ir
    from littleman.room_ports import Op, audit
    from littleman.sim import Machine

    ir = machine_ir(text4)
    ends = {tuple(p["cells"][0]): i for i, p in enumerate(ir["pipes"])}
    state_in = next(i for i, p in enumerate(ir["pipes"])
                    if tuple(p["cells"][-1]) == (9, 11))
    cmd = next(i for i, p in enumerate(ir["pipes"])
               if tuple(p["cells"][-1]) == (12, 4))
    state_out, out = ends[(9, 9)], ends[(9, 30)]
    role = {state_in: "state_in", cmd: "cmd", state_out: "state_out", out: "out"}
    ops, seen = [], set()
    for cell, e in ir["resolution"].items():
        r, c = map(int, cell.split(","))
        if 10 < r < 17:
            ops.append(Op((r, c), role[e["pipe"]], e["op"] == "s"))
            seen.add((e["op"], role[e["pipe"]]))
    assert ("r", "cmd") in seen and ("s", "state_out") in seen
    assert ("r", "state_in") in seen and ("s", "out") in seen
    assert not any(role == "cmd" and op == "s" for op, role in seen)
    m = Machine.parse(text4)
    close = next(rm for rm in m.rooms if rm.kind == "room" and rm.top == 10)
    rep = audit(m, close, ops)
    assert rep["satisfied"] and rep["margin"] >= 2, rep
