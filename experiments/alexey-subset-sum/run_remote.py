"""Subset-sum candidate pipeline, resumable, for a fast machine.

    PYTHONPATH=src python3 experiments/alexey-subset-sum/run_remote.py

Phases (each is skipped if its artifact already exists next to this file):

1. occupancy.json  — run the heaviest public case on the ORIGINAL machine in
   the Python sim, sampling every pipe's occupancy (~every 94 ticks), and
   record each pipe's peak. This is the ground truth for which pipes are
   storage. Slow (tens of minutes) but done once.
2. ss_reinflated.man — full squeeze (fp 13,293,316 -> 5,635,876), then for
   every pipe whose squeezed length dropped below peak*1.3+3, re-route it
   with that SAFE length as the target (not the original length — most of
   the original slack was never used). Pipes whose squeezed length already
   exceeds their measured need are left short: that is free tick savings.
3. remote_result.json — structural gates + the full 20-case public judge
   (builds the C fastsim extension if possible; on mac it links with
   -undefined dynamic_lookup).

Commit occupancy.json + ss_reinflated.man + remote_result.json back, or scp
them to the same path on the GCP box.
"""
import json
import math
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
log = lambda *a: print(*a, flush=True)

import littleman.sim as sim
from littleman.sim import Machine
from littleman.judge import RoundController, judge_problem, normalize_case
from littleman.server_compat import find_shared_walls
from littleman.subset_sum import build_subset_sum
from littleman.alexey_squeeze import squeeze
from littleman.alexey_piperoute import Router, RouteError

PROB = json.loads((ROOT / "data/small/problems/subset-sum.json").read_text())
t_all = time.time()

# ---------------------------------------------------------------- phase 1
occ_path = HERE / "occupancy.json"
if not occ_path.exists():
    log("phase 1: measuring per-pipe peak occupancy (python sim, slow, once)")
    text = build_subset_sum()
    case = max(PROB["publicTestData"],
               key=lambda c: sum(len(r["in"]) for r in normalize_case(c)))
    log("  case:", case.get("name"))
    m = sim.Machine.parse(text)
    peaks = {}
    state = {"n": 0}
    orig_exec = sim.Machine._execute

    def patched(self, man, _o=orig_exec):
        state["n"] += 1
        if state["n"] % 200000 == 0:
            for i, p in enumerate(self.pipes):
                occ = sum(1 for v in p.values if v is not None)
                if occ > peaks.get(i, 0):
                    peaks[i] = occ
            if state["n"] % 20000000 == 0:
                log("  sampled", state["n"], round(time.time() - t_all, 1), "s")
        return _o(self, man)

    sim.Machine._execute = patched
    res = m.run(max_ticks=15_000_000, controller=RoundController(normalize_case(case)))
    sim.Machine._execute = orig_exec
    log("  status", res.status, "ticks", res.ticks,
        "wall", round(time.time() - t_all, 1), "s")
    if res.status != "passed":
        log("  WARNING: measurement run did not pass; peaks may be partial")
    out = {f"{p.cells[0]}->{p.cells[-1]}": {"len": len(p.cells), "peak": peaks.get(i, 0)}
           for i, p in enumerate(m.pipes)}
    occ_path.write_text(json.dumps(out))
    log("  written occupancy.json")
occ = json.loads(occ_path.read_text())

# ---------------------------------------------------------------- phase 2
cand_path = HERE / "ss_reinflated.man"
if not cand_path.exists():
    log("phase 2: squeeze + restore only measured storage needs")
    orig = build_subset_sum()
    out = squeeze(orig, rows=True, cols=True)
    text = out[0] if isinstance(out, tuple) else out

    def pipe_map(t):
        m = Machine.parse(t)
        ridx = {id(r): i for i, r in enumerate(m.rooms)}
        d = {}
        for p in m.pipes:
            d.setdefault((ridx[id(p.source)], ridx[id(p.dest)]), []).append(p)
        return d

    map0, map1 = pipe_map(orig), pipe_map(text)
    todo, unsafe = [], []
    for key, ps0 in sorted(map0.items()):
        for a, b in zip(sorted(ps0, key=lambda p: p.cells[0]),
                        sorted(map1[key], key=lambda p: p.cells[0])):
            k0 = f"{a.cells[0]}->{a.cells[-1]}"
            peak = occ[k0]["peak"]
            need = max(2, math.ceil(peak * 1.3) + 3)
            if len(b.cells) < min(need, len(a.cells)):
                todo.append((b, min(need, len(a.cells)), peak))
    log("  pipes needing restoration:", len(todo), "of",
        sum(len(v) for v in map1.values()))
    ARROW = {"^": (-1, 0), "v": (1, 0), "<": (0, -1), ">": (0, 1)}
    done = 0
    for b, want, peak in todo:
        lines = text.split("\n")
        start, end = b.cells[0], b.cells[-1]
        into = ARROW[lines[end[0]][end[1]]]
        outd = ARROW[lines[start[0]][start[1]]]
        ok = False
        for waypoints in ([start, end],
                          [start, ((start[0] + end[0]) // 2 + 60, (start[1] + end[1]) // 2), end],
                          [start, (max(2, start[0] - 60), (start[1] + end[1]) // 2), end]):
            rt = Router(text)
            rt.erase(b.cells)
            try:
                cells = (rt.route(start, end, into=into, target=want, out=outd)
                         if len(waypoints) == 2 else
                         rt.route_via(waypoints, into=into, target=want, out=outd))
                cand = rt.apply(cells, into=into)
                if len(Machine.parse(cand).pipes) != len(occ):
                    raise RouteError("pipe count changed")
                text = cand
                done += 1
                ok = True
                break
            except Exception:  # noqa: BLE001
                continue
        if not ok:
            if len(b.cells) >= peak + 1:
                log("  keep-short (>=peak)", start, "->", end,
                    "len", len(b.cells), "peak", peak)
            else:
                unsafe.append((start, end, len(b.cells), want, peak))
                log("  UNSAFE", start, "->", end, "len", len(b.cells),
                    "need", want, "peak", peak)
        if done and done % 10 == 0:
            log("  restored", done, "/", len(todo), round(time.time() - t_all, 1), "s")
    log("  restored", done, "unsafe", len(unsafe))
    if unsafe:
        log("  ABORT: %d pipes below measured peak could not be re-routed" % len(unsafe))
        (HERE / "unsafe.json").write_text(json.dumps(unsafe, default=str))
        sys.exit(2)
    cand_path.write_text(text)
    log("  written ss_reinflated.man")
text = cand_path.read_text()

# ---------------------------------------------------------------- phase 3
backend = "python"
try:
    import littleman._fastsim_ext  # noqa: F401
    backend = "c-ext"
except Exception:
    try:
        import sysconfig
        cmd = ["cc", "-O3", "-fPIC", "-shared", "-fno-strict-aliasing"]
        if sys.platform == "darwin":
            cmd += ["-undefined", "dynamic_lookup"]
        cmd += ["-I" + sysconfig.get_paths()["include"],
                str(ROOT / "src/littleman/_ext/fastsim_ext.c"),
                "-o", str(ROOT / "src/littleman/_fastsim_ext.so")]
        subprocess.run(cmd, check=True, cwd=ROOT)
        import littleman._fastsim_ext  # noqa: F401
        backend = "c-ext (built)"
    except Exception as exc:  # noqa: BLE001
        log("WARNING: no C fastsim (%s); judging in pure python is very slow" % exc)
log("phase 3: gates + 20-case judge, backend:", backend)
m = Machine.parse(text)
lines = text.split("\n")
cells = [(r, c) for r, l in enumerate(lines) for c, ch in enumerate(l) if ch != " "]
gates = {
    "rooms": len(m.rooms), "pipes": len(m.pipes), "men": len(m.men),
    "min_pipe": min(len(p.cells) for p in m.pipes),
    "shared_walls": bool(find_shared_walls(text)),
    "box": [max(c for _, c in cells) + 1, max(r for r, _ in cells) + 1],
}
log("gates:", json.dumps(gates))
t_j = time.time()
rep = judge_problem(text, PROB)
result = {
    "backend": backend, "gates": gates,
    "cases_passed": rep.cases_passed, "cases_total": rep.cases_total,
    "case_ticks": rep.case_ticks,
    "failures": [r.reason for r in rep.case_results if not r.passed],
    "fp": rep.footprint, "score": rep.score,
    "judge_wall_s": round(time.time() - t_j, 1),
    "total_wall_s": round(time.time() - t_all, 1),
}
log(json.dumps(result, indent=1))
(HERE / "remote_result.json").write_text(json.dumps(result, indent=1))
log("done -- commit occupancy.json, ss_reinflated.man, remote_result.json")
