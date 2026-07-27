"""Shave-a-row/column with proof (docs/MANIFEST.md step 2).

Score is max(w,h)^2 * ticks, so one cell off the binding dimension beats a
large tick win: reverse went 14x14 -> 13x13 at essentially unchanged ticks
for a 0.862x score.

These tests exist because the blunt version of this operation cost us two
candidates. A squeeze that merely passes the public cases is not evidence
-- a shortened storage pipe deadlocks only on inputs the public set never
reaches. So the tests here are mostly NEGATIVE: they assert the verifier
REFUSES the bad transformations, which is the property that matters.
"""

import json
import pathlib

import pytest

from littleman import room_shrink

REPO = pathlib.Path(__file__).resolve().parent.parent
ART = REPO / "submissions" / "memory" / "tarstars_memory_14.man"


def _cases():
    spec = json.loads(
        (REPO / "data" / "small" / "problems" / "memory.json").read_text())
    return spec["publicTestData"][:2]


pytestmark = pytest.mark.skipif(not ART.exists(), reason="artifact absent")


def test_rejects_a_transformation_that_shortens_a_pipe():
    """The deadlock trap: alexey's subset-sum squeeze went 0/7 this way and
    a snake squeeze of mine passed 5/5 public then died at length 68."""
    text = ART.read_text()
    candidate = room_shrink.drop_row(text, 20)
    verdict = room_shrink.verify(text, candidate, _cases())
    assert not verdict.ok
    assert "shortened" in verdict.reason, verdict.reason


def test_rejects_a_transformation_that_will_not_load():
    text = ART.read_text()
    for row in (10, 27):
        verdict = room_shrink.verify(text, room_shrink.drop_row(text, row),
                                     _cases())
        assert not verdict.ok
        assert "does not load" in verdict.reason, verdict.reason


def test_rejects_a_change_that_does_not_shrink_the_box():
    """memory_13 -> memory_14 is a real 2.71% tick win at IDENTICAL geometry.
    Good change, but not a shave, and `verify` must say so rather than
    reporting success for the wrong reason."""
    before = (REPO / "submissions" / "memory" / "memory_13.man").read_text()
    verdict = room_shrink.verify(before, ART.read_text(), _cases())
    assert not verdict.ok
    assert verdict.reason == "box did not shrink"


def test_blank_candidate_scan_is_honest_about_finding_nothing():
    """memory has no already-blank row or column. That is exactly why the
    blunt squeeze found nothing here while a human hand-compacted content
    until a row freed up -- the operation this module is a step toward."""
    assert room_shrink.blank_candidates(ART.read_text()) == []


def test_pipe_lengths_and_box_agree_with_the_live_artifact():
    text = ART.read_text()
    assert room_shrink.pipe_lengths(text) == [2, 2, 4, 10, 10, 13, 21]
    assert room_shrink.box(text) == 30
