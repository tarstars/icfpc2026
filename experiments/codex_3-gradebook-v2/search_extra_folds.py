#!/usr/bin/env python
"""Search extra staircase folds in the live codex_3 Grade Book machine.

This search starts from ``codex3_gradebook_06.man`` and changes only room
interiors. Room walls and every pipe glyph remain untouched. A successor is
rejected unless its outer dimensions, room geometry, pipe count, exact ordered
pipe-length tuple, and man count match the live baseline.

The search is deterministic. It beam-searches one additional ``merge_once`` at
a time in the parser and four subject engines, judges every structurally valid
successor on the seven public cases, and runs the first handoff's randomized
and ordered-transition stress suites on the best finalists.

Usage:

    uv run python experiments/codex_3-gradebook-v2/search_extra_folds.py

The script writes ``submissions/gradebook/codex3_gradebook_07.man`` only when a
strictly better public-score candidate survives every local gate. The final
submission decision still requires ``scripts/subdb.py compare`` and the
organizers' WASM.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pathlib
from dataclasses import dataclass
from typing import Any

from littleman import server_compat
from littleman.gradebook_components import _fold_room_prefix
from littleman.judge import footprint, judge_case, judge_problem
from littleman.sim import Machine

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASELINE_PATH = ROOT / "submissions" / "gradebook" / "codex3_gradebook_06.man"
PROBLEM_PATH = ROOT / "data" / "small" / "problems" / "gradebook.json"
STRESS_PATH = ROOT / "experiments" / "codex_3-gradebook" / "stress.py"
DEFAULT_OUTPUT = ROOT / "submissions" / "gradebook" / "codex3_gradebook_07.man"
DEFAULT_REPORT = ROOT / "experiments" / "codex_3-gradebook-v2" / "search-result.json"

# Current artifact room order: input, parser, subject engines 4,3,2,1, relays,
# collector, output. These are the five rooms folded by the live generator.
SEARCH_ROOMS = (1, 2, 3, 4, 5)


@dataclass(frozen=True)
class Structure:
    dimensions: tuple[int, int]
    footprint: int
    rooms: tuple[tuple[int, int, int, int, str], ...]
    pipe_lengths: tuple[int, ...]
    men: int


@dataclass(frozen=True)
class State:
    text: str
    vector: tuple[int, ...]
    score: float
    ticks: tuple[int, ...]
    sha256: str


def _dimensions(text: str) -> tuple[int, int]:
    occupied = [
        (row, col)
        for row, line in enumerate(text.splitlines())
        for col, char in enumerate(line)
        if char != " "
    ]
    if not occupied:
        return (0, 0)
    rows = [row for row, _ in occupied]
    cols = [col for _, col in occupied]
    return (max(cols) - min(cols) + 1, max(rows) - min(rows) + 1)


def _structure(text: str) -> Structure:
    machine = Machine.parse(text)
    return Structure(
        dimensions=_dimensions(text),
        footprint=footprint(text),
        rooms=tuple(
            (room.top, room.left, room.bottom, room.right, room.kind)
            for room in machine.rooms
        ),
        pipe_lengths=tuple(len(pipe.cells) for pipe in machine.pipes),
        men=len(machine.men),
    )


def _load_stress_module():
    spec = importlib.util.spec_from_file_location("codex3_gradebook_stress", STRESS_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load stress module: {STRESS_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _evaluate(
    text: str,
    *,
    baseline_structure: Structure,
    problem: dict[str, Any],
) -> State | None:
    try:
        structure = _structure(text)
        if structure != baseline_structure:
            return None
        server_compat.validate_layout(text)
        report = judge_problem(text, problem)
    except Exception:
        return None
    if report.cases_passed != report.cases_total or not report.case_ticks:
        return None
    return State(
        text=text,
        vector=(),
        score=float(report.score),
        ticks=tuple(int(tick) for tick in report.case_ticks),
        sha256=hashlib.sha256(text.encode()).hexdigest(),
    )


def _fold_once(text: str, room_index: int) -> str | None:
    try:
        return _fold_room_prefix(text, room_index, 1)
    except (ValueError, IndexError):
        return None


def _stress(text: str, *, random_start: int, random_count: int) -> dict[str, Any]:
    stress = _load_stress_module()
    random_rows = []
    for seed in range(random_start, random_start + random_count):
        result = judge_case(text, stress._random_case(seed), max_ticks=5_000_000)
        random_rows.append(
            {
                "seed": seed,
                "passed": bool(result.passed),
                "ticks": int(result.ticks),
                "reason": result.reason,
            }
        )
        if not result.passed:
            return {
                "passed": False,
                "random": random_rows,
                "transitions": [],
                "failure": f"random seed {seed}: {result.reason}",
            }

    transition_rows = []
    ordered_edges = 0
    for index, rounds in enumerate(stress._transition_cases()):
        result = judge_case(text, rounds, max_ticks=5_000_000)
        actions = sum(int(round_["in"][0]) for round_ in rounds[1:])
        ordered_edges += actions - 1
        transition_rows.append(
            {
                "chunk": index,
                "actions": actions,
                "passed": bool(result.passed),
                "ticks": int(result.ticks),
                "reason": result.reason,
            }
        )
        if not result.passed:
            return {
                "passed": False,
                "random": random_rows,
                "transitions": transition_rows,
                "ordered_edges": ordered_edges,
                "failure": f"transition chunk {index}: {result.reason}",
            }

    if ordered_edges != 256:
        raise AssertionError(f"stress harness covered {ordered_edges}, expected 256")
    return {
        "passed": True,
        "random": random_rows,
        "transitions": transition_rows,
        "ordered_edges": ordered_edges,
        "failure": None,
    }


def _state_row(state: State) -> dict[str, Any]:
    return {
        "vector": dict(zip(map(str, SEARCH_ROOMS), state.vector, strict=True)),
        "score": state.score,
        "ticks": list(state.ticks),
        "average_ticks": sum(state.ticks) / len(state.ticks),
        "sha256": state.sha256,
    }


def search(
    *,
    max_depth: int,
    beam_width: int,
    stress_finalists: int,
    random_start: int,
    random_count: int,
) -> tuple[State, State | None, dict[str, Any]]:
    baseline_text = BASELINE_PATH.read_text()
    problem = json.loads(PROBLEM_PATH.read_text())
    baseline_structure = _structure(baseline_text)
    baseline_eval = _evaluate(
        baseline_text,
        baseline_structure=baseline_structure,
        problem=problem,
    )
    if baseline_eval is None:
        raise RuntimeError("live baseline failed its own structural/public gate")
    baseline = State(
        text=baseline_eval.text,
        vector=(0,) * len(SEARCH_ROOMS),
        score=baseline_eval.score,
        ticks=baseline_eval.ticks,
        sha256=baseline_eval.sha256,
    )

    beam = [baseline]
    seen = {baseline.sha256}
    frontier_log: list[dict[str, Any]] = []
    all_passing: dict[str, State] = {baseline.sha256: baseline}

    for depth in range(1, max_depth + 1):
        successors: list[State] = []
        attempted = 0
        structural_rejects = 0
        judge_rejects = 0
        exhausted = 0
        for parent in beam:
            for position, room_index in enumerate(SEARCH_ROOMS):
                attempted += 1
                text = _fold_once(parent.text, room_index)
                if text is None:
                    exhausted += 1
                    continue
                digest = hashlib.sha256(text.encode()).hexdigest()
                if digest in seen:
                    continue
                seen.add(digest)
                try:
                    if _structure(text) != baseline_structure:
                        structural_rejects += 1
                        continue
                except Exception:
                    structural_rejects += 1
                    continue
                evaluated = _evaluate(
                    text,
                    baseline_structure=baseline_structure,
                    problem=problem,
                )
                if evaluated is None:
                    judge_rejects += 1
                    continue
                vector = list(parent.vector)
                vector[position] += 1
                state = State(
                    text=text,
                    vector=tuple(vector),
                    score=evaluated.score,
                    ticks=evaluated.ticks,
                    sha256=evaluated.sha256,
                )
                successors.append(state)
                all_passing[state.sha256] = state

        successors.sort(key=lambda state: (state.score, state.vector, state.sha256))
        beam = successors[:beam_width]
        frontier_log.append(
            {
                "depth": depth,
                "attempted": attempted,
                "exhausted": exhausted,
                "structural_rejects": structural_rejects,
                "judge_rejects": judge_rejects,
                "passing": len(successors),
                "beam": [_state_row(state) for state in beam],
            }
        )
        print(
            f"depth {depth:2d}: attempts={attempted:3d} pass={len(successors):3d} "
            f"best={(beam[0].score if beam else float('nan')):,.2f}"
        )
        if not beam:
            break

    ranked = sorted(
        (state for state in all_passing.values() if state.score < baseline.score),
        key=lambda state: (state.score, state.vector, state.sha256),
    )
    stress_log = []
    winner = None
    for state in ranked[:stress_finalists]:
        result = _stress(
            state.text,
            random_start=random_start,
            random_count=random_count,
        )
        stress_log.append({"candidate": _state_row(state), "stress": result})
        if result["passed"]:
            winner = state
            break

    report = {
        "baseline_path": str(BASELINE_PATH.relative_to(ROOT)),
        "baseline_structure": {
            "dimensions": list(baseline_structure.dimensions),
            "footprint": baseline_structure.footprint,
            "rooms": len(baseline_structure.rooms),
            "pipes": len(baseline_structure.pipe_lengths),
            "pipe_lengths": list(baseline_structure.pipe_lengths),
            "men": baseline_structure.men,
        },
        "baseline": _state_row(baseline),
        "parameters": {
            "search_rooms": list(SEARCH_ROOMS),
            "max_depth": max_depth,
            "beam_width": beam_width,
            "stress_finalists": stress_finalists,
            "random_start": random_start,
            "random_count": random_count,
        },
        "frontier": frontier_log,
        "passing_improvements": len(ranked),
        "stress": stress_log,
        "winner": _state_row(winner) if winner is not None else None,
    }
    return baseline, winner, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-depth", type=int, default=20)
    parser.add_argument("--beam-width", type=int, default=12)
    parser.add_argument("--stress-finalists", type=int, default=8)
    parser.add_argument("--random-start", type=int, default=100)
    parser.add_argument("--random-count", type=int, default=24)
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=pathlib.Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    if min(
        args.max_depth,
        args.beam_width,
        args.stress_finalists,
        args.random_count,
    ) < 1:
        parser.error("all search and stress counts must be positive")

    baseline, winner, report = search(
        max_depth=args.max_depth,
        beam_width=args.beam_width,
        stress_finalists=args.stress_finalists,
        random_start=args.random_start,
        random_count=args.random_count,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    print(f"baseline score: {baseline.score:,.2f}")
    if winner is None:
        print("no strict improvement survived public plus adversarial gates")
        print(f"report: {args.report}")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(winner.text)
    improvement = baseline.score / winner.score
    print(f"winner score : {winner.score:,.2f} ({improvement:.6f}x)")
    print(f"fold vector  : {dict(zip(SEARCH_ROOMS, winner.vector, strict=True))}")
    print(f"sha256       : {winner.sha256}")
    print(f"candidate    : {args.output}")
    print(f"report       : {args.report}")
    print()
    print("DECISIVE NEXT GATES:")
    print(f"uv run python scripts/subdb.py compare {args.output.relative_to(ROOT)} gradebook")
    print(f"uv run python scripts/wasm_judge.py {args.output.relative_to(ROOT)} gradebook")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
