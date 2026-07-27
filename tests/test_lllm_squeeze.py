"""Release gates for the exact blank-line ``lllm_04`` squeeze."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from littleman import server_compat
from littleman.alexey_pipecheck import check as pipe_check
from littleman.ir_export import machine_ir
from littleman.judge import footprint
from littleman.lllm_squeeze import (
    CANDIDATE_SHA256,
    DROPPED_COLUMNS,
    DROPPED_ROWS,
    PARENT_SHA256,
    apply_lllm_squeeze,
    build_lllm_squeeze,
)
from littleman.sim import Machine

REPO = Path(__file__).resolve().parents[1]
PARENT = REPO / "submissions/lllm/lllm_03.man"
ARTIFACT = REPO / "submissions/lllm/lllm_04.man"
PROBLEM = json.loads(
    (REPO / "data/small/problems/little-little-little-man.json").read_text()
)


def shifted_key(key: str) -> str:
    row, column = map(int, key.split(","))
    row -= sum(dropped < row for dropped in DROPPED_ROWS)
    column -= sum(dropped < column for dropped in DROPPED_COLUMNS)
    return f"{row},{column}"


def test_exact_transform_artifact_and_hash():
    parent = PARENT.read_text()
    candidate = build_lllm_squeeze()
    assert hashlib.sha256(parent.encode()).hexdigest() == PARENT_SHA256
    assert hashlib.sha256(candidate.encode()).hexdigest() == CANDIDATE_SHA256
    assert apply_lllm_squeeze(parent) == candidate == ARTIFACT.read_text()


def test_layout_topology_and_footprint_are_strict():
    candidate = build_lllm_squeeze()
    machine = Machine.parse(candidate)
    server_compat.validate_layout(candidate)
    pipe_check(candidate)
    assert (len(machine.rooms), len(machine.pipes), len(machine.men)) == (13, 18, 11)
    assert sorted(len(pipe.cells) for pipe in machine.pipes) == [
        2,
        2,
        4,
        6,
        9,
        17,
        19,
        19,
        20,
        21,
        28,
        34,
        43,
        51,
        68,
        98,
        130,
        597,
    ]
    lines = candidate.rstrip("\n").splitlines()
    assert (max(map(len, lines)), len(lines), footprint(candidate)) == (
        304,
        311,
        96_721,
    )


def test_every_pipe_resolution_is_preserved():
    parent_resolution = machine_ir(PARENT.read_text())["resolution"]
    candidate_resolution = machine_ir(build_lllm_squeeze())["resolution"]
    shifted = {shifted_key(key): value for key, value in parent_resolution.items()}
    assert len(shifted) == 628
    assert shifted == candidate_resolution


def test_public_cases_clear_the_next_rank_target():
    report = server_compat.judge_problem(build_lllm_squeeze(), PROBLEM)
    assert (report.cases_passed, report.cases_total) == (10, 10)
    assert report.case_ticks == [
        198093,
        122842,
        340523,
        180233,
        232864,
        177443,
        134416,
        142101,
        226687,
        370584,
    ]
    assert report.score == 20_560_814_770.600002
    assert report.score < 21_498_879_916.8 * 0.966
