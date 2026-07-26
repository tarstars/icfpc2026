"""Independent one-shot subset-sum candidate check."""
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

t_start = time.time()
log = lambda *a: print(*a, flush=True)

backend = "python"
try:
    import littleman._fastsim_ext  # noqa: F401
    backend = "c-ext"
except Exception:
    try:
        subprocess.run(
            [sys.executable, str(ROOT / "scripts/build_fastsim_ext.py")],
            check=True,
            cwd=ROOT,
        )
        import littleman._fastsim_ext  # noqa: F401
        backend = "c-ext (built)"
    except Exception as exc:  # noqa: BLE001
        log("WARNING: C fastsim unavailable (%s); pure python is much slower" % exc)
log("backend:", backend)

from littleman.sim import Machine
from littleman.judge import judge_problem
from littleman.server_compat import find_shared_walls

cand_path = HERE / "ss_reinflated.man"
orig = None

if not cand_path.exists():
    log("candidate missing -- building it here")
    from littleman.subset_sum import build_subset_sum
    from littleman.alexey_squeeze import squeeze
    from littleman.alexey_piperoute import Router, RouteError

    orig = build_subset_sum()
    out = squeeze(orig, rows=True, cols=True)
    text = out[0] if isinstance(out, tuple) else out
    log("squeezed in", round(time.time() - t_start, 1), "s")

    def pipe_map(t):
        m = Machine.parse(t)
        ridx = {id(r): i for i, r in enumerate(m.rooms)}
        d = {}
        for p in m.pipes:
            d.setdefault((ridx[id(p.source)], ridx[id(p.dest)]), []).append(p)
        return m, d

    m0, map0 = pipe_map(orig)
    m1, map1 = pipe_map(text)
    assert set(map0) == set(map1)
    todo = []
    for key, ps0 in sorted(map0.items()):
        ps1 = map1[key]
        assert len(ps0) == len(ps1), key
        for a, b in zip(
            sorted(ps0, key=lambda p: p.cells[0]),
            sorted(ps1, key=lambda p: p.cells[0]),
        ):
            if len(b.cells) < len(a.cells):
                todo.append((key, b.cells[0], b.cells[-1], b.cells, len(a.cells)))
    log("pipes to re-inflate:", len(todo))
    ARROW = {"^": (-1, 0), "v": (1, 0), "<": (0, -1), ">": (0, 1)}
    done = 0
    failures = []
    for index, (key, start, end, cells, want) in enumerate(todo, 1):
        lines = text.split("\n")
        into = ARROW[lines[end[0]][end[1]]]
        outd = ARROW[lines[start[0]][start[1]]]
        rt = Router(text)
        rt.erase(cells)
        try:
            new = rt.route(start, end, into=into, target=want, out=outd)
            cand = rt.apply(new, into=into)
            if len(Machine.parse(cand).pipes) != 2164:
                raise RouteError("pipe count changed")
            text = cand
            done += 1
        except Exception as exc:  # noqa: BLE001
            failures.append({
                "key": key,
                "start": start,
                "end": end,
                "wanted": want,
                "kept": len(cells),
                "error": f"{type(exc).__name__}: {exc}",
            })
            log("  KEEP-SHORT", key, want, "->", len(cells), type(exc).__name__)
        if index % 10 == 0 or index == len(todo):
            log("  progress", index, "/", len(todo), "done", done,
                round(time.time() - t_start, 1), "s")
    log("re-inflated", done, "of", len(todo), "failed", len(failures))
    cand_path.write_text(text)
    (HERE / "reinflation_failures.json").write_text(json.dumps(failures, indent=1))
else:
    text = cand_path.read_text()
    log("using existing candidate", cand_path.name)

m = Machine.parse(text)
gates = {
    "rooms": len(m.rooms),
    "pipes": len(m.pipes),
    "men": len(m.men),
    "min_pipe": min(len(p.cells) for p in m.pipes),
    "shared_walls": bool(find_shared_walls(text)),
}
if orig is None:
    from littleman.subset_sum import build_subset_sum
    orig = build_subset_sum()
l0 = sorted(len(p.cells) for p in Machine.parse(orig).pipes)
l1 = sorted(len(p.cells) for p in m.pipes)
gates["length_multiset_restored"] = l0 == l1
gates["shorter_pipes"] = sum(1 for a, b in zip(l0, l1) if b < a)
gates["longer_pipes"] = sum(1 for a, b in zip(l0, l1) if b > a)
lines = text.split("\n")
cells = [(r, c) for r, line in enumerate(lines) for c, ch in enumerate(line) if ch != " "]
w = max(c for _, c in cells) + 1
h = max(r for r, _ in cells) + 1
gates["box"] = [w, h]
gates["fp"] = max(w, h) ** 2
log("gates:", json.dumps(gates))

prob = json.loads((ROOT / "data/small/problems/subset-sum.json").read_text())
t_j = time.time()
rep = judge_problem(text, prob)
result = {
    "backend": backend,
    "gates": gates,
    "cases_passed": rep.cases_passed,
    "cases_total": rep.cases_total,
    "case_ticks": rep.case_ticks,
    "failures": [r.reason for r in rep.case_results if not r.passed],
    "fp": rep.footprint,
    "score": rep.score,
    "judge_wall_s": round(time.time() - t_j, 1),
    "total_wall_s": round(time.time() - t_start, 1),
}
log(json.dumps(result, indent=1))
(HERE / "remote_result.json").write_text(json.dumps(result, indent=1))
log("written remote_result.json")
