# STATE — read this first after any context flush

Updated: 2026-07-25 morning (contest day 2 of 3).

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

## Active WIP (hand-off ready)

- Packet Reassembly: `tcp_01` is complete and passed 20/20 live at
  52,747,175. It proves the offset-window architecture but is worse than
  `tcp_00`; the ranked next steps are in `docs/alexey-tcp-handoff.md`.
  Separately, the current standings show a team best of 5,981,625.6 whose
  source and submission UUID are absent from Git and cannot be listed through
  the API. Recover that exact artifact in the web UI before another TCP
  submission.
- Plotter: `plotter_01` is a geometry-only 388x441 candidate. It passes all
  public cases and the deterministic 20-segment oracle locally, improving
  local score 32.98% over `plotter_00`; it has not been submitted.

## Contest clock

Lightning round ends 2026-07-25 12:00 UTC (scoreboard frozen 10:00–
14:00 UTC). Full contest ends 2026-07-27 12:00 UTC, final freeze from
10:00 UTC. Check live: `uv run icfpc-api clock`.

## Board (graded problems, best live submission)

Snapshot updated `2026-07-25T05:56:56Z`; every problem below passed all
private cases. Ranks are included because several earlier rank notes are now
stale.

| problem | live score | rank | notes |
|---|---:|---:|---|
| triangle | 832 | 1/189 | `triangle_04`; server-valid final wall step |
| memory | 91,372,247.625 | 42/109 | compact 46x47 `memory_01` |
| reverse | 472,345.6 | 52/104 | shrinking ring |
| sort | 1,455,739.72 | 26/71 | 19x19 `sort_03` |
| brackets | 7,473,269.23 | 38/61 | packed base-3 stack |
| tcp | 5,981,625.6 | 19/48 | counted artifact provenance missing; do not overwrite blindly |
| history | 7,921 | 27/94 | footprint-only |
| plotter | 75,794,498,065 | 37/43 | `plotter_00`; compact local candidate ready |
| gradebook | 104,303,579,599.6 | 25/37 | compact four-worker layout |
| matmul | 33,286,994,352 | 24/36 | compact nested ring |
| sudoku | 105,335,908,125.2 | 42/46 | parallel mask rings |
| subset-sum | 91,769,596,778,389.8 | 29/35 | meet-in-the-middle systolic sorters |

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
- Use `littleman.server_compat` for pre-submission judging. The base simulator
  is too permissive for shared-wall rooms and too strict for a final wall step
  after `s`; both differences are confirmed against the server.

## Completed since the previous state

- All twelve graded problems are solved.
- Memory `memory_01` passed 24/24 live and improved the accepted score to
  91,372,247.625. `claude/memory-compaction-handoff.md` is historical.
- Plotter, Grade Book, Matrix Multiply, Sudoku Auditor, and Subset Sum all
  have preserved accepted implementations and reports under `reports/`.
- Triangle `triangle_04` reached score 832 and rank 1 in the recorded
  standings snapshot.

## Priorities (my recommendation, in order)

1. Recover the exact 5,981,625.6 TCP artifact before making another TCP
   submission.
2. Submit the validated `plotter_01` geometry candidate after the mandatory
   pull and live-score check, if the user authorizes submission.
3. Optimize the weakest current ranks: Sudoku, Plotter, Subset Sum, and
   Matrix Multiply.
4. Continue TCP only from the measured plan in `docs/alexey-tcp-handoff.md`.
