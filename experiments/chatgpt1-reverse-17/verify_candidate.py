#!/usr/bin/env python3
"""Release checks for ``chatgpt1_reverse_09``.

The ordinary Python simulator does not implement ``Y``.  Functional checks in
this file therefore run the organizers' vendored WASM through the already
integrated ``run_batch.mjs`` harness.  Static parser and server-layout checks
are still useful and run first.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import random
import subprocess
import sys
from pathlib import Path
from typing import Any

from littleman.alexey_pipecheck import check as check_pipe_lengths
from littleman.server_compat import validate_layout
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
ARTIFACT = ROOT / "submissions" / "reverse-a-list" / "chatgpt1_reverse_09.man"
GENERATOR = HERE / "build_candidate.py"
RUN_BATCH = ROOT / "experiments" / "gpt-reverse-fresh" / "run_batch.mjs"
PROBLEM = ROOT / "data" / "small" / "problems" / "reverse-a-list.json"
EXPECTED_SHA256 = "aa057e97bb3335be37bc49fc652e7f966e8281af9f7ae61dde59035789f87a41"
MODEL_PUBLIC_TICKS = [142, 82, 127, 202, 114, 124, 243, 382]
ACCEPTED_PUBLIC_SCORE = 53_023.75


def _load_builder():
    spec = importlib.util.spec_from_file_location("chatgpt1_reverse17_builder", GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def geometry(text: str) -> tuple[int, int]:
    lines = text.rstrip("\n").splitlines()
    return max(map(len, lines), default=0), len(lines)


def _public_cases() -> list[dict[str, Any]]:
    spec = json.loads(PROBLEM.read_text())
    cases: list[dict[str, Any]] = []
    for test_case in spec["publicTestData"]:
        rounds = test_case.get("rounds") or [
            {"in": test_case.get("in", []), "out": test_case.get("out", [])}
        ]
        cases.append(
            {
                "name": test_case["name"],
                "input": [[int(value) for value in round_["in"]] for round_ in rounds],
                "expected": [
                    [int(value) for value in round_["out"]] for round_ in rounds
                ],
            }
        )
    return cases


def _append_case(
    cases: list[dict[str, Any]],
    *,
    name: str,
    lengths: list[int],
    rng: random.Random,
    mode: str = "random",
) -> None:
    inputs: list[list[int]] = []
    expected: list[list[int]] = []
    for round_index, length in enumerate(lengths):
        if mode == "index":
            values = [round_index * 10_000 + index - 500 for index in range(length)]
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


def _stress_cases() -> list[dict[str, Any]]:
    rng = random.Random(2026072709)
    cases: list[dict[str, Any]] = []

    for length in range(1, 17):
        _append_case(cases, name=f"single-{length}", lengths=[length], rng=rng, mode="index")
    for first in range(1, 17):
        for second in range(1, 17):
            _append_case(
                cases,
                name=f"pair-{first}-{second}",
                lengths=[first, second],
                rng=rng,
                mode="index",
            )

    for name, lengths, mode in (
        ("ascending", [1, 8, 16], "index"),
        ("descending", [16, 8, 1], "index"),
        ("alternating", [1, 16, 1], "extreme"),
        ("full-three", [16, 16, 16], "extreme"),
        ("singletons", [1, 1, 1], "extreme"),
    ):
        _append_case(cases, name=name, lengths=lengths, rng=rng, mode=mode)

    for index in range(1_000):
        lengths = [rng.randint(1, 16) for _ in range(rng.randint(1, 3))]
        _append_case(cases, name=f"random-{index}", lengths=lengths, rng=rng)
    return cases


def _run_batch(cases: list[dict[str, Any]], max_ticks: int) -> list[dict[str, Any]]:
    request = {
        "programPath": str(ARTIFACT),
        "cases": cases,
        "maxTicks": max_ticks,
    }
    proc = subprocess.run(
        ["node", str(RUN_BATCH)],
        cwd=ROOT,
        env={**os.environ},
        input=json.dumps(request),
        text=True,
        capture_output=True,
        timeout=600,
        check=True,
    )
    return json.loads(proc.stdout)


def main() -> int:
    text = ARTIFACT.read_text()
    generated = _load_builder().build()
    if generated != text:
        raise AssertionError("generator output differs from immutable artifact")

    sha256 = hashlib.sha256(text.encode()).hexdigest()
    if sha256 != EXPECTED_SHA256:
        raise AssertionError((sha256, EXPECTED_SHA256))
    if geometry(text) != (17, 17):
        raise AssertionError(geometry(text))

    machine = Machine.parse(text)
    structure = (len(machine.rooms), len(machine.pipes), len(machine.men))
    if structure != (3, 2, 1):
        raise AssertionError(structure)
    pipe_lengths = sorted(len(pipe.cells) for pipe in machine.pipes)
    if pipe_lengths != [2, 3]:
        raise AssertionError(pipe_lengths)
    check_pipe_lengths(text)
    validate_layout(text)

    public_results = _run_batch(_public_cases(), max_ticks=20_000)
    bad_public = [
        item for item in public_results if not item.get("good") or item.get("fatal")
    ]
    if bad_public:
        raise AssertionError(bad_public)
    public_ticks = [int(item["ticks"]) for item in public_results]
    average_ticks = sum(public_ticks) / len(public_ticks)
    public_score = 17 * 17 * average_ticks
    if public_score >= ACCEPTED_PUBLIC_SCORE:
        raise AssertionError(
            f"candidate passes but loses: {public_score} >= {ACCEPTED_PUBLIC_SCORE}"
        )

    stress_results = _run_batch(_stress_cases(), max_ticks=20_000)
    bad_stress = [
        item for item in stress_results if not item.get("good") or item.get("fatal")
    ]
    if bad_stress:
        raise AssertionError(bad_stress[:5])

    evidence = {
        "sha256": sha256,
        "dimensions": [17, 17],
        "structure": {"rooms": 3, "pipes": 2, "initialMen": 1},
        "pipeLengths": pipe_lengths,
        "publicTicks": public_ticks,
        "modelPublicTicks": MODEL_PUBLIC_TICKS,
        "modelTicksExact": public_ticks == MODEL_PUBLIC_TICKS,
        "averageTicks": average_ticks,
        "publicScore": public_score,
        "acceptedPublicScore": ACCEPTED_PUBLIC_SCORE,
        "scoreRatio": public_score / ACCEPTED_PUBLIC_SCORE,
        "stressCases": len(stress_results),
        "stressMaximumTicks": max(int(item["ticks"]) for item in stress_results),
    }
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
