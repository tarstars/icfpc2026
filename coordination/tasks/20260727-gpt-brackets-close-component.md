# 20260727-gpt-brackets-close-component: synthesize narrower CLOSE variants

- Status: active
- Record owner: gpt
- Work owner: gpt
- Reviewer / integrator / submission controller: claude
- Problem: `brackets`
- Branch: `agent/gpt-solvers-usage`
- Created UTC: `2026-07-27T08:02:00Z`
- Progress lease: 15 minutes without concrete pushed evidence

## Outcome

Synthesize one or more behaviorally equivalent CLOSE room variants with outer
width at most 21, then determine whether the component library can compose a
22x22 whole machine. Preserve a negative certificate if the bounded search
proves the current control-flow template cannot contract.

## Write set

- `experiments/gpt-solvers-usage/brackets_close_*.py`
- `experiments/gpt-solvers-usage/brackets_close_variants.json`
- `src/littleman/gpt_brackets_close.py`
- `tests/test_gpt_brackets_close.py`
- future immutable Brackets candidate/evidence paths only after a distinct
  write-set message
- focused report plus GPT task/status/messages

All existing `.man` files and component modules are read-only.

## Contract

CLOSE consumes the same two logical incoming streams and must emit byte-exact
traces on the same two logical outgoing streams for every reachable component
state. A retained variant must record:

- outer width/height and occupied cells;
- logical port roles and admissible same-wall endpoint families;
- per-transaction latency and steady-state behavior;
- exact or randomized trace-equivalence evidence;
- binding constraints for each `r` and `s` cell.

## Solver

Use bounded state-space search over instruction-cell relocations and path
rewrites, with the existing room as a semantic oracle. The objective is
lexicographic:

1. outer width <= 21;
2. preserve or reduce hot-path ticks;
3. minimize occupied cells and route complexity;
4. retain multiple Pareto shapes rather than one winner.

The whole-machine score remains
`max(width,height)^2 * average ticks`; no variant is promoted unless the
composed candidate beats exact local score 201842.88888888888.

## Coordination

Claude owns generic room/layout infrastructure and every contest mutation. This
task stays in GPT component experiment paths and uses no shared solver files.
