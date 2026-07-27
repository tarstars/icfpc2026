"""Verify the compact multi-round Reverse fresh-farm candidate.

Correctness is checked with the organizers' vendored WASM because the base
Python simulator may not model the mid-contest Y instruction fully.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ARTIFACT = HERE / "reverse_fresh_23.man"
GENERATOR = HERE / "build_candidate.py"
PROBLEM = ROOT / "data/small/problems/reverse-a-list.json"


def run_generator() -> str:
    proc = subprocess.run(
        [sys.executable, str(GENERATOR)],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        text=True,
        capture_output=True,
        check=True,
    )
    return proc.stdout


def run_case(case: dict) -> int:
    inputs = [[int(x) for x in rnd["in"]] for rnd in case["rounds"]]
    expected = [[int(x) for x in rnd["out"]] for rnd in case["rounds"]]
    request = {
        "programPath": str(ARTIFACT),
        "input": inputs,
        "expected": expected,
        "maxTicks": 5000,
    }
    result = subprocess.run(
        ["node", str(HERE / "run_until_expected.mjs")],
        input=json.dumps(request),
        text=True,
        capture_output=True,
        check=True,
    )
    parsed = json.loads(result.stdout)
    flat = [str(x) for rnd in expected for x in rnd]
    if parsed["output"] != flat:
        raise AssertionError((case["name"], parsed["output"], flat))
    return int(parsed["ticks"])


def main() -> None:
    generated = run_generator()
    text = ARTIFACT.read_text()
    if generated != text:
        raise AssertionError("generator output differs from committed artifact")

    lines = text.rstrip("\n").split("\n")
    width, height = max(map(len, lines)), len(lines)
    if (width, height) != (23, 23):
        raise AssertionError((width, height))

    problem = json.loads(PROBLEM.read_text())
    ticks = [run_case(case) for case in problem["publicTestData"]]
    average = sum(ticks) / len(ticks)
    score = max(width, height) ** 2 * average
    result = {
        "sha256": hashlib.sha256(text.encode()).hexdigest(),
        "width": width,
        "height": height,
        "caseTicks": ticks,
        "averageTicks": average,
        "score": score,
        "casesPassed": len(ticks),
    }
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
