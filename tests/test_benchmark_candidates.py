"""Tests for the exact-file candidate benchmark entry point."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "benchmark_candidates.py"


def test_benchmark_reports_exact_metrics_and_parent_comparison(tmp_path):
    output_path = tmp_path / "benchmark.json"
    command = [
        sys.executable,
        str(SCRIPT),
        "max-element",
        "submissions/max-element/max_00.man",
        "--parent",
        "submissions/max-element/max_00.man",
        "--json-output",
        str(output_path),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO,
        check=True,
        text=True,
        capture_output=True,
    )
    stdout = json.loads(completed.stdout)
    written = json.loads(output_path.read_text())
    assert stdout == written
    candidate = stdout["candidates"][0]
    assert candidate["casesPassed"] == candidate["casesTotal"] == 10
    assert candidate["maxDimension"] == 14
    assert candidate["footprint"] == 196
    assert candidate["rooms"] == 3
    assert candidate["men"] == 1
    assert candidate["pipes"] == 2
    assert candidate["pipeLengths"] == [3, 4]
    assert candidate["comparisonWithParent"]["scorePercent"] == 0


def test_benchmark_rejects_an_unparseable_exact_file(tmp_path):
    invalid = tmp_path / "invalid.man"
    invalid.write_text("not a machine\n")
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "max-element", str(invalid)],
        cwd=REPO,
        check=False,
        text=True,
        capture_output=True,
    )
    assert completed.returncode != 0
    result = json.loads(completed.stdout)
    candidate = result["candidates"][0]
    assert candidate["path"] == str(invalid)
    assert candidate["casesPassed"] < candidate["casesTotal"]


def test_benchmark_rejects_a_server_invalid_one_cell_pipe():
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "reverse-a-list",
            "submissions/reverse-a-list/reverse_02.man",
        ],
        cwd=REPO,
        check=False,
        text=True,
        capture_output=True,
    )
    assert completed.returncode == 2
    assert "shorter than 2 cells" in completed.stderr
