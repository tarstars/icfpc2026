# claude_34: priorities re-derived from points, not factors

Written 2026-07-26 16:40Z, 17.4h to freeze, after reviewing
`REVOLUTIONARY_OPTIMIZATION_ROADMAP.md` (in the codex-snake-components
worktree). That document's diagnosis is right and its arithmetic checks
out; its ORDERING optimises the wrong quantity.

## What I verified in it

- The matmul packed-lane bound holds exactly: `16 * 199^2 = 633,616 <
  2^20 = 1,048,576`, and the 3-lane accumulator maxes at 6.967e17
  against the 9.223e18 signed limit. The packed outer product is sound.
- Its central claim matches my own independent measurements: L0/L1 work
  (placement, squeeze, staircase folds) delivered 1.1x-6.3x here and
  cannot reach 100x; the mid-size problems sit 268x-227,000x from the
  leaders, which is an architecture gap, not blank cells.

## The correction: factors are not points

Rank points are `(teams beaten) / (other teams)`, so a factor's value
depends entirely on the local density of the field. Converting the
roadmap's targets through the live ladder:

| problem | +10x | +100x | +1000x | max available |
|---|---|---|---|---|
| **plotter** | **+0.287** | +0.487 | +0.688 | 0.688 |
| **tcp** | **+0.297** | +0.297 | +0.297 | 0.297 |
| **snake** | **+0.268** | +0.429 | +0.429 | 0.429 |
| matmul | +0.147 | +0.382 | +0.691 | 0.691 |
| gradebook | +0.147 | +0.397 | +0.691 | 0.721 |
| sudoku | +0.078 | +0.195 | +0.325 | 0.857 |
| subset-sum | +0.061 | +0.091 | +0.258 | 0.712 |

Consequences that invert the roadmap's sequence:

- **plotter returns twice as much at 10x as matmul does** — and the
  roadmap's own plotter section is the cheapest work in the document
  (replace the roomy FSM with 2-3 hand-sized racetracks, 20-80 ticks per
  pixel instead of hundreds).
- **tcp saturates at +0.297 and gets there by 10x.** Small machine,
  fully understood, and alexey's `> s U d m ^` send-then-read relay loop
  is waiting to be applied to it.
- **subset-sum is the worst target on the board**: 100x buys +0.091.
  The roadmap ranks it 4th; it belongs last. Its field is compressed —
  everyone there is far from the leaders.
- **sudoku has the most available (0.857) and nearly the least
  reachable** (100x -> +0.195). Available != reachable.

## Priority order for the remaining 17 hours

Everything below assumes the same gates as always; nothing ships without
preflight, binding audit, capacity proof and judge equality.

1. **Finish and bank what is running.** k-ring sort (~+0.15 if it fits
   22x22), history 81-82x82 (+0.105 to +0.126), solver M2 on plotter/tcp
   (+0.05). Combined ~+0.33 at low risk, and all three are past their
   design phase. **Do not start a rewrite while these are unbanked.**
2. **plotter racetrack** — the roadmap's best points-per-effort item by a
   wide margin (+0.287 at 10x). Only if a slot frees with >6h left; it
   is a controller rewrite, not a press.
3. **tcp relay loop** — cheap, bounded, +0.297 ceiling reached at 10x.
   Alexey offered the loop shape and the lane is unclaimed.
4. **Endgame sweep at ~07:30Z** — mandatory. Seven problems sit within
   1.03x of the next place up, and the field drifts ~0.1 points per half
   day, so this is both offence and drift defence.

Explicitly deferred to post-contest, with the roadmap as the plan:
matmul packed lanes, gradebook packed record ring, sudoku nine-word
state, pathfinder policy BFS, subset-sum sharding. Each is a genuine
100x-1000x design; none is a 17-hour job with three agents already
committed.

## What to build above the solver stack, later

The roadmap's tooling layer is the right superstructure and correctly
places CP-SAT AFTER the architecture exists: ProcessNetworkIR (processes,
FIFO capacities, initiation interval, sequential/tiled/`Y` variants), a
packed-kernel verifier (signed-64 bit-vector semantics, exhaustive
bounds plus randomized equivalence), a component characteriser keeping a
Pareto family rather than one winner, and — the piece I would add first
because it is cheapest and would have redirected today — a **score
feasibility gate that starts from a points target and derives the legal
(max-dim, ticks) pairs before any room work begins.**
