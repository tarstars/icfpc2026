"""Reproduce and verify the solver-derived 21-square Reverse candidate."""
from __future__ import annotations

import hashlib
import json
import os
import random
import subprocess
import sys
from pathlib import Path

from littleman.server_compat import validate_layout
from littleman.sim import Machine

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ARTIFACT = HERE / "reverse_fresh_21.man"
GENERATOR = HERE / "build_w16_candidate.py"
PROBLEM_PATH = ROOT / "data/small/problems/reverse-a-list.json"
EXPECTED_SHA256 = "08644876ec857c0c5c227fc0c98024fb00a5adf2a6558d4019bdbc743befb696"
EXPECTED_PUBLIC_TICKS = [139, 82, 128, 202, 114, 118, 244, 384]


def run_generator() -> str:
    result = subprocess.run(
        [sys.executable, str(GENERATOR)],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout


def build_stress_cases() -> list[dict]:
    rng = random.Random(20260727)
    cases: list[dict] = []

    def add(name: str, lengths: list[int], mode: str = "random") -> None:
        inputs: list[list[int]] = []
        expected: list[list[int]] = []
        for round_index, length in enumerate(lengths):
            if mode == "extreme":
                values = [
                    -1_000_000 if index % 3 == 0 else 1_000_000 if index % 3 == 1 else 0
                    for index in range(length)
                ]
            elif mode == "index":
                values = [round_index * 1000 + index for index in range(length)]
            else:
                values = [rng.randint(-1_000_000, 1_000_000) for _ in range(length)]
            inputs.append([length, *values])
            expected.append(list(reversed(values)))
        cases.append({"name": name, "input": inputs, "expected": expected})

    for length in range(1, 17):
        add(f"single-{length}", [length], "index")
    add("ascending", list(range(1, 17)), "index")
    add("descending", list(range(16, 0, -1)), "index")
    add("alternating", [1, 16] * 8, "extreme")
    add("all16", [16] * 16)
    add("all1", [1] * 32)
    for first in range(1, 17):
        for second in range(1, 17):
            add(f"pair-{first}-{second}", [first, second], "index")
    for index in range(500):
        add(
            f"random-{index}",
            [rng.randint(1, 16) for _ in range(rng.randint(1, 3))],
        )
    return cases


def run_wasm(cases: list[dict], max_ticks: int = 10_000) -> list[dict]:
    request = {
        "programPath": str(ARTIFACT),
        "cases": cases,
        "maxTicks": max_ticks,
    }
    result = subprocess.run(
        ["node", str(HERE / "run_batch.mjs")],
        cwd=ROOT,
        input=json.dumps(request),
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def main() -> None:
    text = ARTIFACT.read_text()
    if run_generator() != text:
        raise AssertionError("generator output differs from committed artifact")
    sha256 = hashlib.sha256(text.encode()).hexdigest()
    if sha256 != EXPECTED_SHA256:
        raise AssertionError((sha256, EXPECTED_SHA256))

    lines = text.rstrip("\n").split("\n")
    dimensions = (max(map(len, lines)), len(lines))
    if dimensions != (21, 18):
        raise AssertionError(dimensions)

    validate_layout(text)
    machine = Machine.parse(text)
    if (len(machine.rooms), len(machine.pipes), len(machine.men)) != (3, 2, 1):
        raise AssertionError((len(machine.rooms), len(machine.pipes), len(machine.men)))
    pipe_lengths = sorted(len(pipe.cells) for pipe in machine.pipes)
    if pipe_lengths != [2, 3]:
        raise AssertionError(pipe_lengths)

    problem = json.loads(PROBLEM_PATH.read_text())
    public_cases = []
    for test_case in problem["publicTestData"]:
        public_cases.append(
            {
                "name": test_case["name"],
                "input": [[int(value) for value in rnd["in"]] for rnd in test_case["rounds"]],
                "expected": [[int(value) for value in rnd["out"]] for rnd in test_case["rounds"]],
            }
        )
    public_results = run_wasm(public_cases, max_ticks=5_000)
    if any(not item["good"] or item["fatal"] for item in public_results):
        raise AssertionError(public_results)
    public_ticks = [item["ticks"] for item in public_results]
    if public_ticks != EXPECTED_PUBLIC_TICKS:
        raise AssertionError((public_ticks, EXPECTED_PUBLIC_TICKS))

    stress_results = run_wasm(build_stress_cases())
    bad = [item for item in stress_results if not item["good"] or item["fatal"]]
    if bad:
        raise AssertionError(bad[:3])

    average_ticks = sum(public_ticks) / len(public_ticks)
    score = max(dimensions) ** 2 * average_ticks
    print(
        json.dumps(
            {
                "sha256": sha256,
                "dimensions": dimensions,
                "pipeLengths": pipe_lengths,
                "publicTicks": public_ticks,
                "averageTicks": average_ticks,
                "score": score,
                "stressCases": len(stress_results),
                "stressMaximumTicks": max(item["ticks"] for item in stress_results),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
