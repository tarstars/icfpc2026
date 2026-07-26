"""Find the maximal SAFE subset of squeeze deletions by judging, on a fast box.

    PYTHONPATH=src python3 experiments/alexey-subset-sum/bisect_remote.py

The full squeeze (655 rows + 3040 cols) deadlocks because some deleted lines
cut storage pipes. A judge run is ~25 s on an M4 with the C ext, so instead
of measuring occupancy (30+ hours in the Python sim) we TEST deletions:
split the deletable lines into contiguous groups, judge each group alone,
keep the passing ones, then judge the union and peel groups off on failure.
Writes ss_bisect.man + bisect_result.json -- commit both back.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
log = lambda *a: print(*a, flush=True)

try:
    import littleman._fastsim_ext  # noqa: F401
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
    except Exception as e:  # noqa: BLE001
        log("WARNING: no C ext:", e)

from littleman.judge import judge_problem
from littleman.subset_sum import build_subset_sum

PROB = json.loads((ROOT / "data/small/problems/subset-sum.json").read_text())
ORIG = build_subset_sum()
lines = ORIG.rstrip("\n").split("\n")
W = max(len(l) for l in lines)
grid = [l.ljust(W) for l in lines]
H = len(grid)
del_rows = [r for r in range(H) if all(ch in " |" for ch in grid[r])]
del_cols = [c for c in range(W) if all(row[c] in " -" for row in grid)]
log("deletable rows", len(del_rows), "cols", len(del_cols))


def build(rows, cols):
    rs, cs = set(rows), set(cols)
    return "\n".join(
        "".join(row[c] for c in range(W) if c not in cs).rstrip()
        for r, row in enumerate(grid) if r not in rs) + "\n"


def ok(rows, cols, tag):
    t0 = time.time()
    rep = judge_problem(build(rows, cols), PROB)
    good = rep.cases_passed == rep.cases_total
    log(f"  [{tag}] rows={len(rows)} cols={len(cols)} -> "
        f"{rep.cases_passed}/{rep.cases_total} fp={rep.footprint} "
        f"score={rep.score if good else 'x'} ({round(time.time() - t0, 1)}s)")
    return good, rep


def groups(seq, n):
    k = max(1, len(seq) // n)
    return [seq[i:i + k] for i in range(0, len(seq), k)]


t_all = time.time()
base_ok, rep0 = ok([], [], "baseline")
assert base_ok, "regenerated original must pass"

passing_r, passing_c = [], []
for g in groups(del_rows, 8):
    if ok(g, [], f"rows {g[0]}-{g[-1]}")[0]:
        passing_r.append(g)
for g in groups(del_cols, 16):
    if ok([], g, f"cols {g[0]}-{g[-1]}")[0]:
        passing_c.append(g)


def flat(gs):
    return [x for g in gs for x in g]


rows, cols = flat(passing_r), flat(passing_c)
good, rep = ok(rows, cols, "union")
work_r, work_c = list(passing_r), list(passing_c)
while not good and (work_r or work_c):
    if work_c and (not work_r or len(flat(work_c)) >= len(flat(work_r))):
        drop = max(work_c, key=len)
        work_c.remove(drop)
        dropped = f"cols {drop[0]}-{drop[-1]}"
    else:
        drop = max(work_r, key=len)
        work_r.remove(drop)
        dropped = f"rows {drop[0]}-{drop[-1]}"
    rows, cols = flat(work_r), flat(work_c)
    good, rep = ok(rows, cols, f"union minus {dropped}")

result = {"rows_deleted": len(rows), "cols_deleted": len(cols),
          "passed": good, "fp": rep.footprint, "score": rep.score,
          "baseline_score": rep0.score, "wall_s": round(time.time() - t_all, 1)}
log(json.dumps(result))
if good and rep.score < rep0.score:
    (HERE / "ss_bisect.man").write_text(build(rows, cols))
    (HERE / "bisect_result.json").write_text(
        json.dumps({**result, "rows": rows, "cols": cols}))
    log("written ss_bisect.man + bisect_result.json -- commit both")
else:
    log("no safe improvement found; commit nothing")
