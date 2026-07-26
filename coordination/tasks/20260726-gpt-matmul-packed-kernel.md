# 20260726-gpt-matmul-packed-kernel: verified packed MatMul kernel handoff

- Status: active
- Record owner: gpt
- Work owner: gpt
- Reviewer: codex
- Integrator: codex
- Problem: `matmul`
- Base main commit: `36f4778deef6635314705b3d018568ee4969c24d`
- Branch: `agent/gpt`
- Progress lease: 15 minutes without concrete evidence
- Created UTC: 2026-07-26T17:17:51Z
- Last updated UTC: 2026-07-26T17:17:51Z

## Outcome

Publish an independently executable proof and implementation handoff for the
three-column packed Matrix Multiply kernel. This task is research-only: it does
not add or modify a numbered `.man` solution and does not change live metadata.

## Exclusive write set

- `coordination/tasks/20260726-gpt-matmul-packed-kernel.md`
- `coordination/status/gpt.md`
- `coordination/messages/gpt/`
- `reports/2026-07-26-gpt-matmul-packed-kernel.md`
- `experiments/gpt-matmul-packed/packed_matmul_reference.py`

## Shared read-only paths

- `docs/REVOLUTIONARY_OPTIMIZATION_ROADMAP.md`
- `reports/2026-07-24-matrix-multiply.md`
- `src/littleman/matmul.py`
- `src/littleman/matmul_ring.py`
- `src/littleman/matmul_press.py`
- `submissions/matmul/`

## Do not touch

- `main`
- `docs/current-state.md`
- existing submission artifacts, responses, and variant catalogs
- `codex/`, `claude/`, and `coordination/messages/{codex,claude,alexey}/`
- generic simulator, parser, canvas, package, and API infrastructure

## Deliverables

- Executable Python reference for three independent 20-bit output lanes.
- Exact signed-64 and no-cross-lane-carry bounds.
- Directed extreme tests and 5,000 deterministic random matrix tests.
- Focused architecture handoff with one-lane and multi-lane acceptance gates.
- Immutable handoff message to Codex, Claude, and Alexey.

## Acceptance checks

- `python3 experiments/gpt-matmul-packed/packed_matmul_reference.py` prints
  `packed three-lane MatMul reference: all tests passed`.
- Every generated result equals naive matrix multiplication.
- `16 * 199^2 < 2^20`, so each lane is carry-independent.
- The worst packed accumulator is strictly below `2^63`.
- No `.man` candidate or contest result is presented as validated by this task.

## Contest authority

Read-only API access: not needed for this research-only commit.

Contest submission: forbidden. A later solution task must perform the normal
freshness gate before committing or submitting any generated `.man` candidate.

## Handoff

Push the exact report, executable reference, status, and immutable handoff on
`agent/gpt`. Codex reviews and may integrate or use the result to assign a
separate implementation task with its own solution freshness checks.
