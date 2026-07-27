from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib

import pytest

from littleman import server_compat
from littleman.judge import footprint, judge_problem
from littleman.sim import Machine

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILD_PATH = ROOT / "experiments" / "codex_3-gradebook" / "build.py"
PROBLEM_PATH = ROOT / "data" / "small" / "problems" / "gradebook.json"
EXPECTED_SHA256 = "bd83b5ae20e482697444bbe07c7df09f165707c1acb005f96addb63a955e3fc1"
EXPECTED_TICKS = (18762, 62256, 64464, 49556, 70909, 34373, 217200)


def _load_builder():
    spec = importlib.util.spec_from_file_location("codex3_gradebook_build", BUILD_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_codex3_gradebook_rank_step() -> None:
    text = _load_builder().build_candidate()
    lines = text.rstrip("\n").split("\n")

    assert (max(map(len, lines)), len(lines)) == (379, 315)
    assert footprint(text) == 379**2
    assert hashlib.sha256(text.encode()).hexdigest() == EXPECTED_SHA256

    machine = Machine.parse(text)
    assert (len(machine.rooms), len(machine.pipes), len(machine.men)) == (16, 31, 14)
    assert min(len(pipe.cells) for pipe in machine.pipes) >= 2
    server_compat.validate_layout(text)

    problem = json.loads(PROBLEM_PATH.read_text())
    report = judge_problem(text, problem)
    assert report.cases_passed == report.cases_total == 7
    assert tuple(report.case_ticks) == EXPECTED_TICKS
    assert report.score == pytest.approx(10_619_584_331.428572)
