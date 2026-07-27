"""Submission database and the candidate comparator that prevents our worst bug.

Three times today a candidate was judged against the wrong number, in both
directions:

* I told gpt their Reverse farm's break-even box was 20.8. It was 16 — I
  had compared their PUBLIC-case ticks against a live average derived from
  the HIDDEN set.
* gpt recommended submitting a 20-square after comparing its public local
  score against `84,423.95`, which is the accepted machine's live hidden
  score. They caught it themselves and retracted.
* I submitted a Brackets candidate on a 9/9 from `preflight.py`; the server
  returned 19/26 with two wall failures, because our judge over-accepts.

The pattern is always the same: **a number measured one way compared
against a number measured another way.** Discipline has not fixed it, so
this makes the correct comparison the easy one.

    uv run python scripts/subdb.py build
    uv run python scripts/subdb.py show
    uv run python scripts/subdb.py compare <candidate.man> <problem-slug>

`compare` measures the candidate AND the currently-live artifact with the
SAME judge, in the same run, and predicts the live score from their ratio.
It refuses to print a verdict any other way.

The judge is the organizers' own WASM (`scripts/wasm_judge.py`), which
matched the contest server exactly on both a failing machine (7/9, wall)
and a passing control (9/9 -> 26/26) where `server_compat` said 9/9 for
both. `preflight.py` remains useful and faster for parse/layout/pipe
checks; it is not a submission gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
DB_PATH = REPO / "data" / "submissions.json"
PROBLEM_DIR = REPO / "data" / "small" / "problems"


def git(*args: str) -> str:
    out = subprocess.run(["git", *args], cwd=REPO, capture_output=True,
                         text=True, timeout=180)
    return out.stdout if out.returncode == 0 else ""


def refs() -> list[str]:
    return [r for r in git("for-each-ref", "--format=%(refname:short)",
                           "refs/remotes", "refs/heads").split()
            if not r.endswith("/HEAD")]


def geometry(text: str) -> tuple[int, int]:
    lines = text.split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    return max((len(line.rstrip()) for line in lines), default=0), len(lines)


def build() -> dict:
    """Collect every submission response recorded anywhere in the repo.

    Records live on many branches -- codex alone left them across 20+ -- so
    a single-branch scan silently misses most of the history. That is the
    same blind spot that hid an unsubmitted artifact worth a rank on tcp.
    """
    records: dict[str, dict] = {}
    for ref in refs():
        for path in git("ls-tree", "-r", "--name-only", ref).splitlines():
            if not (path.startswith("submissions/")
                    and path.endswith("-submit.json")):
                continue
            raw = git("show", f"{ref}:{path}")
            if not raw.strip():
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if data.get("score") is None:
                continue                      # rejected: keep the file, not the row
            parts = path.split("/")
            problem = parts[1]
            name = parts[-1].replace("-submit.json", "")
            key = f"{problem}/{name}"
            if key in records:
                continue
            records[key] = {
                "problem": problem,
                "artifact": name,
                "score": data["score"],
                "cases_passed": data.get("casesPassed"),
                "cases_total": data.get("casesTotal"),
                "width": data.get("width"),
                "height": data.get("height"),
                "submission_id": data.get("id"),
                "created": data.get("createdAt"),
                "seen_on": ref,
            }
    return records


def load() -> dict:
    if DB_PATH.exists():
        return json.loads(DB_PATH.read_text())
    return {}


def save(records: dict) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    DB_PATH.write_text(json.dumps(records, indent=2, sort_keys=True) + "\n")


def best_per_problem(records: dict) -> dict[str, dict]:
    """The live artifact for each problem: only the BEST submission counts."""
    best: dict[str, dict] = {}
    for row in records.values():
        problem = row["problem"]
        if problem not in best or row["score"] < best[problem]["score"]:
            best[problem] = row
    return best


# problem directory name -> the slug the API and data files use
SLUG = {"sort": "sort-numbers", "lllm": "little-little-little-man",
        "llm": "little-little-man", "history": "history-lesson",
        "sudoku-validity": "sudoku-validity", "reverse-a-list": "reverse-a-list"}


def slug_for(problem_dir: str) -> str:
    return SLUG.get(problem_dir, problem_dir)


def find_artifact(problem: str, name: str) -> str | None:
    """The artifact text, from the working tree or any ref."""
    local = REPO / "submissions" / problem / f"{name}.man"
    if local.exists():
        text = local.read_text()
        if not text.startswith("version https"):     # git-lfs pointer
            return text
    for ref in refs():
        text = git("show", f"{ref}:submissions/{problem}/{name}.man")
        if text and not text.startswith("version https"):
            return text
    return None


def wasm_measure(path: pathlib.Path, slug: str, max_ticks: int) -> dict | None:
    """Public-case measurement under the organizers' engine."""
    out = subprocess.run(
        ["uv", "run", "python", str(REPO / "scripts" / "wasm_judge.py"),
         str(path), slug, "--max-ticks", str(max_ticks)],
        cwd=REPO, capture_output=True, text=True, timeout=900)
    passed = total = None
    avg = None
    for line in out.stdout.splitlines():
        if line.strip().startswith("cases"):
            frac = line.split(":")[1].strip()
            passed, total = (int(v) for v in frac.split("/"))
        elif line.strip().startswith("score"):
            avg = float(line.split("avgTicks")[1].split()[0].replace(",", ""))
    if passed is None or avg is None:
        return None
    return {"passed": passed, "total": total, "avg_ticks": avg}


def compare(candidate: pathlib.Path, slug: str, max_ticks: int) -> int:
    records = load() or build()
    problem_dir = next((d for d in {r["problem"] for r in records.values()}
                        if slug_for(d) == slug), slug)
    live = best_per_problem(records).get(problem_dir)
    if live is None:
        print(f"no recorded submission for {problem_dir}; run `build` first")
        return 1

    live_text = find_artifact(problem_dir, live["artifact"])
    if live_text is None:
        print(f"cannot materialise the live artifact "
              f"{problem_dir}/{live['artifact']}.man (git-lfs pointer?)")
        return 1

    scratch = candidate.parent / f"_live_{live['artifact']}.man"
    scratch.write_text(live_text)

    print(f"problem  : {slug}")
    print(f"live      : {live['artifact']}  score {live['score']:,.0f}  "
          f"{live['cases_passed']}/{live['cases_total']}")
    print("measuring BOTH under the organizers' WASM (same judge, same run)")

    live_m = wasm_measure(scratch, slug, max_ticks)
    cand_m = wasm_measure(candidate, slug, max_ticks)
    scratch.unlink(missing_ok=True)
    if live_m is None or cand_m is None:
        print("measurement failed; refusing to guess")
        return 1

    live_box = max(geometry(live_text))
    cand_box = max(geometry(candidate.read_text()))
    live_public = live_box ** 2 * live_m["avg_ticks"]
    cand_public = cand_box ** 2 * cand_m["avg_ticks"]

    print(f"  live      {live_box:>4}^2 x {live_m['avg_ticks']:>10,.3f} "
          f"= {live_public:>16,.2f}   {live_m['passed']}/{live_m['total']}")
    print(f"  candidate {cand_box:>4}^2 x {cand_m['avg_ticks']:>10,.3f} "
          f"= {cand_public:>16,.2f}   {cand_m['passed']}/{cand_m['total']}")

    if cand_m["passed"] != cand_m["total"]:
        print("\nVERDICT  : DO NOT SUBMIT -- the candidate does not pass every "
              "public case under the real engine")
        return 1

    ratio = live_public / cand_public if cand_public else 0.0
    predicted = live["score"] / ratio if ratio else float("inf")
    print(f"\n  ratio     {ratio:.4f}x   predicted live score "
          f"{predicted:,.0f}  (live is {live['score']:,.0f})")
    # break-even box, the number people keep deriving by hand and getting wrong
    breakeven = (live_public / cand_m["avg_ticks"]) ** 0.5
    print(f"  break-even box for these ticks: {breakeven:.2f} "
          f"(candidate is {cand_box})")

    if ratio > 1.0:
        print("\nVERDICT  : SUBMIT -- better than live on a like-for-like "
              "public measurement")
        return 0
    print("\nVERDICT  : do not submit -- worse than live. Only the best "
          "submission counts, so it would not hurt, but it will not help.")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build", help="rebuild the database from every ref")
    sub.add_parser("show", help="the live artifact per problem")
    cmp_parser = sub.add_parser("compare", help="candidate vs live, same judge")
    cmp_parser.add_argument("candidate")
    cmp_parser.add_argument("problem", help="slug, e.g. sort-numbers")
    cmp_parser.add_argument("--max-ticks", type=int, default=1_000_000)
    args = parser.parse_args()

    if args.command == "build":
        records = build()
        save(records)
        print(f"{len(records)} scored submissions across "
              f"{len({r['problem'] for r in records.values()})} problems "
              f"-> {DB_PATH.relative_to(REPO)}")
        return 0
    if args.command == "show":
        records = load() or build()
        best = best_per_problem(records)
        print(f"{'problem':22} {'artifact':26} {'score':>18} {'cases':>8} {'box':>5}")
        for problem in sorted(best):
            row = best[problem]
            box = max(row["width"] or 0, row["height"] or 0)
            cases = f"{row['cases_passed']}/{row['cases_total']}"
            print(f"{problem:22} {row['artifact']:26} {row['score']:>18,.0f} "
                  f"{cases:>8} {box:>5}")
        return 0
    return compare(pathlib.Path(args.candidate), args.problem, args.max_ticks)


if __name__ == "__main__":
    sys.exit(main())
