"""Verify the GPT LLM row-squeeze candidate without retaining huge parse heaps.

Each public case is judged in a fresh child process because the 9 MB physical
machine can temporarily use over 1 GB while parsing/compiling.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from build_candidate import EXPECTED_SHA, build
from littleman import alexey_pipecheck
from littleman.judge import footprint, judge_case, normalize_case
from littleman.server_compat import validate_layout
from littleman.sim import Machine

PROBLEM_PATH = ROOT / "data/small/problems/little-little-man.json"


def normalized_bindings(text: str) -> tuple[str, int, int]:
    machine = Machine.parse(text)
    pipe_index = {id(pipe): index for index, pipe in enumerate(machine.pipes)}
    resolution = []
    margins = []
    for room_index, room in enumerate(machine.rooms):
        incoming = machine.in_pipes.get(id(room), [])
        outgoing = machine.out_pipes.get(id(room), [])
        op_index = 0
        rows, cols = room.interior()
        for row in rows:
            for col in cols:
                op = machine.grid[row][col]
                if op in "srq":
                    pipes = outgoing if op == "s" else incoming
                    endpoint = 0 if op == "s" else -1
                    ranked = sorted(
                        (
                            abs(pipe.cells[endpoint][0] - row)
                            + abs(pipe.cells[endpoint][1] - col),
                            pipe.cells[endpoint],
                            pipe_index[id(pipe)],
                        )
                        for pipe in pipes
                    )
                    resolution.append((room_index, op_index, op, ranked[0][2]))
                    if len(ranked) > 1:
                        margins.append(ranked[1][0] - ranked[0][0])
                    op_index += 1
                elif op in "SRU":
                    pipes = outgoing if op == "S" else incoming
                    endpoint = 0 if op == "S" else -1
                    ordered = sorted(pipes, key=lambda pipe: pipe.cells[endpoint])
                    resolution.append(
                        (
                            room_index,
                            op_index,
                            op,
                            [pipe_index[id(pipe)] for pipe in ordered],
                        )
                    )
                    op_index += 1
    encoded = json.dumps(resolution, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest(), len(resolution), min(margins)


def judge_one(path: Path, index: int) -> dict:
    code = r'''
import json,sys
from pathlib import Path
sys.path.insert(0, sys.argv[3])
from littleman.judge import judge_case, normalize_case
text=Path(sys.argv[1]).read_text()
problem=json.loads(Path(sys.argv[4]).read_text())
index=int(sys.argv[2])
result=judge_case(text,normalize_case(problem["publicTestData"][index]),max_ticks=problem.get("tickCap",50000000))
print(json.dumps({"index":index,"passed":result.passed,"ticks":result.ticks,"reason":result.reason}))
'''
    output = subprocess.check_output(
        [sys.executable, "-c", code, str(path), str(index), str(ROOT / "src"), str(PROBLEM_PATH)],
        text=True,
    )
    return json.loads(output)


def main() -> None:
    candidate = build()
    assert hashlib.sha256(candidate.encode()).hexdigest() == EXPECTED_SHA
    validate_layout(candidate)
    alexey_pipecheck.check(candidate)
    machine = Machine.parse(candidate)
    assert (len(machine.rooms), len(machine.pipes), len(machine.men)) == (145, 231, 143)
    assert min(len(pipe.cells) for pipe in machine.pipes) >= 2

    parent = (ROOT / "submissions/llm/llm_codex_01.man").read_text()
    assert normalized_bindings(candidate) == normalized_bindings(parent)

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "candidate.man"
        path.write_text(candidate)
        results = [judge_one(path, index) for index in range(14)]
    assert all(result["passed"] for result in results), results
    ticks = [result["ticks"] for result in results]
    width = max(map(len, candidate.rstrip("\n").splitlines()))
    height = len(candidate.rstrip("\n").splitlines())
    average = sum(ticks) / len(ticks)
    score = max(width, height) ** 2 * average
    print(
        json.dumps(
            {
                "sha256": EXPECTED_SHA,
                "width": width,
                "height": height,
                "footprint": footprint(candidate),
                "caseTicks": ticks,
                "averageTicks": average,
                "score": score,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
