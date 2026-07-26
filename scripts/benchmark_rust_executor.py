#!/usr/bin/env python
"""Reproduce Rust executor correctness and performance acceptance metrics.

Examples:

    uv run python scripts/benchmark_rust_executor.py --suite frozen --workers 8
    uv run python scripts/benchmark_rust_executor.py --suite current --workers 8
    uv run python scripts/benchmark_rust_executor.py --llm-batch --workers 8
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import platform
import re
import subprocess
import sys
import time

from littleman import judge, rustexec

REPO = pathlib.Path(__file__).resolve().parent.parent
GOAL_COMMIT = "e8d048cf1fdfdb06add7e64deb2da5e4f2fca85e"
FROZEN_TESTS = (
    "tests/test_llm.py",
    "tests/test_llm_actionprotocol.py",
    "tests/test_llm_bindscore.py",
    "tests/test_llm_bordercheck.py",
    "tests/test_llm_candidatefetch.py",
    "tests/test_llm_cmpfetch.py",
    "tests/test_llm_colorfetch.py",
    "tests/test_llm_components.py",
    "tests/test_llm_cycle.py",
    "tests/test_llm_fetchjoin.py",
    "tests/test_llm_fuzz.py",
    "tests/test_llm_geom.py",
    "tests/test_llm_geometry_assemble.py",
    "tests/test_llm_initframe.py",
    "tests/test_llm_manmap.py",
    "tests/test_llm_manstep.py",
    "tests/test_llm_maskmap.py",
    "tests/test_llm_opfetch.py",
    "tests/test_llm_packraw.py",
    "tests/test_llm_pairpack.py",
    "tests/test_llm_perimeter.py",
    "tests/test_llm_pipeaction.py",
    "tests/test_llm_pipeapply.py",
    "tests/test_llm_pipecandidate.py",
    "tests/test_llm_pipeframe.py",
    "tests/test_llm_pipemask.py",
    "tests/test_llm_pipeselect.py",
    "tests/test_llm_pipestarts.py",
    "tests/test_llm_pipetrace.py",
    "tests/test_llm_pipetrace_dest.py",
    "tests/test_llm_rawfetch.py",
    "tests/test_llm_recordstrip.py",
    "tests/test_llm_rich_exec.py",
    "tests/test_llm_ring_exec.py",
    "tests/test_llm_roomfind.py",
    "tests/test_llm_runtimefetch.py",
    "tests/test_llm_scan.py",
    "tests/test_llm_selecteligible.py",
    "tests/test_llm_statebuild.py",
    "tests/test_llm_statecopy.py",
    "tests/test_llm_stateframe.py",
    "tests/test_llm_stateindex.py",
    "tests/test_llm_tick_assemble.py",
    "tests/test_llm_wallgen.py",
    "tests/test_llm_wallhit.py",
    "tests/test_llm_wallscan.py",
)


def command_version(*command):
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    return result.stdout.strip() or result.stderr.strip()


def hardware():
    model = "unknown"
    cpuinfo = pathlib.Path("/proc/cpuinfo")
    if cpuinfo.exists():
        match = re.search(r"^model name\s*:\s*(.+)$", cpuinfo.read_text(), re.MULTILINE)
        if match:
            model = match.group(1)
    return {
        "platform": platform.platform(),
        "python": sys.version.splitlines()[0],
        "rustc": command_version("rustc", "--version"),
        "cargo": command_version("cargo", "--version"),
        "cpu_model": model,
        "logical_cpus": os.cpu_count(),
    }


def suite_files(mode):
    if mode == "frozen":
        return list(FROZEN_TESTS)
    return sorted(
        str(path.relative_to(REPO)) for path in (REPO / "tests").glob("test_llm*.py")
    )


def run_suite(mode, workers):
    files = suite_files(mode)
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "littleman.rustexec",
        "-n",
        str(workers),
        "--durations=20",
        *files,
    ]
    started = time.perf_counter()
    process = subprocess.run(
        command, cwd=REPO, capture_output=True, text=True, check=False
    )
    elapsed = time.perf_counter() - started
    output = process.stdout + process.stderr
    print(output, end="")
    summary_match = re.search(
        r"(?P<passed>\d+) passed(?:, (?P<skipped>\d+) skipped)? in (?P<seconds>[\d.]+)s",
        output,
    )
    durations = [
        line.strip()
        for line in output.splitlines()
        if re.match(r"^\d+\.\d+s (?:call|setup|teardown)\s+", line)
    ][:20]
    result = {
        "mode": mode,
        "workers": workers,
        "modules": len(files),
        "command": command,
        "returncode": process.returncode,
        "wall_seconds": elapsed,
        "slowest": durations,
    }
    if summary_match:
        result.update(
            passed=int(summary_match.group("passed")),
            skipped=int(summary_match.group("skipped") or 0),
            pytest_seconds=float(summary_match.group("seconds")),
        )
    if process.returncode:
        raise SystemExit(process.returncode)
    return result


def run_llm_batch(workers):
    artifact = REPO / "submissions/llm/llm_codex_01.man"
    problem = json.loads(
        (REPO / "data/small/problems/little-little-man.json").read_text()
    )
    rounds = [judge.normalize_case(case) for case in problem["publicTestData"]]
    started = time.perf_counter()
    compiled = rustexec.CompiledMachine(artifact.read_text())
    compile_seconds = time.perf_counter() - started
    started = time.perf_counter()
    sequential = rustexec.run_rounds_parallel(
        compiled, rounds, max_ticks=problem["tickCap"], workers=1
    )
    sequential_seconds = time.perf_counter() - started
    started = time.perf_counter()
    parallel = rustexec.run_rounds_parallel(
        compiled, rounds, max_ticks=problem["tickCap"], workers=workers
    )
    parallel_seconds = time.perf_counter() - started
    started = time.perf_counter()
    encoded = compiled.encoded_ir()
    encode_seconds = time.perf_counter() - started
    return {
        "artifact": str(artifact.relative_to(REPO)),
        "sha256": compiled.sha256,
        "cases": len(rounds),
        "workers": workers,
        "compile_seconds": compile_seconds,
        "sequential_seconds": sequential_seconds,
        "parallel_seconds": parallel_seconds,
        "speedup": sequential_seconds / parallel_seconds,
        "deterministic": sequential == parallel,
        "all_passed": all(result.status == "passed" for result in parallel),
        "ticks": [result.judged_ticks for result in parallel],
        "total_ticks": sum(result.judged_ticks for result in parallel),
        "encoded_ir_bytes": len(encoded),
        "encode_seconds": encode_seconds,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=["frozen", "current"])
    parser.add_argument("--llm-batch", action="store_true")
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    if not args.suite and not args.llm_batch:
        parser.error("select --suite and/or --llm-batch")
    report = {
        "goal_commit": GOAL_COMMIT,
        "git_head": command_version("git", "rev-parse", "HEAD"),
        "backend": rustexec.backend(),
        "hardware": hardware(),
    }
    if args.suite:
        report["suite"] = run_suite(args.suite, args.workers)
    if args.llm_batch:
        report["llm_batch"] = run_llm_batch(args.workers)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
