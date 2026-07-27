#!/usr/bin/env python3
"""Certify the Rust engine (`littleman._fastsim_rust`) against the oracle.

The oracle is the organizers' own Go->WASM engine vendored in
`claude/official-sim/` -- NOT `sim.py`, `fastsim.py` or `server_compat.py`.
Those Python judges are known to be wrong: `server_compat` scored
`gpt_brackets_18` 9/9 while both the WASM and the contest server score it
7/9 ("wall"), and `sim.py` never implemented `Y` (split) at all.

Usage
-----
    uv run python scripts/rust_certify.py                      # everything
    uv run python scripts/rust_certify.py --problem brackets   # one problem
    uv run python scripts/rust_certify.py --artifact a.man --problem brackets
    uv run python scripts/rust_certify.py --verbose            # per-case rows

For every artifact and every public test case it runs

  * the oracle -- one fresh WASM session per case (public cases are
    INDEPENDENT runs; the site's editor chains them with ` / ` and stateful
    programs then diverge), and
  * the Rust engine, both entry points:
      v2 = `rustexec.run_official`   (semantics_version=2: `Y` enabled)
      v1 = `rustexec.CompiledMachine.run_rounds` (the legacy `_rust.run`
           path used by `rustexec.Machine`, no `Y`)

and compares pass/fail, the scoring tick, and the failure reason.

Scoring tick
------------
`judge.judge_case` scores a passing case with `RoundController
.last_output_tick`: the tick that produced the last expected value/frame,
which is generally EARLIER than the halt tick.  The oracle is therefore
bisected for the first tick at which the case is satisfied rather than
being read at halt time, so the two numbers are comparable.

Known-good calibration (both reproduced by this script):
    reverse_fresh_23.man  8/8, ticks 175 94 152 238 138 154 280 420
                          (avg 206.375, and it uses `Y`)
    gpt_brackets_18.man   7/9, `wall` at oracle ticks 66 and 146
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import threading
import time

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

PROBLEMS = REPO / "data" / "small" / "problems"
ENGINE = REPO / "claude" / "official-sim" / "engine.mjs"

# `submissions/<dir>` does not always equal `data/small/problems/<slug>`.
SLUG_ALIASES = {
    "history": "history-lesson",
    "sort": "sort-numbers",
    "llm": "little-little-man",
    "lllm": "little-little-little-man",
}

MAX_ARTIFACT_BYTES = 400_000
LFS_MAGIC = b"version https"

DRIVER_JS = r"""
// Persistent driver over the organizers' WASM engine: one JSON request per
// stdin line -> one JSON response per stdout line.  Boots the WASM once.
import { createInterface } from "node:readline";
import { bootEngine, parseResp } from "__ENGINE__";

const enc = (v) => (v == null ? "" : v.map((r) => r.join(" ")).join(" / "));
const eng = await bootEngine();

function open(req) {
  const rows = req.program.replace(/\n+$/, "").split("\n");
  const sess = eng.newSession();
  const st = parseResp(
    eng.load(
      sess,
      rows,
      enc(req.input),
      enc(req.expected),
      req.frames && req.frames.some((f) => f.length)
        ? JSON.stringify(req.frames)
        : ""
    )
  );
  return { sess, st };
}

// "the run has produced everything this case demands"
function done(st, nvals, nframes) {
  if (nvals > 0 && !st.outputSettled) return false;
  if (nframes > 0) {
    const fj = st.frameJudge;
    if (!fj || fj.mismatch || (fj.matched ?? 0) < nframes) return false;
  }
  return true;
}

function run(req) {
  const nvals = (req.expected ?? []).reduce((a, r) => a + r.length, 0);
  const nframes = (req.frames ?? []).reduce((a, r) => a + r.length, 0);
  const maxTicks = req.maxTicks ?? 1000000;
  const cap = req.chunk ?? 4096;
  let sess, st;
  try {
    ({ sess, st } = open(req));
  } catch (e) {
    return { ok: false, status: "load-error", reason: e.message };
  }
  let prev = st.step;
  let chunk = 8;
  let stalled = false;
  while (!st.halted && st.step < maxTicks && !done(st, nvals, nframes)) {
    prev = st.step;
    st = parseResp(eng.stepN(sess, Math.min(chunk, maxTicks - st.step), false));
    if (st.step === prev) {
      stalled = true;
      break;
    }
    chunk = Math.min(chunk * 2, cap);
  }
  const finished = done(st, nvals, nframes);
  const out = {
    ok: true,
    status: st.halted
      ? st.reason === "done"
        ? "done"
        : "error"
      : stalled
      ? "stalled"
      : finished
      ? "settled"
      : "tick-cap",
    halted: !!st.halted,
    reason: st.reason ?? null,
    fatal: st.fatal ?? null,
    ticks: st.step,
    output: (st.output ?? []).slice(0, 64),
    outputSettled: !!st.outputSettled,
    frameJudge: st.frameJudge ?? null,
    passed: finished && !st.fatal,
    settleTick: null,
  };
  eng.closeSession(sess);
  if (!out.passed || (nvals === 0 && nframes === 0)) return out;
  // Exact first satisfying tick: the predicate is monotone, so bisect
  // inside the bracket (prev, ticks] with fresh replays.
  let lo = prev, hi = st.step;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    const probe = open(req);
    const s2 = parseResp(eng.stepN(probe.sess, mid, false));
    const good = done(s2, nvals, nframes) && !s2.fatal;
    eng.closeSession(probe.sess);
    if (good) hi = mid;
    else lo = mid;
  }
  out.settleTick = hi;
  return out;
}

const rl = createInterface({ input: process.stdin });
for await (const line of rl) {
  if (!line.trim()) continue;
  let res;
  try {
    res = run(JSON.parse(line));
  } catch (e) {
    res = { ok: false, status: "driver-error", reason: String(e && e.message) };
  }
  // The Go/WASM runtime routes its own writes to fd 1, so a panic or a
  // stray print inside the engine would corrupt a bare JSON-per-line
  // protocol.  Tag our replies and let the reader skip everything else.
  process.stdout.write("@@RES@@" + JSON.stringify(res) + "\n");
}
process.exit(0);
"""

MARKER = "@@RES@@"


class Oracle:
    """Persistent Node process holding one booted WASM engine."""

    def __init__(self, workdir: pathlib.Path, timeout: float):
        self.path = workdir / "rust_certify_oracle.mjs"
        self.path.write_text(DRIVER_JS.replace("__ENGINE__", ENGINE.as_uri()))
        self.errlog = workdir / "rust_certify_oracle.err"
        self.timeout = timeout
        self.proc = None
        self.noise = []
        self._spawn()

    def _spawn(self):
        self.close()
        self.proc = subprocess.Popen(
            ["node", "--max-old-space-size=4096", str(self.path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.errlog.open("a"),
            text=True,
            bufsize=1,
        )

    def close(self):
        if self.proc is not None:
            try:
                self.proc.kill()
                self.proc.wait(timeout=5)
            except Exception:
                pass
            self.proc = None

    def ask(self, request: dict) -> dict:
        """Send one job; kill+respawn the engine if it exceeds the timeout."""
        killer = threading.Timer(self.timeout, self._kill_now)
        killer.start()
        line = ""
        del self.noise[:]
        try:
            self.proc.stdin.write(json.dumps(request) + "\n")
            self.proc.stdin.flush()
            while True:  # skip anything the WASM runtime itself printed
                line = self.proc.stdout.readline()
                if not line or line.startswith(MARKER):
                    break
                self.noise.append(line.rstrip()[:200])
        except (BrokenPipeError, ValueError, OSError):
            line = ""
        finally:
            killer.cancel()
        oom = any("out of memory" in n for n in self.noise)
        if not line or oom:
            self._spawn()
            if oom:
                # The vendored engine is a wasm32 Go binary: it snapshots
                # every step for `back()` and dies at the 4 GB heap limit
                # somewhere past ~1.2M ticks.  Nothing to do with Rust.
                return {"ok": False, "status": "oracle-oom",
                        "reason": "oracle-oom"}
            return {"ok": False, "status": "oracle-timeout", "reason": "timeout"}
        try:
            return json.loads(line[len(MARKER):])
        except json.JSONDecodeError:
            # A crashed or noisy engine must not abort the whole sweep.
            self._spawn()
            return {"ok": False, "status": "oracle-garbage",
                    "reason": line.strip()[:80]}

    def _kill_now(self):
        proc = self.proc
        if proc is not None:
            try:
                proc.kill()
            except Exception:
                pass


def rounds_of(case) -> list:
    if "rounds" in case:
        return case["rounds"]
    return [{"in": case.get("in", []), "out": case.get("out", [])}]


def oracle_request(text: str, rounds: list, max_ticks: int) -> dict:
    return {
        "program": text,
        "input": [[int(v) for v in rd.get("in", [])] for rd in rounds],
        "expected": [[int(v) for v in rd.get("out", [])] for rd in rounds],
        "frames": [list(rd.get("frames", [])) for rd in rounds],
        "maxTicks": max_ticks,
    }


def oracle_view(result: dict) -> dict:
    """Normalize the oracle answer to (passed, ticks, reason)."""
    if not result.get("ok"):
        view = {"passed": False, "ticks": None,
                "reason": result.get("status") or "oracle-error"}
        if view["reason"] == "load-error":
            # the loader's own words: these are the structural rules the
            # contest server enforces and our Python parser does not
            view["detail"] = str(result.get("reason"))[:90]
        return view
    if result["passed"]:
        return {"passed": True,
                "ticks": result.get("settleTick") or result["ticks"],
                "reason": None}
    fatal = result.get("fatal") or {}
    reason = fatal.get("reason") or result.get("reason") or result["status"]
    if result["status"] in {"tick-cap", "stalled"} and not fatal:
        reason = result["status"]
    return {"passed": False, "ticks": result["ticks"], "reason": reason}


def rust_v2(text: str, rounds: list, max_ticks: int) -> dict:
    """`rustexec.run_official` -- semantics_version=2, `Y` enabled."""
    from littleman import rustexec
    from littleman.judge import RoundController
    from littleman.sim import Machine

    try:
        machine = Machine.parse(text)
    except Exception as exc:  # parse errors are a real disagreement
        return {"passed": False, "ticks": None,
                "reason": f"parse:{type(exc).__name__}:{exc}"[:60]}
    controller = RoundController(rounds)
    if controller.done:
        return {"passed": True, "ticks": 0, "reason": None}
    try:
        res = rustexec.run_official(machine, controller=controller,
                                    max_ticks=max_ticks)
    except Exception as exc:
        return {"passed": False, "ticks": None,
                "reason": f"{type(exc).__name__}:{exc}"[:60]}
    status = "error" if res["error"] else (res["verdict"] or res["status"])
    if status == "passed":
        return {"passed": True, "ticks": controller.last_output_tick,
                "reason": None}
    reason = "wrong-output" if status == "failed" else (res["error"] or status)
    return {"passed": False, "ticks": res["ticks"], "reason": reason}


def rust_v1(compiled, index: int, rounds: list, max_ticks: int) -> dict:
    """The legacy `_rust.run` path behind `rustexec.Machine` (no `Y`)."""
    try:
        res = compiled.run_rounds(index, rounds, max_ticks)
    except Exception as exc:
        return {"passed": False, "ticks": None,
                "reason": f"{type(exc).__name__}:{exc}"[:60]}
    if res.status == "passed":
        return {"passed": True, "ticks": res.judged_ticks, "reason": None}
    reason = "wrong-output" if res.status == "failed" else (
        res.error or res.status)
    return {"passed": False, "ticks": res.ticks, "reason": reason}


def norm_reason(reason) -> str:
    """Both engines refuse to load some programs; only the wording differs."""
    reason = reason or ""
    if reason == "load-error" or reason.startswith("parse:"):
        return "load-error"
    return reason


UNAVAILABLE = {"oracle-oom", "oracle-timeout", "oracle-garbage",
               "oracle-error", "driver-error", "oracle-short"}


def classify(oracle: dict, rust: dict) -> str:
    if oracle["reason"] in UNAVAILABLE:
        return "oracle-unavailable"
    if oracle["passed"] != rust["passed"]:
        return "verdict"
    if not oracle["passed"]:
        if norm_reason(oracle["reason"]) != norm_reason(rust["reason"]):
            return "reason"
        if oracle["reason"] in {"tick-cap", "stalled"}:
            return "agree"  # neither engine ever finishes; the caps differ
        if oracle["ticks"] is None or rust["ticks"] is None:
            return "agree"
        delta = rust["ticks"] - oracle["ticks"]
        if delta == 0:
            return "agree"
        return "tick-off-by-one" if abs(delta) == 1 else "ticks"
    return "agree" if oracle["ticks"] == rust["ticks"] else "ticks"


RANK = {"oracle-unavailable": -1, "agree": 0, "tick-off-by-one": 1,
        "ticks": 2, "reason": 3, "verdict": 4}


def short(path: pathlib.Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def artifacts(args) -> list:
    if args.artifact:
        slug = args.problem[0] if args.problem else ""
        return [(pathlib.Path(a), slug) for a in args.artifact]
    found = []
    for path in sorted((REPO / "submissions").rglob("*.man")):
        slug = SLUG_ALIASES.get(path.parts[
            path.parts.index("submissions") + 1], None)
        if slug is None:
            slug = path.parts[path.parts.index("submissions") + 1]
        if args.problem and slug not in args.problem:
            continue
        if slug in args.skip_problem:
            continue
        size = path.stat().st_size
        if size > args.max_bytes:
            continue
        with path.open("rb") as handle:
            if handle.read(len(LFS_MAGIC)) == LFS_MAGIC:
                continue
        found.append((path, slug))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--artifact", action="append",
                        help="explicit .man path (repeatable)")
    parser.add_argument("--problem", action="append", default=[],
                        help="problem slug filter / override (repeatable)")
    parser.add_argument("--skip-problem", action="append", default=[],
                        help="problem slug to leave out (repeatable)")
    parser.add_argument("--max-ticks", type=int, default=0,
                        help="0 = the problem's tickCap, else 5,000,000")
    parser.add_argument("--oracle-max-ticks", type=int, default=1_200_000,
                        help="the WASM oracle dies at the wasm32 4 GB Go heap "
                             "past roughly this many ticks; cases needing more "
                             "are reported as uncertifiable, not as failures")
    parser.add_argument("--max-bytes", type=int, default=MAX_ARTIFACT_BYTES)
    parser.add_argument("--case-timeout", type=float, default=120.0)
    parser.add_argument("--skip-v1", action="store_true",
                        help="only certify run_official (semantics v2)")
    parser.add_argument("--verbose", action="store_true",
                        help="print every disagreeing case")
    parser.add_argument("--json", help="write the full per-case report here")
    args = parser.parse_args()

    from littleman import rustexec

    if not rustexec.HAVE_RUST:
        print("FATAL: littleman._fastsim_rust is not importable; build with")
        print("  cargo build --release --manifest-path rust/Cargo.toml")
        print("  cp rust/target/release/lib_fastsim_rust.so"
              " src/littleman/_fastsim_rust.so")
        return 2
    print(f"rust backend : {rustexec.backend()} (IR v{rustexec.IR_VERSION})")
    print(f"oracle       : {ENGINE}")

    workdir = pathlib.Path(os.environ.get("TMPDIR", "/tmp"))
    oracle = Oracle(workdir, args.case_timeout)
    specs = {}
    rows = []
    started = time.time()

    for path, slug in artifacts(args):
        if slug not in specs:
            spec_path = PROBLEMS / f"{slug}.json"
            if not spec_path.exists():
                print(f"  ?? no spec for {slug} ({path})")
                specs[slug] = None
            else:
                specs[slug] = json.loads(spec_path.read_text())
        spec = specs[slug]
        if spec is None:
            continue
        cap = args.max_ticks or spec.get("tickCap") or 5_000_000
        text = path.read_text()
        compiled = None
        if not args.skip_v1:
            try:
                compiled = rustexec.CompiledMachine(text)
            except Exception as exc:
                compiled = f"{type(exc).__name__}:{exc}"[:60]
        for index, case in enumerate(spec["publicTestData"]):
            rounds = rounds_of(case)
            ocap = min(cap, args.oracle_max_ticks)
            raw = oracle.ask(oracle_request(text, rounds, ocap))
            view_o = oracle_view(raw)
            view_2 = rust_v2(text, rounds, cap)
            # The oracle runs on a shorter leash than Rust (4 GB Go heap).
            # If it stopped at its own cap while Rust got further, the case
            # is uncertifiable rather than a disagreement.
            if (ocap < cap and not view_o["passed"]
                    and view_o["reason"] in {"tick-cap", "stalled"}
                    and view_o["ticks"] == ocap
                    and not (not view_2["passed"]
                             and view_2["reason"] in {"tick-cap", "stalled"})):
                view_o["reason"] = "oracle-short"
            if compiled is None:
                view_1 = None
            elif isinstance(compiled, str):
                view_1 = {"passed": False, "ticks": None, "reason": compiled}
            else:
                view_1 = rust_v1(compiled, index, rounds, cap)
            rows.append({
                "artifact": short(path),
                "problem": slug,
                "case": index,
                "oracle": view_o,
                "v2": view_2,
                "v1": view_1,
                "v2_class": classify(view_o, view_2),
                "v1_class": classify(view_o, view_1) if view_1 else None,
            })
        done = len({row["artifact"] for row in rows})
        worst = max((row["v2_class"] for row in rows[-len(
            spec["publicTestData"]):]), key=lambda c: RANK[c])
        print(f"  [{done:3}] {short(path):58} {worst:16}"
              f" ({time.time() - started:.0f}s)", flush=True)
        if args.json:  # survive a crash halfway through a long sweep
            pathlib.Path(args.json).write_text(json.dumps(rows))

    oracle.close()
    report(rows, args)
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(rows, indent=1))
    worst = max((RANK[row["v2_class"]] for row in rows), default=0)
    return 0 if worst == 0 else 1


def bucket(rows, key) -> None:
    """Print the artifact-level agreement table for one Rust entry point."""
    by_artifact = {}
    for row in rows:
        if row[key] is not None:
            by_artifact.setdefault(row["artifact"], []).append(row)
    buckets = {name: [] for name in RANK}
    partial = 0
    for name, group in sorted(by_artifact.items()):
        usable = [r for r in group if r[key] != "oracle-unavailable"]
        if len(usable) < len(group):
            partial += 1
        if not usable:
            buckets["oracle-unavailable"].append(name)
            continue
        buckets[max(usable, key=lambda r: RANK[r[key]])[key]].append(name)
    total = len(by_artifact)
    for name in sorted(RANK, key=RANK.get):
        if name == "oracle-unavailable":
            continue
        print(f"  {name:18} {len(buckets[name]):4}/{total} artifacts")
    cases = [row for row in rows if row[key] is not None]
    usable = [row for row in cases if row[key] != "oracle-unavailable"]
    agree = sum(1 for row in usable if row[key] == "agree")
    dead = len(buckets["oracle-unavailable"])
    print(f"  {'cases':18} {agree:4}/{len(usable)} agree exactly")
    if len(cases) != len(usable):
        print(f"  {'not certifiable':18} {len(cases) - len(usable):4}/"
              f"{len(cases)} cases the oracle could not run"
              f"  ({partial} artifacts partly, {dead} wholly)")


def report(rows, args) -> None:
    print("\n=== agreement: Rust run_official (v2, `Y` enabled) vs oracle ===")
    bucket(rows, "v2_class")
    if not args.skip_v1 and any(row["v1_class"] for row in rows):
        print("\n=== agreement: Rust legacy `run` (v1, no `Y`) vs oracle ===")
        bucket(rows, "v1_class")

    bad = [row for row in rows
           if row["v2_class"] not in {"agree", "oracle-unavailable"}]
    if bad:
        print(f"\n=== disagreeing cases (v2): {len(bad)} ===")
        pairs = {}
        for row in bad:
            pairs.setdefault((row["v2_class"], row["oracle"]["reason"],
                              row["v2"]["reason"]), []).append(row)
        for (kind, oreason, rreason), group in sorted(
                pairs.items(), key=lambda kv: -len(kv[1])):
            print(f"  {kind:16} oracle={oreason!s:22} rust={rreason!s:22}"
                  f"  x{len(group)}"
                  f"  e.g. {group[0]['artifact']}#{group[0]['case']}")
        if args.verbose:
            print()
            for row in bad:
                print(f"  {row['artifact']}#{row['case']:<2} {row['v2_class']:16}"
                      f" oracle={row['oracle']} rust={row['v2']}")

    skipped = [row for row in rows if row["v2_class"] == "oracle-unavailable"]
    if skipped:
        why = {}
        for row in skipped:
            why[row["oracle"]["reason"]] = why.get(row["oracle"]["reason"], 0) + 1
        print(f"\n=== cases the oracle could not judge: {len(skipped)} ===")
        for reason, count in sorted(why.items(), key=lambda kv: -kv[1]):
            print(f"  {reason:20} x{count}")


if __name__ == "__main__":
    sys.exit(main())
