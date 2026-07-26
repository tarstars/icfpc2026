"""Whole-state differential tests for the PyO3/Rust executor."""

from __future__ import annotations

import json
import pathlib

import pytest

from littleman import fastsim, judge, rustexec, sim

REPO = pathlib.Path(__file__).resolve().parent.parent
PROBLEMS = REPO / "data" / "small" / "problems"
SLUG = {
    "atoi": "atoi",
    "brackets": "brackets",
    "gradebook": "gradebook",
    "hello-world": "hello-world",
    "history": "history-lesson",
    "lllm": "little-little-little-man",
    "llm": "little-little-man",
    "matmul": "matmul",
    "max-element": "max-element",
    "memory": "memory",
    "palette": "palette",
    "plotter": "plotter",
    "reverse-a-list": "reverse-a-list",
    "snake": "snake",
    "sort": "sort-numbers",
    "subset-sum": "subset-sum",
    "sudoku-validity": "sudoku-validity",
    "tcp": "tcp",
    "triangle": "triangle",
}
ARTIFACTS = []
for artifact in sorted((REPO / "submissions").rglob("*.man")):
    problem_slug = SLUG.get(artifact.parent.name) or SLUG.get(artifact.parent.parent.name)
    if problem_slug is not None:
        ARTIFACTS.append((artifact, problem_slug))


def snapshot(machine, result):
    return {
        "status": result.status,
        "error": result.error,
        "ticks": result.ticks,
        "output": list(result.output),
        "output_ticks": list(result.output_ticks),
        "frames": [[list(row) for row in frame] for frame in result.frames],
        "frame_ticks": list(result.frame_ticks),
        "men": [
            (m.r, m.c, m.direction, m.A, m.B, m.BP, m.halted, m.blocked)
            for m in machine.men
        ],
        "pipes": [list(pipe.values) for pipe in machine.pipes],
        "displays": [
            (
                display.cursor,
                [list(row) for row in display.current],
                [list(row) for row in display.next],
            )
            for display in machine.displays
        ],
    }


def run(module, text, *, rounds=None, inputs=None, cap=30_000):
    machine = module.Machine.parse(text)
    controller = judge.RoundController(rounds) if rounds is not None else None
    result = machine.run(inputs=inputs, max_ticks=cap, controller=controller)
    return snapshot(machine, result)


def assert_same(text, *, rounds=None, inputs=None, cap=30_000, label="case"):
    expected = run(sim, text, rounds=rounds, inputs=inputs, cap=cap)
    actual = run(rustexec, text, rounds=rounds, inputs=inputs, cap=cap)
    for field in expected:
        assert actual[field] == expected[field], (
            f"Rust divergence on {label}: {field}; "
            f"reference ticks={expected['ticks']}, Rust ticks={actual['ticks']}"
        )


def test_native_backend_is_loaded():
    assert rustexec.HAVE_RUST
    assert rustexec.backend() == "rust"


def test_ir_version_is_fail_closed():
    machine = sim.Machine.parse((REPO / "submissions/max-element/max_00.man").read_text())
    spec = fastsim.build_spec(fastsim.compile_machine(machine))
    spec["ir_version"] = 2
    with pytest.raises(ValueError, match="unsupported IR version 2"):
        rustexec._rust.run(spec, None, None, [], 1)


@pytest.mark.parametrize(
    "path,slug",
    ARTIFACTS,
    ids=[f"{path.parent.name}/{path.name}" for path, _ in ARTIFACTS],
)
def test_every_submission_prefix_matches_reference(path, slug):
    """Every preserved artifact and public case, bounded but whole-state."""
    text = path.read_text()
    try:
        sim.Machine.parse(text)
    except sim.LoadError:
        pytest.skip("artifact is an intentionally unloadable experiment")
    problem = json.loads((PROBLEMS / f"{slug}.json").read_text())
    cap = min(problem.get("tickCap") or 5_000_000, 10_000)
    for case in problem["publicTestData"]:
        assert_same(
            text,
            rounds=judge.normalize_case(case),
            cap=cap,
            label=f"{path.name}::{case['name']}",
        )


@pytest.mark.parametrize(
    "relative,slug,case_index,cap",
    [
        ("max-element/max_00.man", "max-element", 0, 10_000),
        ("reverse-a-list/reverse_01.man", "reverse-a-list", 7, 20_000),
        ("llm/llm_codex_01.man", "little-little-man", 0, 300_000),
    ],
)
def test_completed_representative_cases(relative, slug, case_index, cap):
    text = (REPO / "submissions" / relative).read_text()
    problem = json.loads((PROBLEMS / f"{slug}.json").read_text())
    case = problem["publicTestData"][case_index]
    assert_same(
        text,
        rounds=judge.normalize_case(case),
        cap=cap,
        label=f"completed {relative}::{case['name']}",
    )
