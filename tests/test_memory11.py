"""Preservation gates for the recovered counted memory_11 artifact."""

from __future__ import annotations

import hashlib
import json
import pathlib

from littleman import server_compat
from littleman.alexey_pipecheck import check as pipe_check
from littleman.judge import footprint, judge_problem
from littleman.sim import Machine

REPO = pathlib.Path(__file__).resolve().parent.parent
ARTIFACT = REPO / "submissions" / "memory" / "memory_11.man"
PROBLEM = json.loads((REPO / "data/small/problems/memory.json").read_text())


def test_recovered_artifact_identity_and_layout():
    program = ARTIFACT.read_text()
    assert hashlib.sha256(program.encode()).hexdigest() == (
        "c9e2dea84fa3b6d809cfe85a02abfcf7e614349d5488432e776fdd256fbb41a4"
    )
    machine = Machine.parse(program)
    assert (len(machine.rooms), len(machine.pipes), len(machine.men)) == (7, 7, 5)
    assert footprint(program) == 841
    server_compat.validate_layout(program)
    pipe_check(program)


def test_recovered_artifact_passes_with_exact_public_ticks():
    report = judge_problem(ARTIFACT.read_text(), PROBLEM)
    assert (report.cases_passed, report.cases_total) == (7, 7)
    assert report.case_ticks == [295, 625, 1557, 1117, 1547, 919, 21507]
    assert report.score == 3_311_978.142857143


def test_recovered_live_response_matches_artifact():
    response = json.loads(ARTIFACT.with_name("memory_11-submit.json").read_text())
    assert response["id"] == "89c637e7-7601-4637-a36f-07b94afeb12f"
    assert response["casesPassed"] == response["casesTotal"] == 24
    assert (response["width"], response["height"], response["area2"]) == (29, 29, 841)
    assert response["score"] == 16_033_454.75
