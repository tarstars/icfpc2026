"""brackets_03: the fast classifier machine must agree with a Python model."""

import json
import random
from pathlib import Path

import pytest

from littleman.brackets_fast import build, ROOMS_04, PIPES_04
from littleman.judge import judge_case, judge_problem

ROOT = Path(__file__).resolve().parents[1]
MAN = ROOT / "submissions" / "brackets" / "brackets_03.man"
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
