#!/usr/bin/env python
"""Differential test harness across every Little Man engine we have.

Runs a machine artifact against each available simulator over a problem's
public cases and reports per-case ``passed / ticks / failure-reason`` plus
any disagreement with the organizers' WASM, which is ground truth.

Engines
-------
``wasm``           ``claude/official-sim`` -- the organizers' own Go->WASM
                   engine, the same one the contest server runs.  AUTHORITY.
``sim``            ``littleman.judge`` forced onto the pure-Python
                   ``sim.Machine.run`` reference loop.
``fastsim``        ``littleman.judge`` on its normal executor
                   (``fastsim.Machine``: C extension when built).
``server_compat``  ``littleman.server_compat`` -- the layout gate plus
                   ``alexey_walljudge``'s wall-tolerant semantics, i.e. what
                   ``scripts/preflight.py`` decides submissions with.

Usage
-----
    uv run python scripts/sim_diff.py <file.man> <problem-slug>
    uv run python scripts/sim_diff.py --json --engine wasm <f.man> <slug>
    uv run python scripts/sim_diff.py --sweep            # every submissions/*.man

Importable: :func:`run_engine`, :func:`load_cases`, :func:`diff_artifact`.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROBLEM_DIR = ROOT / "data" / "small" / "problems"
WASM_RUNNER = pathlib.Path(
    os.environ.get(
        "SIM_DIFF_WASM_RUNNER",
        "/tmp/claude-1001/-home-tarstars-prj-icfpc2026-claude/"
        "16162f30-05a0-40b1-b603-617db3401d67/scratchpad/wasm_multi.mjs",
    )
)

ENGINES = ("wasm", "sim", "fastsim", "server_compat")

# submissions/<dir> -> data/small/problems/<slug>.json
DIR_TO_SLUG = {
    "history": "history-lesson",
    "lllm": "little-little-little-man",
    "llm": "little-little-man",
    "sort": "sort-numbers",
    "subset-sum": "subset-sum",
}


# --------------------------------------------------------------- problem data
def load_problem(slug: str) -> dict:
    return json.loads((PROBLEM_DIR / f"{slug}.json").read_text())


def load_cases(slug: str) -> list[list[dict]]:
    """Public cases, each normalised to a list of rounds."""
    cases = []
    for case in load_problem(slug)["publicTestData"]:
        rounds = case.get("rounds")
        if not rounds:
            rounds = [{"in": case.get("in", []), "out": case.get("out", [])}]
        cases.append(rounds)
    return cases


def slug_for(path: pathlib.Path) -> str:
    name = path.parent.name
    return DIR_TO_SLUG.get(name, name)


# ------------------------------------------------------------------ reasons
# Every way an engine can say "this program does not load".  The three
# engines word it completely differently, so compare the class, not the text.
_LOAD_MARKERS = (
    "loaderror", "load-error", "load:", "servercompatibilityerror",
    "layout-reject", "pipe interrupted", "pipe reverses", "pipe runs off",
    "bad pipe glyph", "unmatched backtick", "between backticks",
    "outgoing pipe", "incoming pipe", "share", "multiple '@'", "too large",
    "bad display attach", "shorter than", "must be at least",
)


def bucket(reason: str | None, passed: bool) -> str:
    """Collapse engine-specific wording into comparable buckets."""
    if passed:
        return "pass"
    if not reason:
        return "no-output"
    r = reason.lower()
    for key in ("timeout", "stalled", "engine-error", "engine-crash"):
        if key in r:
            return key
    if any(marker in r for marker in _LOAD_MARKERS):
        return "load-error"
    for key in ("wall", "bad-op", "no-pipe", "split-limit"):
        if key in r:
            return key
    if r.startswith("display"):
        return "display"
    if "cap" in r:  # tick-cap / step-cap / op-cap / time-cap
        return "cap"
    if r in {"done", "halted"} or "wrong-output" in r:
        # the machine ran out of work without matching every expected value
        return "no-output"
    return r


# --------------------------------------------------------------------- wasm
def _wasm_case(rounds) -> dict:
    """One case in the runner's wire format.

    `frames` must be nested one level per ROUND (`[][][]string`: rounds ->
    frames -> rows); a flat list of frames makes the Go loader reject the
    request with "bad framesJson".
    """
    return {
        "input": [[int(v) for v in rd.get("in", [])] for rd in rounds],
        "expected": [[int(v) for v in rd.get("out", [])] for rd in rounds],
        "frames": ([rd.get("frames", []) for rd in rounds]
                   if any(rd.get("frames") for rd in rounds) else []),
    }


# The Go runtime inside the WASM can exit for good after some load errors;
# every later case in that node process then fails spuriously.  Detect and
# restart from the offending case in a fresh process.
_WASM_POISON = ("already exited", "not a function")


def _wasm_batch(text: str, cases, max_ticks: int, wall_ms: int,
                timeout: float) -> tuple[list[dict], str]:
    request = {"program": text, "cases": [_wasm_case(r) for r in cases],
               "maxTicks": max_ticks, "wallMs": wall_ms}
    proc = subprocess.run(["node", str(WASM_RUNNER)], input=json.dumps(request),
                          capture_output=True, text=True, timeout=timeout)
    rows = [json.loads(line[5:]) for line in proc.stdout.splitlines()
            if line.startswith("CASE ")]
    return rows, proc.stderr.strip()[:200]


def run_wasm(text: str, cases, max_ticks: int, wall_ms: int = 60_000,
             timeout: float = 600.0) -> list[dict]:
    # One resident WASM instance leaks across sessions: on a big program a
    # later `load()` starts returning `undefined` ("Unexpected token u in
    # JSON"), which looks exactly like a load error but is not one.  Give
    # every case of a big program its own node process.
    batch = 1 if len(text) > 50_000 else len(cases)
    raw_rows: list[dict] = []
    restarts = 0
    while len(raw_rows) < len(cases):
        rows, err = _wasm_batch(text, cases[len(raw_rows):len(raw_rows) + batch],
                                max_ticks, wall_ms, timeout)
        if not rows:
            raise RuntimeError(f"wasm runner produced nothing: {err}")
        for row in rows:
            reason = str(row.get("reason") or "").lower()
            if any(p in reason for p in _WASM_POISON) and restarts < 8:
                restarts += 1
                break  # rerun this case (and the rest) in a fresh process
            raw_rows.append(row)
        else:
            continue
        if restarts >= 8:
            raw_rows.extend(rows)
    out = []
    for raw in raw_rows[:len(cases)]:
        # `outputSettled` is NOT a valid oracle on display problems -- it goes
        # true even when the committed frames are wrong.  The runner judges
        # values against `state.output` and frames against the engine's own
        # `frameJudge:{matched,total}` and reports the answer as `passed`.
        passed = bool(raw.get("passed"))
        fatal = raw.get("fatal") or {}
        reason = fatal.get("reason") or raw.get("reason") or raw.get("status")
        if raw.get("status") == "load-error":
            reason = f"load: {reason}"
        out.append({
            "passed": passed,
            "ticks": int(raw.get("ticks") or 0),
            "reason": None if passed else reason,
            "bucket": bucket(None if passed else reason, passed),
            "ms": raw.get("ms"),
            "fatal_pos": fatal.get("pos"),
            "fatal_cell": fatal.get("cell"),
        })
    return out


# ------------------------------------------------------------------- python
def run_python(engine: str, text: str, cases, max_ticks: int) -> list[dict]:
    from littleman import fastsim

    if engine == "server_compat":
        from littleman import server_compat
        try:
            server_compat.validate_layout(text)
        except Exception as exc:  # ServerCompatibilityError / LoadError
            return [{"passed": False, "ticks": 0,
                     "reason": f"layout-reject: {exc}"[:120],
                     "bucket": "load-error"} for _ in cases]
        from littleman import alexey_walljudge as impl
    else:
        from littleman import judge as impl

    saved = fastsim.FASTSIM_ENABLED
    if engine == "sim":
        fastsim.FASTSIM_ENABLED = False
    try:
        out = []
        for rounds in cases:
            start = time.time()
            try:
                res = impl.judge_case(text, rounds, max_ticks=max_ticks)
                passed, ticks, reason = res.passed, res.ticks, res.reason
            except Exception as exc:
                passed, ticks = False, 0
                reason = f"{type(exc).__name__}: {exc}"[:120]
            out.append({"passed": passed, "ticks": ticks,
                        "reason": None if passed else reason,
                        "bucket": bucket(None if passed else reason, passed),
                        "ms": int((time.time() - start) * 1000)})
        return out
    finally:
        fastsim.FASTSIM_ENABLED = saved


def run_engine(engine: str, text: str, cases, max_ticks: int,
               wall_ms: int = 60_000) -> list[dict]:
    """Per-case results for one engine.  Same shape for every engine."""
    if engine == "wasm":
        return run_wasm(text, cases, max_ticks, wall_ms=wall_ms)
    return run_python(engine, text, cases, max_ticks)


# ---------------------------------------------------------------- comparison
def diff_artifact(path: str | pathlib.Path, slug: str,
                  engines=ENGINES, max_ticks: int | None = None,
                  wall_ms: int = 60_000) -> dict:
    """Run every engine on one artifact; flag disagreement with the WASM."""
    path = pathlib.Path(path)
    text = path.read_text()
    problem = load_problem(slug)
    cap = max_ticks or problem.get("tickCap") or 5_000_000
    cases = load_cases(slug)
    results = {}
    for engine in engines:
        try:
            results[engine] = run_engine(engine, text, cases, cap,
                                         wall_ms=wall_ms)
        except Exception as exc:
            results[engine] = [{"passed": False, "ticks": 0,
                                "reason": f"engine-error: {exc}"[:160],
                                "bucket": "engine-error"}] * len(cases)
    return {"artifact": str(path), "problem": slug, "cases": len(cases),
            "tick_cap": cap, "results": results,
            "disagreements": collect_disagreements(results)}


def collect_disagreements(results: dict) -> list[dict]:
    """Per-case pass/fail (and reason) mismatches against the WASM."""
    truth = results.get("wasm")
    if not truth:
        return []
    out = []
    for engine, rows in results.items():
        if engine == "wasm":
            continue
        for index, (ours, gold) in enumerate(zip(rows, truth)):
            if gold["bucket"] in {"timeout", "stalled", "engine-error"}:
                continue
            if ours["bucket"] in {"timeout", "engine-error"}:
                continue
            if ours["passed"] != gold["passed"]:
                out.append({"engine": engine, "case": index,
                            "kind": "verdict",
                            "ours": ours["bucket"], "wasm": gold["bucket"],
                            "our_passed": ours["passed"],
                            "wasm_passed": gold["passed"]})
            elif not ours["passed"] and ours["bucket"] != gold["bucket"]:
                out.append({"engine": engine, "case": index,
                            "kind": "reason",
                            "ours": ours["bucket"], "wasm": gold["bucket"],
                            "our_passed": False, "wasm_passed": False})
    return out


# --------------------------------------------------------------------- sweep
def iter_artifacts(max_bytes: int = 400_000):
    """Every `submissions/*/*.man` that is neither an LFS pointer nor huge."""
    for path in sorted((ROOT / "submissions").glob("*/*.man")):
        size = path.stat().st_size
        if size > max_bytes:
            yield path, "skip-large"
            continue
        with path.open("rb") as handle:
            if handle.read(16).startswith(b"version https:"):
                yield path, "skip-lfs"
                continue
        yield path, "ok"


def _sweep_one(path: pathlib.Path, engines, per_engine_timeout: float) -> dict:
    slug = slug_for(path)
    record = {"artifact": str(path), "problem": slug, "state": "ok",
              "results": {}}
    for engine in engines:
        cmd = [sys.executable, str(pathlib.Path(__file__).resolve()),
               "--json", "--engine", engine, str(path), slug]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=per_engine_timeout, cwd=str(ROOT))
            payload = json.loads(proc.stdout)
            record["results"][engine] = payload["results"][engine]
            record["cases"] = payload["cases"]
        except subprocess.TimeoutExpired:
            record["results"][engine] = [{"passed": False, "ticks": 0,
                                          "reason": "timeout",
                                          "bucket": "timeout"}]
        except Exception as exc:
            record["results"][engine] = [{"passed": False, "ticks": 0,
                                          "reason": f"engine-error: {exc}"[:160],
                                          "bucket": "engine-error"}]
    # pad short rows (a timed-out engine reports one row, not one per case)
    n = record.get("cases") or max(len(v) for v in record["results"].values())
    record["cases"] = n
    for engine, rows in record["results"].items():
        if len(rows) < n:
            record["results"][engine] = rows + [dict(rows[-1])] * (n - len(rows))
    record["disagreements"] = collect_disagreements(record["results"])
    return record


def sweep(engines=ENGINES, per_engine_timeout: float = 150.0,
          out_path: pathlib.Path | None = None, workers: int = 8) -> list[dict]:
    """Run every artifact, one subprocess per (artifact, engine), so that a
    hang in one engine cannot lose the others' answers."""
    from concurrent.futures import ThreadPoolExecutor

    todo = []
    records = []
    for path, state in iter_artifacts():
        if state != "ok":
            records.append({"artifact": str(path), "state": state})
            print(f"{state:12} {path}", flush=True)
        else:
            todo.append(path)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_sweep_one, p, engines, per_engine_timeout): p
                   for p in todo}
        for future, path in futures.items():
            record = future.result()
            records.append(record)
            marks = " ".join(
                f"{e}={sum(r['passed'] for r in record['results'][e])}"
                for e in engines)
            print(f"{'DIFF' if record['disagreements'] else '  ok':6} "
                  f"{path.relative_to(ROOT)}  {marks}", flush=True)
            if out_path:
                out_path.write_text(json.dumps(records))
    return records


# ----------------------------------------------------------------------- cli
def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", nargs="?")
    parser.add_argument("problem", nargs="?",
                        help="slug; inferred from the submissions/ dir if absent")
    parser.add_argument("--engine", action="append",
                        choices=list(ENGINES),
                        help="restrict to these engines (repeatable)")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--sweep", action="store_true")
    parser.add_argument("--out", type=pathlib.Path)
    parser.add_argument("--max-ticks", type=int)
    parser.add_argument("--wall-ms", type=int, default=60_000)
    args = parser.parse_args(argv[1:])
    engines = tuple(args.engine) if args.engine else ENGINES

    if args.sweep:
        sweep(engines, out_path=args.out)
        return 0
    if not args.artifact:
        parser.error("artifact required (or --sweep)")
    path = pathlib.Path(args.artifact)
    slug = args.problem or slug_for(path)
    report = diff_artifact(path, slug, engines, args.max_ticks, args.wall_ms)

    if args.json:
        print(json.dumps(report))
        return 0

    print(f"artifact : {path}")
    print(f"problem  : {slug}  ({report['cases']} public cases, "
          f"tick cap {report['tick_cap']:,})")
    width = max(len(e) for e in engines)
    for engine in engines:
        rows = report["results"][engine]
        mark = "AUTHORITY" if engine == "wasm" else ""
        print(f"  {engine:<{width}}  {sum(r['passed'] for r in rows)}"
              f"/{len(rows)}  {mark}")
    print()
    print(f"  {'case':<5}" + "".join(f"{e:<26}" for e in engines))
    for index in range(report["cases"]):
        cells = []
        for engine in engines:
            row = report["results"][engine][index]
            tag = "pass" if row["passed"] else row["bucket"]
            cells.append(f"{tag}/{row['ticks']}")
        print(f"  {index:<5}" + "".join(f"{c:<26}" for c in cells))
    print()
    if report["disagreements"]:
        print(f"DISAGREEMENTS vs WASM: {len(report['disagreements'])}")
        for d in report["disagreements"]:
            print(f"  case {d['case']:<3} {d['engine']:<14} "
                  f"ours={d['ours']:<14} wasm={d['wasm']}")
    else:
        print("no disagreement with the organizers' WASM")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
