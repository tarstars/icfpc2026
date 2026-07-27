# 20260727-gpt-sudoku-tagged-update-loop: loop the three mask updates

- Status: active
- Record owner: gpt
- Work owner: gpt
- Reviewer: codex
- Integrator: codex
- Problem: `sudoku-validity`
- Base main commit: `e6ed1423a7fb0cda17d1f3db79e82e8831b08244`
- Branch: `agent/gpt-sudoku-loop`
- Progress lease: 15 minutes without concrete evidence
- Created UTC: `2026-07-27T03:45:00Z`
- Last updated UTC: `2026-07-27T03:45:00Z`

## Outcome

Replace the three unrolled copies of the accepted single-ring Sudoku mask-update
controller with one tagged loop, preserving the 27-mask state representation and
all ring protocols. Produce an exact generated candidate and independent local
evidence for Codex to freshness-gate and promote.

## Exclusive write set

- `coordination/tasks/20260727-gpt-sudoku-tagged-update-loop.md`
- `coordination/status/gpt.md`
- `coordination/messages/gpt/`
- `experiments/gpt-sudoku-loop/`
- `reports/2026-07-27-gpt-sudoku-tagged-loop.md`

## Shared read-only paths

- `experiments/gpt-submission-candidates/`
- `submissions/sudoku-validity/`
- `src/littleman/sudoku.py`
- `src/littleman/gradebook.py`
- `src/littleman/alexey_stairfold.py`
- `src/littleman/alexey_squeeze.py`
- problem fixtures and accepted Sudoku reports/catalogues

## Do not touch

- `main`
- existing numbered `.man` files, response JSON, or variant catalogues
- `codex/`, `claude/`, `alexey/`, and other agents' status/message namespaces
- generic simulator, parser, canvas, package, lock, or contest API infrastructure

## Deliverables

- Deterministic generator for the tagged-loop architecture.
- Exact candidate under `experiments/gpt-sudoku-loop/`.
- Public, directed, random-prefix, layout, pipe-length, and byte-reproduction evidence.
- Exact dimensions, ticks, footprint, score, SHA-256, and comparison with `sudoku_05`.
- Immutable handoff to Codex, with Claude and Alexey copied.

## Acceptance checks

- Generator output is byte-identical to the committed candidate.
- All six public cases pass.
- Directed valid-grid, shuffled-prefix, and row/column/box duplicate workloads pass.
- Layout passes `littleman.server_compat`; every pipe has at least two cells.
- The state ring remains 27 masks in canonical row/column/box order.
- Local footprint-tick score improves over exact accepted `sudoku_05`.
- Local, projected, and live facts remain explicitly separate.

## Contest authority

Read-only contest API: unavailable to GPT.

Contest submission: forbidden on this branch. Codex must perform the mandatory
GitHub/live-score freshness gate before promotion or submission.

## Handoff

Push the generator, exact artifact, test harness, benchmark JSON, focused report,
status, and immutable handoff. Codex reviews and may promote through a separate
release task.