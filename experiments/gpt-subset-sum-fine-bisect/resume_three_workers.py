"""Resume fine_bisect with three memory-safe workers and columns first."""
from __future__ import annotations

import json
import multiprocessing as mp
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import fine_bisect as m

BASELINE_CACHE = Path(__file__).with_name("baseline_result.json")


def run_groups() -> list[dict]:
    previous = {}
    if m.CHECKPOINT.exists():
        for item in json.loads(m.CHECKPOINT.read_text()):
            previous[item["tag"]] = item
    specs = [
        ("col", index, group) for index, group in enumerate(m.COL_GROUPS)
    ] + [
        ("row", index, group) for index, group in enumerate(m.ROW_GROUPS)
    ]
    todo = [
        spec for spec in specs
        if m.group_key(spec[0], spec[1]) not in previous
    ]
    results = dict(previous)
    print(
        f"resume: cached={len(previous)} todo={len(todo)} workers=3 "
        "order=columns-first",
        flush=True,
    )
    if todo:
        context = mp.get_context("fork")
        with ProcessPoolExecutor(max_workers=3, mp_context=context) as pool:
            futures = {pool.submit(m.worker, spec): spec for spec in todo}
            for future in as_completed(futures):
                item = future.result()
                results[item["tag"]] = item
                ordered = [results[key] for key in sorted(results)]
                m.write_json(m.CHECKPOINT, ordered)
                print(
                    f"[{len(results):03d}/096] {item['tag']} "
                    f"{item['cases_passed']}/{item['cases_total']} "
                    f"fp={item['footprint']} wall={item['wall_s']}s",
                    flush=True,
                )
    return [results[key] for key in sorted(results)]


def main() -> None:
    started = time.time()
    baseline = json.loads(BASELINE_CACHE.read_text())
    if not baseline["passed"]:
        raise SystemExit("cached baseline is not green")
    print("baseline cached", json.dumps(baseline, sort_keys=True), flush=True)

    group_results = run_groups()
    by_tag = {item["tag"]: item for item in group_results}
    passing = []
    for kind, source in (("col", m.COL_GROUPS), ("row", m.ROW_GROUPS)):
        for index, group in enumerate(source):
            if by_tag[m.group_key(kind, index)]["passed"]:
                passing.append((kind, index, group))
    passing.sort(key=lambda item: (0 if item[0] == "col" else 1, item[1]))

    trace = []
    retained = m.recursive_add([], passing, trace)
    rows, cols = m.flatten(retained)
    final = m.evaluate(rows, cols, "final")
    candidate = m.build(rows, cols)

    try:
        m.validate_layout(candidate)
        machine = m.Machine.parse(candidate)
        structural = {
            "server_layout": "pass",
            "rooms": len(machine.rooms),
            "pipes": len(machine.pipes),
            "men": len(machine.men),
            "min_pipe": min(len(pipe.cells) for pipe in machine.pipes),
        }
    except Exception as exc:  # noqa: BLE001
        structural = {"server_layout": f"fail: {type(exc).__name__}: {exc}"}

    binding = m.logical_binding_summary(candidate)
    sha256 = m.hashlib.sha256(candidate.encode()).hexdigest()
    result = {
        "schema_version": 1,
        "baseline": baseline,
        "group_count": {"rows": len(m.ROW_GROUPS), "cols": len(m.COL_GROUPS)},
        "passing_groups": sum(1 for item in group_results if item["passed"]),
        "retained_group_tags": [m.group_key(k, i) for k, i, _ in retained],
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
        "resumed_after_oom": True,
        "workers": 3,
        "group_order": "columns-first",
    }
    m.write_json(m.RESULT, result)
    if (
        final["passed"]
        and final["score"] is not None
        and baseline["score"] is not None
        and final["score"] < baseline["score"]
        and structural.get("server_layout") == "pass"
        and binding["binding_diffs_count"] == 0
    ):
        m.CANDIDATE.write_text(candidate)
        print("written passing candidate", m.CANDIDATE, sha256, flush=True)
    else:
        print("no promotion-safe candidate; result JSON written", flush=True)
    print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
