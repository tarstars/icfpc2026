"""Gates for the Hello World machine.

The program takes no input, so the only interesting failure modes are
arithmetic (a delta chain that drifts) and layout (a literal split across
a row turn, which silently changes its value because a westward literal
reads its digits backwards).
"""

import json
import pathlib

from littleman.hello_world import TEXT, build_hello_world, build_room, tokens
from littleman.judge import judge_problem

REPO = pathlib.Path(__file__).resolve().parent.parent
ARTIFACT = REPO / "submissions" / "hello-world" / "hello_00.man"
PROBLEM = REPO / "data" / "small" / "problems" / "hello-world.json"


def _problem():
    return json.loads(PROBLEM.read_text())


def test_delta_chain_reproduces_the_text():
    """Interpret the token stream the way the little man would."""
    a = b = 0
    emitted = []
    for tok in tokens():
        if tok == "M":
            b = a
        elif tok == "N":
            a = -a
        elif tok == "+":
            a = a + b
        elif tok == "s":
            emitted.append(a)
        elif tok == "H":
            break
        else:
            a = int(tok.strip("`"))
    assert emitted == [ord(c) for c in TEXT]


def test_no_literal_is_split_across_a_row():
    """Every backtick pair must open and close on the same room row."""
    for row in build_room(11):
        assert row.count("`") % 2 == 0, row


def test_public_case_passes():
    report = judge_problem(build_hello_world(), _problem())
    assert report.cases_passed == report.cases_total == 1


def test_artifact_matches_the_generator():
    assert ARTIFACT.read_text() == build_hello_world()


def test_generator_is_deterministic():
    assert build_hello_world() == build_hello_world()


def test_footprint_is_the_swept_optimum():
    lines = [x for x in build_hello_world().split("\n") if x]
    assert max(len(lines), max(len(x) for x in lines)) == 13
