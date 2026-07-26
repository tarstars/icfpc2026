"""Fine-grained parallel judge search for safe Subset Sum squeeze deletions.

Search partition (coordinated with Alexey):
  * exactly 32 contiguous row groups
  * exactly 64 contiguous column groups

Independent group tests use four worker processes. Passing groups are then
added to a serialized, always-passing union using recursive batch addition.
"""
from __future__ import annotations

import hashlib
import json
import math
import multiprocessing as mp
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

from littleman.judge import judge_problem
from littleman.server_compat import validate_layout
from littleman.sim import Machine
from littleman.subset_sum import build_subset_sum

PROBLEM = json.loads((ROOT / "data/small/problems/subset-sum.json").read_text())
ORIGINAL = build_subset_sum()
RAW_LINES = ORIGINAL.rstrip("\n").split("\n")
WIDTH = max(map(len, RAW_LINES))
GRID = [line.ljust(WIDTH) for line in RAW_LINES]
HEIGHT = len(GRID)
DELETABLE_ROWS = [r for r in range(HEIGHT) if all(ch in " |" for ch in GRID[r])]
DELETABLE_COLS = [c for c in range(WIDTH) if all(row[c] in " -" for row in GRID)]

CHECKPOINT = HERE / "fine_group_results.json"
TRACE = HERE / "union_trace.json"
RESULT = HERE / "fine_bisect_result.json"
CANDIDATE = HERE / "ss_fine_bisect.man"


def balanced_groups(seq: list[int], count: int) -> list[list[int]]:
    """Split into exactly count nonempty contiguous groups."""
    if count < 1 or count > len(seq):
        raise ValueError((len(seq), count))
    q, r = divmod(len(seq), count)
    out = []
    pos = 0
    for index in range(count):
        size = q + (1 if index < r else 0)
        out.append(seq[pos : pos + size])
        pos += size
    assert pos == len(seq)
    assert len(out) == count and all(out)
    return out


ROW_GROUPS = balanced_groups(DELETABLE_ROWS, 32)
COL_GROUPS = balanced_groups(DELETABLE_COLS, 64)


def build(rows: list[int] | tuple[int, ...], cols: list[int] | tuple[int, ...]) -> str:
    row_set, col_set = set(rows), set(cols)
    return "\n".join(
        "".join(row[c] for c in range(WIDTH) if c not in col_set).rstrip()
        for r, row in enumerate(GRID)
        if r not in row_set
    ) + "\n"


def finite_score(value: float | None) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return value


def evaluate(rows: list[int], cols: list[int], tag: str) -> dict[str, Any]:
    started = time.time()
    text = build(rows, cols)
    try:
        report = judge_problem(text, PROBLEM)
        passed = report.cases_passed == report.cases_total
        return {
            "tag": tag,
            "passed": passed,
            "cases_passed": report.cases_passed,
            "cases_total": report.cases_total,
            "case_ticks": report.case_ticks,
            "failures": [case.reason for case in report.case_results if not case.passed],
            "footprint": report.footprint,
            "score": finite_score(report.score),
            "rows_deleted": len(rows),
            "cols_deleted": len(cols),
            "wall_s": round(time.time() - started, 3),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "tag": tag,
            "passed": False,
            "cases_passed": 0,
            "cases_total": len(PROBLEM["publicTestData"]),
            "case_ticks": [],
            "failures": [f"{type(exc).__name__}: {exc}"],
            "footprint": None,
            "score": None,
            "rows_deleted": len(rows),
            "cols_deleted": len(cols),
            "wall_s": round(time.time() - started, 3),
        }


def worker(spec: tuple[str, int, list[int]]) -> dict[str, Any]:
    kind, index, group = spec
    rows, cols = (group, []) if kind == "row" else ([], group)
    result = evaluate(rows, cols, f"{kind}-{index:03d}")
    result.update(
        {
            "kind": kind,
            "index": index,
            "start": group[0],
            "end": group[-1],
            "line_count": len(group),
            "pid": os.getpid(),
        }
    )
    return result


def write_json(path: Path, value: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=1, sort_keys=True))
    tmp.replace(path)


def group_key(kind: str, index: int) -> str:
    return f"{kind}-{index:03d}"


def run_groups(max_workers: int = 4) -> list[dict[str, Any]]:
    previous: dict[str, dict[str, Any]] = {}
    if CHECKPOINT.exists():
        for item in json.loads(CHECKPOINT.read_text()):
            previous[item["tag"]] = item

    specs = [
        ("row", index, group) for index, group in enumerate(ROW_GROUPS)
    ] + [
        ("col", index, group) for index, group in enumerate(COL_GROUPS)
    ]
    todo = [spec for spec in specs if group_key(spec[0], spec[1]) not in previous]
    results = dict(previous)
    print(
        f"groups: rows={len(ROW_GROUPS)} cols={len(COL_GROUPS)} "
        f"cached={len(previous)} todo={len(todo)} workers={max_workers}",
        flush=True,
    )
    if todo:
        context = mp.get_context("fork")
        with ProcessPoolExecutor(max_workers=max_workers, mp_context=context) as pool:
            futures = {pool.submit(worker, spec): spec for spec in todo}
            for future in as_completed(futures):
                item = future.result()
                results[item["tag"]] = item
                ordered = [results[key] for key in sorted(results)]
                write_json(CHECKPOINT, ordered)
                print(
                    f"[{len(results):03d}/096] {item['tag']} "
                    f"{item['cases_passed']}/{item['cases_total']} "
                    f"fp={item['footprint']} wall={item['wall_s']}s",
                    flush=True,
                )
    return [results[key] for key in sorted(results)]


def flatten(groups: list[tuple[str, int, list[int]]]) -> tuple[list[int], list[int]]:
    rows: list[int] = []
    cols: list[int] = []
    for kind, _index, group in groups:
        (rows if kind == "row" else cols).extend(group)
    return sorted(rows), sorted(cols)


def recursive_add(
    current: list[tuple[str, int, list[int]]],
    batch: list[tuple[str, int, list[int]]],
    trace: list[dict[str, Any]],
) -> list[tuple[str, int, list[int]]]:
    """Add the largest safe batches; final current always passes."""
    if not batch:
        return current
    rows, cols = flatten(current + batch)
    tag = "union+" + ",".join(group_key(k, i) for k, i, _ in batch)
    result = evaluate(rows, cols, tag)
    trace.append(
        {
            "attempted_groups": [group_key(k, i) for k, i, _ in batch],
            **result,
        }
    )
    write_json(TRACE, trace)
    print(
        f"[{tag[:90]}] {result['cases_passed']}/{result['cases_total']} "
        f"rows={len(rows)} cols={len(cols)} fp={result['footprint']} "
        f"wall={result['wall_s']}s",
        flush=True,
    )
    if result["passed"]:
        return current + batch
    if len(batch) == 1:
        return current
    middle = len(batch) // 2
    current = recursive_add(current, batch[:middle], trace)
    return recursive_add(current, batch[middle:], trace)


def logical_binding_summary(candidate: str) -> dict[str, Any]:
    """Compare resolved logical source/destination pairs at every pipe op."""
    operations = "sSrRUq"

    class Probe:
        pass

    def collect(text: str):
        machine = Machine.parse(text)
        room_index = {id(room): i for i, room in enumerate(machine.rooms)}
        pipe_key = {
            id(pipe): (room_index[id(pipe.source)], room_index[id(pipe.dest)])
            for pipe in machine.pipes
        }
        duplicate_pairs: dict[tuple[int, int], int] = {}
        for key in pipe_key.values():
            duplicate_pairs[key] = duplicate_pairs.get(key, 0) + 1
        rows = []
        for room_i, room in enumerate(machine.rooms):
            op_i = 0
            incoming = sorted(
                machine.in_pipes.get(id(room), []), key=lambda p: p.cells[-1]
            )
            outgoing = sorted(
                machine.out_pipes.get(id(room), []), key=lambda p: p.cells[0]
            )
            for row in range(room.top + 1, room.bottom):
                for col in range(room.left + 1, room.right):
                    char = machine.grid[row][col]
                    if char not in operations:
                        continue
                    probe = Probe()
                    probe.r, probe.c, probe.room = row, col, room
                    if char == "s":
                        selected = (pipe_key[id(machine._nearest_outgoing(probe))],)
                    elif char in "rq":
                        selected = (pipe_key[id(machine._nearest_incoming(probe))],)
                    elif char == "S":
                        selected = tuple(pipe_key[id(pipe)] for pipe in outgoing)
                    else:
                        selected = tuple(pipe_key[id(pipe)] for pipe in incoming)
                    rows.append((room_i, op_i, char, selected))
                    op_i += 1
        return machine, rows, duplicate_pairs

    before, old, old_pairs = collect(ORIGINAL)
    after, new, new_pairs = collect(candidate)
    diffs = [
        {"before": left, "after": right}
        for left, right in zip(old, new)
        if left != right
    ]
    return {
        "structure_before": [len(before.rooms), len(before.pipes), len(before.men)],
        "structure_after": [len(after.rooms), len(after.pipes), len(after.men)],
        "duplicate_pairs_before": sum(1 for v in old_pairs.values() if v > 1),
        "duplicate_pairs_after": sum(1 for v in new_pairs.values() if v > 1),
        "pipe_ops_before": len(old),
        "pipe_ops_after": len(new),
        "binding_diffs_count": len(diffs),
        "binding_diffs_first100": diffs[:100],
    }


def main() -> None:
    started = time.time()
    print(
        f"deletable rows={len(DELETABLE_ROWS)} cols={len(DELETABLE_COLS)}; "
        f"exact groups={len(ROW_GROUPS)}/{len(COL_GROUPS)}",
        flush=True,
    )
    baseline = evaluate([], [], "baseline")
    print("baseline", json.dumps(baseline, sort_keys=True), flush=True)
    if not baseline["passed"]:
        raise SystemExit("regenerated baseline did not pass")

    group_results = run_groups(max_workers=4)
    passing = []
    by_tag = {item["tag"]: item for item in group_results}
    for kind, source in (("col", COL_GROUPS), ("row", ROW_GROUPS)):
        for index, group in enumerate(source):
            if by_tag[group_key(kind, index)]["passed"]:
                passing.append((kind, index, group))

    passing.sort(key=lambda item: (0 if item[0] == "col" else 1, item[1]))
    trace: list[dict[str, Any]] = []
    retained = recursive_add([], passing, trace)
    rows, cols = flatten(retained)
    final = evaluate(rows, cols, "final")
    candidate = build(rows, cols)

    try:
        validate_layout(candidate)
        machine = Machine.parse(candidate)
        structural: dict[str, Any] = {
            "server_layout": "pass",
            "rooms": len(machine.rooms),
            "pipes": len(machine.pipes),
            "men": len(machine.men),
            "min_pipe": min(len(pipe.cells) for pipe in machine.pipes),
        }
    except Exception as exc:  # noqa: BLE001
        structural = {"server_layout": f"fail: {type(exc).__name__}: {exc}"}

    binding = logical_binding_summary(candidate)
    sha256 = hashlib.sha256(candidate.encode()).hexdigest()
    result = {
        "schema_version": 1,
        "baseline": baseline,
        "group_count": {"rows": len(ROW_GROUPS), "cols": len(COL_GROUPS)},
        "passing_groups": sum(1 for item in group_results if item["passed"]),
        "retained_group_tags": [group_key(k, i) for k, i, _ in retained],
        "rows": rows,
        "cols": cols,
        "rows_deleted": len(rows),
        "cols_deleted": len(cols),
        "final": final,
        "structural": structural,
        "binding": binding,
        "sha256": sha256,
        "candidate_bytes": len(candidate.encode()),
        "wall_s": round(time.time() - started, 3),
    }
    write_json(RESULT, result)
    if (
        final["passed"]
        and final["score"] is not None
        and baseline["score"] is not None
        and final["score"] < baseline["score"]
        and structural.get("server_layout") == "pass"
        and binding["binding_diffs_count"] == 0
    ):
        CANDIDATE.write_text(candidate)
        print("written passing candidate", CANDIDATE, sha256, flush=True)
    else:
        print("no promotion-safe candidate; result JSON written", flush=True)
    print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
