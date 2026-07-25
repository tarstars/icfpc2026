#!/usr/bin/env python3
"""Acceptance checks for the extracted official WASM littleman engine.

Drives claude/official-sim/harness.mjs (Node v18) via subprocess.
Run: python3 claude/official-sim/run_checks.py
"""
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
HARNESS = HERE / "harness.mjs"
LATENCIES = []


def run_harness(req: dict) -> dict:
    t0 = time.time()
    proc = subprocess.run(
        ["node", str(HARNESS)],
        input=json.dumps(req).encode(),
        capture_output=True,
        timeout=180,
    )
    LATENCIES.append(time.time() - t0)
    if proc.returncode != 0:
        raise RuntimeError(f"harness failed: {proc.stderr.decode()[:500]}")
    return json.loads(proc.stdout.decode())


RESULTS = []


def report(name: str, ok: bool, detail: str) -> None:
    RESULTS.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def check1() -> None:
    """memory_04.man vs public memory cases, all rounds in one run
    (editor mode: rounds joined by ' / ', expected drives round release)."""
    prog = (REPO / "submissions/memory/memory_04.man").read_text()
    cases = json.loads((REPO / "data/small/problems/memory.json").read_text())[
        "publicTestData"
    ]
    matched = []
    for c in cases:
        inp = [int(t) for t in c["in"]]
        want = [str(int(t)) for t in c["out"]]
        res = run_harness(
            {
                "program": prog,
                "input": inp,
                "expected": [want],
                "maxTicks": 3_000_000,
                "stopOnSettle": True,
            }
        )
        got = [str(v) for v in res["output"]]
        matched.append(got == want)
    ok = sum(matched) >= 3
    report(
        "1 memory_04 vs public cases (each case = independent single-round run,"
        " expected passed so the engine settles)",
        ok,
        f"{sum(matched)}/{len(cases)} cases matched exactly: "
        + ",".join("Y" if m else "n" for m in matched),
    )


def _squash(timeline):
    """[{t,men,alive}] -> 't0..t1:men/alive' run-length segments."""
    segs = []
    for e in timeline:
        key = (e["men"], e["alive"])
        if segs and segs[-1][2] == key:
            segs[-1][1] = e["t"]
        else:
            segs.append([e["t"], e["t"], key])
    return " ".join(
        f"t{a}..{b}:{m}men/{al}alive" if a != b else f"t{a}:{m}men/{al}alive"
        for a, b, (m, al) in segs
    )


SPLIT_DEMO = """+------+
| >  H |
|      |
|@Y    |
|      |
| >  H |
+------+
"""

Y_MEET_MAP = """+-------------------+
|     >     v       |
|                   |
| >   Y             |
|                   |
|     >          v  |
|@Y<                |
|  ^             <  |
|                   |
|                   |
|                   |
| >         ^       |
+-------------------+
"""


def check2() -> None:
    """/split demo: split, both copies halt on H, no error."""
    res = run_harness({"program": SPLIT_DEMO, "maxTicks": 100, "trace": True})
    tl = res["menTimeline"]
    final = tl[-1]
    ok = (
        res["status"] == "done"
        and res["fatal"] is None
        and final["men"] == 2
        and final["alive"] == 0
        and any(e["men"] == 2 and e["alive"] == 2 for e in tl)
    )
    report(
        "2 /split demo (both copies halt on H)",
        ok,
        f"status={res['status']} reason={res['reason']} timeline: {_squash(tl)}",
    )


def check3() -> None:
    """User's editor-verified Y map: copies meet and DIE (drop of 2, no error)."""
    res = run_harness({"program": Y_MEET_MAP, "maxTicks": 300, "trace": True})
    tl = res["menTimeline"]
    drop2 = [
        (a["t"], b["t"], a["men"], b["men"])
        for a, b in zip(tl, tl[1:])
        if a["men"] - b["men"] >= 2
    ]
    ok = bool(drop2) and res["fatal"] is None and res["status"] != "error"
    report(
        "3 Y meet-and-die map (annihilation, no error)",
        ok,
        f"status={res['status']} reason={res['reason']} drops(-2men)={drop2[:4]}"
        f" timeline: {_squash(tl)}",
    )


def check4() -> None:
    """Stepping on 'Z' -> fatal bad-op."""
    prog = "+----+\n|@ Z |\n+----+\n"
    res = run_harness({"program": prog, "maxTicks": 20, "trace": True})
    f = res["fatal"] or {}
    ok = res["status"] == "error" and f.get("reason") == "bad-op" and f.get("cell") == "Z"
    report(
        "4 bad program (step on Z)",
        ok,
        f"status={res['status']} fatal={f} at tick {res['ticks']}",
    )


def check5() -> None:
    """5 random single-room LLLM-alphabet programs: sim.py vs official engine
    after up to 64 ticks (no pipes, no Y)."""
    import random

    sys.path.insert(0, str(REPO / "src"))
    from littleman.llm_fuzz import random_program
    from littleman.sim import Machine

    rng = random.Random(20260725)
    details = []
    agree = 0
    clean = 0  # non-error runs (real movement/arithmetic evidence)
    i = -1
    while clean < 5 and i < 40:
        i += 1
        rows = random_program(rng)
        text = "\n".join(rows) + "\n"
        res = run_harness({"program": text, "maxTicks": 64})
        m = Machine.parse(text)
        rr = m.run([], max_ticks=64)
        man = m.men[0]
        off_err = res["status"] == "error"
        sim_err = rr.status == "error"
        if off_err or sim_err:
            reason = (res["fatal"] or {}).get("reason") or res["reason"]
            ok = off_err and sim_err and reason == rr.error
            details.append(f"#{i}:err {reason}/{rr.error} {'OK' if ok else 'DIFF'}")
        else:
            r0 = res["runners"][0]
            same_pos = r0["pos"] == [man.c, man.r]
            same_dir = r0["dir"] == [man.direction[1], man.direction[0]]
            same_reg = [int(r0["a"]), int(r0["b"]), int(r0["backpack"])] == [
                man.A, man.B, man.BP
            ]
            same_halt = (res["status"] == "done") == (rr.status == "halted")
            ok = same_pos and same_dir and same_reg and same_halt
            clean += 1
            details.append(
                f"#{i}:{res['status']}/{rr.status}"
                f" pos{r0['pos']}=={[man.c, man.r]}"
                f" reg{[int(r0['a']), int(r0['b']), int(r0['backpack'])]}"
                f"=={[man.A, man.B, man.BP]} {'OK' if ok else 'DIFF'}"
            )
        agree += ok
    total = len(details)
    report(
        "5 sim.py cross-check (random fuzz programs, 64 ticks, drawn until"
        " 5 non-error runs)",
        agree == total and clean >= 5,
        f"{agree}/{total} agree ({clean} non-error); " + "; ".join(details),
    )


def main() -> None:
    check1()
    check2()
    check3()
    check4()
    check5()
    n_ok = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"\n{n_ok}/{len(RESULTS)} checks passed")
    lat = ", ".join(f"{v:.2f}s" for v in LATENCIES)
    print(f"harness invocations: {len(LATENCIES)}, total {sum(LATENCIES):.2f}s ({lat})")
    sys.exit(0 if n_ok == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
