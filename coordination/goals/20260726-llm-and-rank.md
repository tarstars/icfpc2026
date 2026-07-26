# GOAL: solve LLM, then buy rank on everything already solved

- Set: 2026-07-26T06:30Z
- Working deadline: **2026-07-27T09:00Z** (standings freeze 10:00Z, contest ends 12:00Z)
- Owner: Claude, on `agent/claude`. Codex works in parallel; see the protocol.

## Where we actually stand — measured, not guessed

Team **wheezards**, **22.86 of 32 points** across 16 graded problems.

**`icfpc-api standings` only works with a problem UUID.** Given a slug it
returns `{"rows": []}` silently, which is why every rank claim I made
before 06:20Z was "unmeasured". It is measurable. Use the UUID.

| problem | cases | rank | points | **available** | our score / best |
|---|---|---|---|---|---|
| little-little-man | 2/28 | 21/22 | 0.12 | **1.88** | 1x |
| sudoku-validity | 20/20 | 58/64 | 1.10 | **0.90** | 227,421x |
| pathfinder | 18/18 | 20/24 | 1.17 | 0.83 | 1,581x |
| matmul | 20/20 | 42/58 | 1.28 | 0.72 | 1,316x |
| subset-sum | 20/20 | 41/57 | 1.29 | 0.71 | **183,539,193,557x** |
| gradebook | 20/20 | 43/60 | 1.29 | 0.71 | 1,289x |
| plotter | 20/20 | 44/62 | 1.30 | 0.70 | 1,935x |
| reverse-a-list | 20/20 | 81/149 | 1.46 | 0.54 | 28x |
| brackets | 26/26 | 48/90 | 1.47 | 0.53 | 11,650x |
| snake | 17/17 | 16/37 | 1.58 | 0.42 | 22x |
| tcp | 20/20 | 32/78 | 1.60 | 0.40 | 18x |
| sort-numbers | 25/25 | 40/113 | 1.65 | 0.35 | 50x |
| history-lesson | 1/1 | 36/130 | 1.73 | 0.27 | 1x |
| lllm | 21/21 | 4/32 | 1.90 | 0.10 | 17x |
| memory | 24/24 | 12/153 | 1.93 | 0.07 | 619x |
| triangle | 19/19 | 1/239 | 2.00 | 0.00 | 1x |

`rankPoints = (n - rank) / (n - 1)`, so on a 149-team problem each place
is worth 0.0068 points and moving 81 -> 20 is worth **+0.41**.

**Correction to yesterday's handoff: pathfinder is SOLVED** — 18/18,
rank 20/24. Codex did it. It is not a zero.

## Priority 1 — LLM (1.88 points, the largest single item on the board)

We pass 2/28. Every other graded problem passes 100% of its cases, so
this is the only place where *pass* points are still available, and they
are worth far more than any rank work.

Increments, each submitted the moment it passes — this is what took LLLM
from 0 to 21/21 in one night:

1. **Multi-man, no pipes** — unlocks `pileup` and `bounce house` locally.
   In flight now.
2. **Pipes + `s`/`r`** — unlocks the remaining 11 local cases.

Watch the semantics that differ from LLLM (pinned in `llm.py`, the
validated reference — 24/24 public frame sequences):
tick order is *pipes advance, then every man executes, then every
non-blocked man advances*; a wall stops the **whole program** with every
man frozen and the one on the wall still drawn, and that tick completes
in full; `H` halts only its own man.

**Hard constraint: LLLM's 21/21 must never regress.** Same code. If
multi-man cannot be added without breaking single-man, stop and say so.

## Priority 2 — rank on problems already solved

The `our score / best` column is the instruction here. **Where we are
1,000x-227,421x off the best, the gap is not layout.** Last night's
presses bought 1.1x-6.3x by moving rooms around; nobody closes a 1,289x
gap that way. Those teams are running a different algorithm or a
fundamentally denser encoding. So:

- **Small problems (reverse-a-list 28x, tcp 18x, snake 22x, sort 50x):**
  we own these generators outright and may rewrite them, not just press
  them. On small machines **ticks dominate** — reverse-a-list is 256
  footprint x 1,845 ticks, and the best team's 17,093 implies roughly
  18x fewer ticks at a similar size. *Last night's finding that "the tick
  lever is a dud" applied only to big machines whose interiors were off
  limits to a press. It does not apply here.* Start with reverse-a-list:
  cheapest to iterate, 149 teams so each place is cheap, and the user
  flagged it.
- **Mid problems (sudoku 227,421x, brackets 11,650x, plotter 1,935x,
  pathfinder 1,581x, matmul 1,316x, gradebook 1,289x):** before touching
  these, spend a little time asking *what could possibly be 1,000x
  better* — measure where our ticks actually go on one case. A wrong
  algorithm cannot be pressed into a right one.
- **subset-sum:** the best team scores **500**. Ours is 91.8 trillion.
  That is not an optimization gap, it is a different program. Worth one
  focused hour of "what are they doing that we are not", but note one
  local judge run takes **15m25s**, so treat wall-clock as the binding
  constraint. Do not start a blind rewrite.
- Do not spend on **triangle** (already 1/239) or **memory**/**lllm**
  (0.07 and 0.10 left).

## Method that is now proven, and should be reused

- **Shrink the goal to one failing test case**, land it, submit, repeat.
  LLLM went 4/21 -> 10/21 -> 21/21 as separate submissions in one night.
- **Submit partial early.** Partial credit is per test case and
  `privateTestCount` is 0 on the hard problems.
- **Build a harness whose only job is to say where execution stalls.**
- **Keep the inner loop fast** — component + Python model, not full
  machine rebuilds.
- **Measure occupancy before any press** (matmul 43.9% -> -37%;
  gradebook 90.4% -> -8.8%).
- Every press clears a binding audit with **0 pipe-role diffs** and
  `room_ports.audit` margins >= 2.

## Rules that stay in force

- Verify in this tree before submitting — own pytest, own judge, own
  preflight — never on an agent's report alone.
- Submit only via
  `uv run icfpc-api --env-file ../icfpc2026/.env submit <problemUUID> <file> --confirm --wait`,
  **stdout redirected to the record file and stderr separately** (merged
  progress lines corrupted three records yesterday).
- `.man` files are immutable; a new attempt is a new `<slug>_NN.man`.
- Never edit `codex/`, Codex's status or messages, `AGENTS.md`,
  `docs/current-state.md`, `sim.py`, or variant catalogs.
- Push a checkpoint at least every 15 minutes.
- `data/small/problems` is a REDUCED copy; local pass counts understate.
- `atoi`, `hello-world`, `max-element`, `palette` are ungraded practice
  and return 403. Check `status` in the `problems` listing first.

## Definition of done

1. LLM passes materially more than 2/28, submitted.
2. At least three already-solved problems improved in rank, submitted.
3. Every claim in the final handoff carries a measured number, and
   anything unverified is labelled as such.
