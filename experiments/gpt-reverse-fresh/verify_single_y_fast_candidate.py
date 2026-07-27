"""Reproduce and verify the faster 20-square single-Y Reverse candidate."""
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
ARTIFACT = HERE / "reverse_fresh_20_fast.man"
GENERATOR = HERE / "build_single_y_fast_candidate.py"
PROBLEM_PATH = ROOT / "data/small/problems/reverse-a-list.json"
EXPECTED_SHA256 = "f36477129f496a499cd0d594b3a30a1f560f82aae2eaefee639426c042fb01e8"
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


def add_case(cases, rng, name, lengths, mode="random"):
    inputs, expected = [], []
    for round_index, length in enumerate(lengths):
        if mode == "index":
            values = [round_index * 1000 + index for index in range(length)]
        elif mode == "extreme":
            values = [
                -1_000_000 if index % 3 == 0 else 1_000_000 if index % 3 == 1 else 0
                for index in range(length)
            ]
        else:
            values = [rng.randint(-1_000_000, 1_000_000) for _ in range(length)]
        inputs.append([length, *values])
        expected.append(list(reversed(values)))
    cases.append({"name": name, "input": inputs, "expected": expected})


def build_stress_cases():
    rng = random.Random(2026072702)
    cases = []
    for length in range(1, 17):
        add_case(cases, rng, f"single-{length}", [length], "index")
    add_case(cases, rng, "ascending", list(range(1, 17)), "index")
    add_case(cases, rng, "descending", list(range(16, 0, -1)), "index")
    add_case(cases, rng, "alternating", [1, 16] * 16, "extreme")
    add_case(cases, rng, "all16", [16] * 32)
    add_case(cases, rng, "all1", [1] * 64)
    for first in range(1, 17):
        for second in range(1, 17):
            add_case(cases, rng, f"pair-{first}-{second}", [first, second], "index")
    for index in range(1000):
        add_case(
            cases,
            rng,
            f"random-{index}",
            [rng.randint(1, 16) for _ in range(rng.randint(1, 5))],
        )
    return cases


def run_wasm(cases, max_ticks=20_000):
    request = {"programPath": str(ARTIFACT), "cases": cases, "maxTicks": max_ticks}
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
    if dimensions != (20, 18):
        raise AssertionError(dimensions)

    validate_layout(text)
    machine = Machine.parse(text)
    if (len(machine.rooms), len(machine.pipes), len(machine.men)) != (3, 2, 1):
        raise AssertionError((len(machine.rooms), len(machine.pipes), len(machine.men)))
    pipe_lengths = sorted(len(pipe.cells) for pipe in machine.pipes)
    if pipe_lengths != [2, 3]:
        raise AssertionError(pipe_lengths)

    problem = json.loads(PROBLEM_PATH.read_text())
    public_cases = [
        {
            "name": test_case["name"],
            "input": [[int(value) for value in rnd["in"]] for rnd in test_case["rounds"]],
            "expected": [[int(value) for value in rnd["out"]] for rnd in test_case["rounds"]],
        }
        for test_case in problem["publicTestData"]
    ]
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
