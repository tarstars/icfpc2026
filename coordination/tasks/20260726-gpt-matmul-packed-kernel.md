# 20260726-gpt-matmul-packed-kernel: verified packed MatMul kernel handoff

- Status: handoff ready; implementation write set released
- Record owner: gpt
- Work owner: gpt
- Reviewer: codex
- Integrator: codex
- Problem: `matmul`
- Base main commit: `36f4778deef6635314705b3d018568ee4969c24d`
- Branch: `agent/gpt`
- Progress lease: complete
- Created UTC: 2026-07-26T17:17:51Z
- Last updated UTC: 2026-07-26T17:25:00Z

## Outcome

Published an independently executable proof and implementation handoff for the
three-column packed Matrix Multiply kernel. This task is research-only: it does
not add or modify a numbered `.man` solution and does not change live metadata.

## Exclusive write set

Released after handoff:

- `reports/2026-07-26-gpt-matmul-packed-kernel.md`
- `experiments/gpt-matmul-packed/packed_matmul_reference.py`

GPT retains ownership only of:

- `coordination/tasks/20260726-gpt-matmul-packed-kernel.md`
- `coordination/status/gpt.md`
- `coordination/messages/gpt/`

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

## Acceptance evidence

Command run before publication:

```bash
python3 experiments/gpt-matmul-packed/packed_matmul_reference.py
```

Observed:

```text
packed three-lane MatMul reference: all tests passed
```

Established properties:

- Every generated result equals naive matrix multiplication.
- `16 * 199^2 < 2^20`, so each lane is carry-independent.
- The worst packed accumulator is strictly below `2^63`.
- No `.man` candidate or contest result is presented as validated by this task.

## Contest authority

Read-only API access: not needed for this research-only commit.

Contest submission: forbidden. A later solution task must perform the normal
freshness gate before committing or submitting any generated `.man` candidate.

## Handoff

- Payload commit: `5b85bb10dc2f74a358ec361f2dcf12efb725ea83`
- Handoff message commit: `384ab0cce27fff3bb8f66b85ee61f6d37c973ef1`
- Message: `coordination/messages/gpt/20260726T172500Z-20260726-gpt-matmul-packed-kernel-handoff.md`

Codex may integrate the research evidence or use it to assign a separate
solution task with live-state freshness checks and unique implementation paths.
