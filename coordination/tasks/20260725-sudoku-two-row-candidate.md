# 20260725-sudoku-two-row-candidate

- Status: completed
- Record owner: codex
- Work owner: codex
- Reviewer: codex
- Integrator: codex
- Problem: `sudoku-validity` (`f66c928f-3369-4870-9153-8b20cafc2ecd`)
- Base main commit: `86ac36a010fa0d53ea947941b4c91fb1ac6cfbfa`
- Branch: `main`
- Progress lease: four-hour goal session
- Created UTC: 2026-07-25T08:10:44Z
- Last updated UTC: 2026-07-25T08:29:19Z

## Outcome

Turn the measured 306-square two-row Sudoku packing bound into a real,
generated, server-compatible candidate that improves measured local score over
immutable `sudoku_00`.

## Exclusive write set

- `src/littleman/sudoku.py`
- `tests/test_sudoku.py`
- `submissions/sudoku-validity/`
- `reports/2026-07-25-sudoku-two-row.md`
- `coordination/status/codex.md`
- `coordination/messages/codex/`
- `codex/`
- final integrator-owned shared state and catalog updates

## Shared read-only paths

- `src/littleman/canvas.py`
- `src/littleman/gradebook.py`
- `src/littleman/matmul.py`
- `src/littleman/server_compat.py`
- `data/small/problems/sudoku-validity.json`
- `reports/2026-07-24-sudoku-auditor.md`
- `reports/2026-07-25-tcp-transfer-audits.md`

## Do not touch

- `claude/`
- Claude's Memory source, tests, artifacts, report, status, and messages
- `.env`
- unrelated untracked user files

## Deliverables

- A new generated `sudoku_01.man`, retained only if it improves local score.
- Exact generator regression and layout/capacity assertions.
- Public, deterministic valid-prefix, row/column/box duplicate, and
  server-compatibility validation.
- A focused report and immutable variant catalog entry.

## Acceptance checks

- Generator output equals the checked-in artifact byte-for-byte.
- All six public cases pass.
- Existing seeded and directed adversarial cases pass.
- Layout passes `littleman.server_compat`.
- Exact SHA-256, bytes, dimensions, footprint, per-case ticks, average ticks,
  local score, parent, and measured comparison are recorded.

## Contest authority

Read-only API access: allowed and required before a solution commit.

Contest submission: forbidden by the active goal.

## Handoff

Codex integrates and pushes the exact validated state to `main`, or records a
specific negative result if no working two-row candidate improves
`sudoku_00`.

## Result

Retained `sudoku_01` at 286×285 and local score 42,411,416,857.33333,
59.15% below `sudoku_00`. The artifact reproduces exactly, all focused tests
pass, and the live counted result remains unchanged. It was integrated in
commit `b9174c96e8bffb501a244429ca46912f33e653fc`. No submission was created.
