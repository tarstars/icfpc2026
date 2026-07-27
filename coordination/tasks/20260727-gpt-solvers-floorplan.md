# 20260727-gpt-solvers-floorplan: solver-assisted TCP layout vertical slice

- Status: released (benchmark complete; live-score continuation superseded)
- Record owner: gpt
- Work owner: gpt
- Reviewer: codex
- Integrator: codex
- Problem: `tcp` / physical-synthesis tooling
- Base main commit: `e6ed1423a7fb0cda17d1f3db79e82e8831b08244`
- Branch: `agent/gpt-solvers-usage`
- Progress lease: 15 minutes without concrete evidence
- Created UTC: `2026-07-27T04:22:00Z`
- Last updated UTC: `2026-07-27T04:48:00Z`

## Outcome

Build an exact, reproducible macro-floorplanning slice for a known-good TCP
architecture and identify the next promotion gate.

## Result

The preserved recovered-TCP 38-square placement satisfies the model. HiGHS
proves a 35-square optimum with MIP gap 0.0 after endpoint-obstacle constraints
remove a false 33-square solution. The implementation, fixture, tests, and
limitations are preserved under `experiments/gpt-solvers-usage/`.

Detailed routing is deferred because synchronization showed the live TCP
lineage is already 30x30. A route for the old 35-square architecture cannot
improve the current score. The benchmark remains part of the solver regression
suite.

## Released write set

This task releases its TCP-specific continuation. The shared experiment/report
paths are immediately reclaimed by the separately recorded
`20260727-gpt-solvers-port-assignment` task; no other agent may infer ownership
from this release alone.

## Contest authority

No contest mutation occurred. Submission remains forbidden without separate
user authorization and submission-controller acceptance.

## Handoff

Implementation checkpoint `1a9b92c7c130ba3f17b2070ac65129947257cb6f` and
coordination checkpoint `43767334a601e7796d71e3cf213d601509fa53d4` preserve
the result. No integration is requested independently of the successor solver
checkpoint.
