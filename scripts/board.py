"""Coordinator's board: every graded problem, our rank, and what a move is worth.

Written when codex ran out of tokens and coordination moved here. The point
is to answer one question fast -- *where is the next point* -- because with
hours left, effort spent on a problem where we are already rank 3 is effort
stolen from one where we are rank 81.

Two things the API makes easy to get wrong, both learned the hard way:

- `standings` takes the problem **UUID**, not the slug. A slug returns an
  empty row list rather than an error, which reads exactly like "we have no
  submission" and cost us hours once already.
- Our own row carries no "this is you" flag. We locate it by matching the
  score of a submission we own (`ANCHOR`), then reuse the resulting teamId
  everywhere. Passing --team skips that.

Scoring, for reading the `gain` column: each problem is worth 2 points,
`casesPassed/casesTotal` for correctness plus `(n-rank)/(n-1)` for rank. So
the value of climbing is set by *how crowded the neighbourhood is*, not by
how much the score improves -- on a dense problem a 2% score cut can jump
twenty ranks, and on a sparse one halving the score can be worth nothing.
"""

from __future__ import annotations

import argparse
import bisect
import json
import subprocess
import sys

ENV = "../icfpc2026/.env"
# a submission we own, used only to recognise our own row in the standings
ANCHOR = ("matmul", 5931034965.900001)


def api(*args: str) -> object:
    """One CLI call. stderr is left attached so failures stay visible."""
    out = subprocess.run(
        ["uv", "run", "icfpc-api", "--env-file", ENV, *args],
        capture_output=True, text=True, timeout=300)
    if out.returncode != 0:
        return None
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return None


def graded_problems() -> list[dict]:
    problems = api("problems") or []
    return [p for p in problems if p.get("status") == "graded"]


def scored_rows(rows: list[dict]) -> list[dict]:
    """Rows that actually placed. A row with rank None never passed."""
    return sorted((r for r in rows if r.get("rank") is not None),
                  key=lambda r: r["rank"])


def find_team(problems: list[dict]) -> str | None:
    """Identify us by the score of a submission we know we own."""
    slug, score = ANCHOR
    for problem in problems:
        if problem["slug"] != slug:
            continue
        table = api("standings", problem["id"]) or {}
        for row in table.get("rows", []):
            if row.get("score") is not None and abs(row["score"] - score) < 1:
                return row["teamId"]
    return None


def gain_curve(scores: list[float], rank: int, total: int) -> list[tuple]:
    """What each better rank is worth, and the score needed to reach it.

    `scores` is every placed score ascending. Rank r needs a score just under
    the incumbent at r, so the target is that incumbent's score.
    """
    out = []
    for target in (rank - 1, rank - 2, rank - 3, max(1, rank // 2), 1):
        if target < 1 or target >= rank or any(target == t for t, _, _ in out):
            continue
        need = scores[target - 1]
        points = (rank - target) / (total - 1) if total > 1 else 0.0
        out.append((target, need, points))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--team", help="our teamId; found automatically if omitted")
    parser.add_argument("--detail", action="store_true",
                        help="show the climb curve for each problem")
    args = parser.parse_args()

    problems = graded_problems()
    if not problems:
        print("no graded problems returned -- API down or unreleased?")
        return 1

    team = args.team or find_team(problems)
    if not team:
        print("could not identify our team; pass --team")
        return 1

    print(f"{'problem':22} {'rank':>10} {'cases':>7} {'score':>18} "
          f"{'pts':>6}  {'crowding: ranks per 1% score cut':>10}")
    print("-" * 92)

    report = []
    for problem in sorted(problems, key=lambda p: p["slug"]):
        table = api("standings", problem["id"]) or {}
        rows = scored_rows(table.get("rows", []))
        if not rows:
            continue
        total = len(rows)
        mine = next((r for r in rows if r["teamId"] == team), None)
        if mine is None:
            print(f"{problem['slug']:22} {'ABSENT':>10} "
                  f"{'-':>7} {'-':>18} {'0.000':>6}   <-- unsubmitted, 2 pts on the table")
            report.append((problem, None, total, None))
            continue

        rank, score = mine["rank"], mine["score"]
        scores = [r["score"] for r in rows]
        # how many ranks a 1% score improvement would buy, right here
        better = bisect.bisect_left(scores, score * 0.99)
        density = rank - better - 1
        frozen = " FROZEN" if table.get("frozen") else ""
        print(f"{problem['slug']:22} {f'{rank}/{total}':>10} "
              f"{mine['casesPassed']}/{mine['casesTotal']:<5} {score:>18,.0f} "
              f"{mine['points']:>6.3f}   {density:>3} ranks{frozen}")
        report.append((problem, mine, total, scores))

    if args.detail:
        for problem, mine, total, scores in report:
            if mine is None:
                continue
            print(f"\n{problem['slug']} -- rank {mine['rank']}/{total}")
            for target, need, points in gain_curve(scores, mine["rank"], total):
                factor = mine["score"] / need if need else float("inf")
                print(f"   rank {target:>3}: need score <= {need:>16,.0f} "
                      f"({factor:>6.2f}x better)  -> +{points:.3f} pts")

    total_points = sum(m["points"] for _, m, _, _ in report if m)
    print(f"\ntotal points on graded problems: {total_points:.3f} "
          f"of {2 * len(report)} possible")
    return 0


if __name__ == "__main__":
    sys.exit(main())
