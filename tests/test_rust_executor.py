"""Whole-state differential tests for the PyO3/Rust executor."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
from copy import deepcopy

import pytest

from littleman import fastsim, judge, rustexec, sim
from littleman.split_probe import YMachine

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
    problem_slug = SLUG.get(artifact.parent.name) or SLUG.get(
        artifact.parent.parent.name
    )
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


def test_backend_is_reported_and_plugin_updates_judge():
    expected = "rust" if rustexec.HAVE_RUST else "python-fallback"
    assert rustexec.backend() == expected
    if sim.Machine is rustexec.Machine:
        assert judge.Machine is rustexec.Machine


def test_missing_extension_falls_back_to_python():
    environment = os.environ.copy()
    environment["LITTLEMAN_RUSTEXEC"] = "0"
    code = """
import json
from pathlib import Path
from littleman import judge, rustexec

assert not rustexec.HAVE_RUST
assert rustexec.backend() == "python-fallback"
text = Path("submissions/max-element/max_00.man").read_text()
problem = json.loads(Path("data/small/problems/max-element.json").read_text())
rounds = judge.normalize_case(problem["publicTestData"][0])
cap = problem["tickCap"] or 5_000_000
compiled = rustexec.CompiledMachine(text)
result = compiled.run_rounds(0, rounds, cap)
assert result.status == "passed"
machine = rustexec.Machine.parse(text)
controller = judge.RoundController(rounds)
direct = machine.run(max_ticks=cap, controller=controller)
assert direct.status == "passed"
assert direct.ticks == result.ticks
"""
    process = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert process.returncode == 0, process.stderr


@pytest.mark.skipif(not rustexec.HAVE_RUST, reason="native IR API is not built")
def test_ir_version_is_fail_closed():
    machine = sim.Machine.parse(
        (REPO / "submissions/max-element/max_00.man").read_text()
    )
    spec = fastsim.build_spec(fastsim.compile_machine(machine))
    spec["ir_version"] = 2
    with pytest.raises(ValueError, match="unsupported IR version 2"):
        rustexec._rust.run(spec, None, None, [], 1)


@pytest.mark.skipif(not rustexec.HAVE_RUST, reason="native IR API is not built")
def test_malformed_ir_indices_and_shapes_fail_closed():
    machine = sim.Machine.parse(
        (REPO / "submissions/max-element/max_00.man").read_text()
    )
    base = fastsim.build_spec(fastsim.compile_machine(machine))
    malformed = []
    spec = deepcopy(base)
    spec["mcell"][0] = spec["n_cells"]
    malformed.append(spec)
    spec = deepcopy(base)
    spec["step"][0][0] = spec["n_cells"]
    malformed.append(spec)
    spec = deepcopy(base)
    spec["room_out_off"][-1] += 1
    malformed.append(spec)
    spec = deepcopy(base)
    spec["p_runs"][0] = [0]
    malformed.append(spec)
    spec = deepcopy(base)
    spec["input_pipe"] = len(spec["p_len"])
    malformed.append(spec)
    spec = deepcopy(base)
    spec["cellpos"][0] = spec["W"] * spec["H"]
    malformed.append(spec)
    for invalid in malformed:
        with pytest.raises(ValueError):
            rustexec._rust.run(invalid, None, None, [], 1)


def test_cached_parallel_batch_is_deterministic():
    text = (REPO / "submissions/max-element/max_00.man").read_text()
    problem = json.loads((PROBLEMS / "max-element.json").read_text())
    cases = [judge.normalize_case(case) for case in problem["publicTestData"]]
    compiled = rustexec.CompiledMachine(text)
    assert compiled.sha256 == __import__("hashlib").sha256(text.encode()).hexdigest()
    sequential = rustexec.run_rounds_parallel(
        compiled, cases, max_ticks=problem["tickCap"], workers=1
    )
    parallel = rustexec.run_rounds_parallel(
        compiled, cases, max_ticks=problem["tickCap"], workers=2
    )
    assert sequential == parallel
    assert all(result.status == "passed" for result in parallel)


def test_pytest_plugin_preserves_wall_tolerant_server_judge():
    from littleman import alexey_walljudge, server_compat

    assert alexey_walljudge.Machine is rustexec.ReferenceMachine
    source = (REPO / "submissions/triangle/triangle_04.man").read_text()
    problem = json.loads((PROBLEMS / "triangle.json").read_text())
    report = server_compat.judge_problem(source, problem)
    assert report.cases_passed == report.cases_total == 6
    assert report.case_ticks == [13] * 6


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


def bordered_room(rows):
    width = len(rows[0])
    assert all(len(row) == width for row in rows)
    return "\n".join(
        [
            "+" + "-" * width + "+",
            *("|" + row + "|" for row in rows),
            "+" + "-" * width + "+",
        ]
    )


def official_pair(
    rows, ticks, *, directions=None, registers=None, halted=None, cap=65_536
):
    if not rustexec.HAVE_RUST:
        pytest.skip("official Split executor requires the native extension")
    machine = sim.Machine.parse(bordered_room(rows))
    reference = YMachine(rows, cap=cap)
    directions = directions or [sim.RIGHT] * len(machine.men)
    registers = registers or [(0, 0, 0)] * len(machine.men)
    halted = halted or [False] * len(machine.men)
    assert len(machine.men) == len(reference.men) == len(directions)
    for index, (direction, values, is_halted) in enumerate(
        zip(directions, registers, halted)
    ):
        machine.men[index].direction = direction
        machine.men[index].A, machine.men[index].B, machine.men[index].BP = values
        machine.men[index].halted = is_halted
        reference.men[index].d = direction
        reference.men[index].A, reference.men[index].B, reference.men[index].BP = values
        reference.men[index].halted = is_halted
    actual = rustexec.run_official(machine, max_ticks=ticks, men_cap=cap)
    reference.run(ticks)
    direction_index = {sim.UP: 0, sim.RIGHT: 1, sim.DOWN: 2, sim.LEFT: 3}
    actual_live = []
    for cell, direction, a, b, bp, alive in zip(
        actual["mcell"],
        actual["mdir"],
        actual["mA"],
        actual["mB"],
        actual["mBP"],
        actual["malive"],
    ):
        if alive:
            row, column = divmod(actual["cellpos"][cell], len(rows[0]) + 2)
            actual_live.append((row - 1, column - 1, direction, a, b, bp))
    reference_live = [
        (man.r, man.c, direction_index[man.d], man.A, man.B, man.BP)
        for man in reference.live()
    ]
    return actual, reference, actual_live, reference_live


def test_split_birth_geometry_registers_and_creation_order():
    rows = ["       "] * 3 + ["  @Y   "] + ["       "] * 3
    actual, reference, actual_live, reference_live = official_pair(
        rows,
        2,
        registers=[(-(1 << 63), (1 << 63) - 1, -7)],
    )
    assert actual["error"] == reference.error is None
    assert actual_live == reference_live
    assert actual_live == [
        (4, 3, 2, -(1 << 63), (1 << 63) - 1, -7),
        (2, 3, 0, -(1 << 63), (1 << 63) - 1, -7),
    ]


@pytest.mark.parametrize(
    "rows,directions,halted",
    [
        (["     ", " @ @ ", "     "], [sim.RIGHT, sim.LEFT], [False, False]),
        (["     ", " @@  ", "     "], [sim.RIGHT, sim.LEFT], [False, False]),
        (["     ", " @@  ", "     "], [sim.RIGHT, sim.RIGHT], [False, True]),
    ],
    ids=["same-cell-arrival", "swap-through", "walking-onto-standing"],
)
def test_official_collision_modes_annihilate(rows, directions, halted):
    actual, reference, actual_live, reference_live = official_pair(
        rows, 1, directions=directions, halted=halted
    )
    assert actual["error"] == reference.error is None
    assert actual_live == reference_live == []


def test_split_wall_birth_is_an_error():
    rows = [" @Y  ", "     ", "     "]
    actual, reference, _, _ = official_pair(rows, 2)
    assert actual["status"] == "error"
    assert actual["error"] == reference.error == "wall-birth"


def test_split_birth_onto_halted_man_kills_both():
    rows = ["       ", "  @    ", " @Y    ", "       ", "       "]
    actual, reference, actual_live, reference_live = official_pair(
        rows,
        2,
        directions=[sim.RIGHT, sim.RIGHT],
        halted=[True, False],
    )
    assert actual["error"] == reference.error is None
    assert actual_live == reference_live
    assert len(actual_live) == 1
    assert actual_live[0][:3] == (3, 2, 2)


def test_two_splits_spawning_on_same_cell_annihilate_babies():
    rows = [" @   ", " Y   ", " @Y  ", "     ", "     "]
    actual, reference, actual_live, reference_live = official_pair(
        rows,
        2,
        directions=[sim.DOWN, sim.RIGHT],
    )
    assert actual["error"] == reference.error is None
    assert actual_live == reference_live
    assert [(row, column) for row, column, *_ in actual_live] == [(1, 0), (3, 2)]


def test_live_man_cap_is_fail_closed():
    rows = ["       ", "    @  ", " @Y    ", "       ", "       "]
    actual, reference, _, _ = official_pair(
        rows,
        2,
        directions=[sim.RIGHT, sim.RIGHT],
        halted=[True, False],
        cap=2,
    )
    assert actual["status"] == "error"
    assert actual["error"] == reference.error == "men-cap"
