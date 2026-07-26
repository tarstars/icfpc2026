# 20260726-gpt-preserve-local-candidates: preserve validated `.man` candidates

- Status: active
- Record owner: gpt
- Work owner: gpt
- Reviewer: codex
- Integrator: codex
- Problems: `matmul`, `sudoku-validity`
- Base main commit: `36f4778deef6635314705b3d018568ee4969c24d`
- Branch: `agent/gpt`
- Progress lease: 15 minutes without concrete evidence
- Created UTC: `2026-07-26T17:42:55Z`
- Last updated UTC: `2026-07-26T17:42:55Z`

## Outcome

Preserve the exact bytes of two already locally validated candidates, together
with their reproduction scripts and benchmark evidence, so other agents can
review and promote them. This is a user-directed preservation task, not a live
submission or shared-catalog update.

## Exclusive write set

- `coordination/tasks/20260726-gpt-preserve-local-candidates.md`
- `coordination/status/gpt.md`
- `coordination/messages/gpt/`
- `experiments/gpt-submission-candidates/`
- `reports/2026-07-26-gpt-local-submission-candidates.md`

## Shared read-only paths

- `submissions/matmul/`
- `submissions/sudoku-validity/`
- `src/littleman/matmul*.py`
- `src/littleman/sudoku.py`
- problem fixtures and current reports/catalogues

## Do not touch

- `main`
- existing numbered `.man` files, terminal response JSON, or variant catalogues
- `docs/current-state.md`
- `codex/`, `claude/`, and other agents' status/message namespaces
- generic simulator, parser, canvas, package, lock, or API infrastructure

## Deliverables

- `experiments/gpt-submission-candidates/matmul_08.man` with SHA-256
  `6d77cb4dac845d620a3f39804c345cb818c17de3d7577af848bc0ea8a9cc685e`.
- `experiments/gpt-submission-candidates/sudoku_05_single_ring.man` with
  SHA-256 `16860f965aa0e57c1b2e031a6a650c3bde2ae195961e8a164a2fe8e1cc58b49d`.
- Exact generator/reproduction scripts and benchmark JSON.
- Focused report that distinguishes local measurements from live facts and
  states that the contest freshness gate was not available to GPT.
- Immutable handoff message to Codex, Claude, and Alexey.

## Acceptance checks

- Committed `.man` bytes hash exactly to the values above.
- Reproduction scripts emit byte-identical artifacts when run in the uploaded
  snapshot environment.
- Recorded public results are 7/7 for MatMul and 6/6 for Sudoku.
- Recorded directed tests are 35/35 for MatMul and 17/17 for Sudoku.
- `littleman.server_compat` and minimum-pipe checks are recorded as passed from
  the original local validation.
- No live score, hidden-case result, or submission ID is invented.

## Freshness limitation

GPT has GitHub access but no contest API connector or repository `.env`
execution path. Therefore these files are preserved under `experiments/`, not
promoted into shared submission catalogues. Codex must perform the mandated
fresh contest query before integration, renaming, or submission.

## Contest authority

Contest submission: forbidden. No contest-side mutation is authorized by this
task.

## Handoff

Push exact artifacts, scripts, benchmarks, report, status, and an immutable
message. Codex may perform the freshness gate and promote a candidate through a
separate solution task.
