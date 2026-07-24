# STATE — read this first after any context flush

Updated: 2026-07-24 late (contest day 1 of 3).

## Read order for a fresh session

1. This file.
2. `docs/littleman-cookbook.md` — ALL verified idioms, layout rules,
   debug ladder, submission workflow. Non-negotiable reading before
   touching any .man design.
3. If working plotter: `claude/plotter-plan.md` (complete spec).
   If building tooling: `docs/toolchain-plan.md` (levels, APIs, build
   order — levels 2+3 are quick pure-checker wins, do them before
   the next machine).
   `docs/synthesis-stack.md` — top-down compiler-stack analysis
   (HLS/place-and-route framing, latency-insensitivity, netlist
   schema, soft-core vs synthesis fork); meets toolchain-plan at the
   netlist. Near-term actionable piece: the semi-automatic compactor.
4. `docs/language-reference.md` only for spec disputes.

## Contest clock

Lightning round ends 2026-07-25 12:00 UTC (scoreboard frozen 10:00–
14:00 UTC). Full contest ends 2026-07-27 12:00 UTC, final freeze from
10:00 UTC. Check live: `uv run icfpc-api clock`.

## Board (graded problems, best live submission)

| problem   | status | live score | ours? | notes |
|-----------|--------|-----------|-------|-------|
| triangle  | 19/19  | 1053      | claude | at proven floor, done |
| memory    | 24/24  | 43.8M     | claude | v1; compaction is the biggest single win available (footprint 4489 = 67²; ~40-wide target ≈ 2.8× better) |
| reverse   | 25?/   | 1.95M     | claude | shrinking ring; fine |
| sort      | 25/25  | 3.46M     | claude | sort_02 ring; teammate's pipeline superseded |
| brackets  | 26/26  | 7.47M     | claude | packed base-3 stack |
| tcp       | 20/20  | 20.0M     | codex  | paired-value ring |
| history   | 1/1    | 7921      | codex  | footprint-only |
| plotter   | UNSOLVED | —       | —     | display infra DONE; machine spec ready in plotter-plan.md; plotter.py = broken sketch, rewrite |
| gradebook | UNSOLVED | —       | —     | ring of (subject,student,grade)? read spec first |
| matmul    | UNSOLVED | —       | —     | ring storage + nested loops; big |
| sudoku    | UNSOLVED | —       | —     | 81 values, 27 group-sum/set checks; bitmask-in-64bit per group looks right |
| subset-sum| UNSOLVED | —       | —     | n small? 15M tick cap hints brute-force enumeration via binary counter + x-loop |

Practice: max-element solved (10/10, no submission possible).

## Ground truth (unchanged)

- Repo `~/prj/icfpc2026`; my area `claude/`; NEVER touch `codex/`
  (teammate works in parallel — pull before starting, expect their
  uncommitted files, commit only your own).
- `.env` (mode 600) holds team API key. Submit ONLY via
  `uv run icfpc-api submit <problemId> <file> --confirm --wait`,
  redirect stdout to a file to keep the submission id.
- Problem ids/slugs: `uv run icfpc-api problems`. Specs cached in
  `data/small/problems/*.json`.
- Versioning: .man files immutable; new attempt = `<slug>_NN.man` +
  variants.json entry. See any submissions/*/README.md.
- Simulator is trustworthy: 7 problems went to the server on first
  try after local green. If sim and server ever disagree, STOP and
  fix the sim first.

## In progress

Plotter: infra (display parse/semantics/frame-judge) merged and
green (72 tests). Machine not started beyond broken sketches.
Next concrete step = step 1 of plotter-plan.md build order.

## Priorities (my recommendation, in order)

1. Plotter via plotter-plan.md (2 points at stake, plan is ready).
2. Sudoku Auditor / Grade Book (likely ring + streaming compare,
   reuse cookbook idioms; read specs).
3. Memory compaction (known ~2.5-3× score win, pure layout work).
4. Subset Sum (needs algorithm thought; 15M cap).
5. Matmul last (biggest machine).
