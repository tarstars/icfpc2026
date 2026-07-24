"""Regression tests for the geometry-only compact Memory variant."""

from __future__ import annotations

import json
from pathlib import Path

from littleman.judge import footprint, judge_problem
from littleman.memory import build_memory, build_memory_compact

REPO = Path(__file__).resolve().parent.parent
PROBLEM = json.loads((REPO / "data" / "small" / "problems" / "memory.json").read_text())


def test_compact_memory_matches_checked_in_candidate():
    candidate = REPO / "submissions" / "memory" / "memory_01.man"
    assert build_memory_compact() == candidate.read_text()


def test_compact_memory_passes_public_cases_with_smaller_footprint():
    compact = build_memory_compact()
    report = judge_problem(compact, PROBLEM)
    assert report.cases_passed == report.cases_total == 7, report.case_results
    assert footprint(compact) == 2209
    assert footprint(compact) < footprint(build_memory())
