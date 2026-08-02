# Task 20260802-chatgpt1-server-loader-validation

- Status: complete; handoff ready
- Owner: chatgpt_1
- Reviewer/integrator: repository maintainer
- Base: `main` at branch creation
- Branch: `agent/chatgpt-1-server-loader-validation`
- Completed UTC: 2026-08-02T06:26:24Z

## Outcome

Consolidate the organizer-only loader rules in `littleman.server_compat` so one parser-like entry point rejects every preserved layout that was locally parseable but server-invalid:

- `submissions/reverse-a-list/reverse_02.man` — one-cell pipes;
- `submissions/reverse-a-list/reverse_03.man` — more than one pipe against the input-room wall;
- `submissions/sort/sort_05.man` — one-cell pipe;
- `submissions/triangle/triangle_03.man` — shared room wall / interrupted-pipe geometry.

The core simulator parser remains intentionally unchanged because the repository records divergences in both directions; strict organizer behavior belongs in the server-compatibility layer.

## Exclusive write set

- `src/littleman/server_compat.py`
- `src/littleman/alexey_pipecheck.py` (documentation synchronization only)
- `tests/test_server_compat.py`
- `tests/test_server_compat_pipe_lengths.py`
- `reports/2026-08-02-chatgpt1-server-loader-validation.md`
- `coordination/status/chatgpt_1.md`
- `coordination/messages/chatgpt_1/20260802T*-20260802-chatgpt1-server-loader-validation-*.md`
- this task record

## Read-only dependencies

- `src/littleman/sim.py`
- `scripts/preflight.py`
- preserved `.man` artifacts and submission responses

## Acceptance results

1. PASS — `parse_server_compatible(text)` returns the parsed `Machine` for valid layouts.
2. PASS — all four preserved server-invalid layouts raise `ServerCompatibilityError` through both the parser-like entry point and `validate_layout`.
3. PASS — `reverse_01`, `sort_06`, and `triangle_04` remain accepted; measured pipe lengths are `[2, 2, 2, 17]`, `[2, 3, 7, 17]`, and `[2, 2]`.
4. PASS — existing public function signatures are retained.
5. PASS — the legacy pipe-checker documentation now describes `validate_layout` as including the rule.
6. PASS — no contest-side mutation and no code integration into `main` by chatgpt_1.

Focused validation: exact changed files compiled; the new and expanded loader tests passed `13 passed, 1 deselected` in a local harness using the current room/pipe discovery routines and preserved artifacts. Full repository pytest was not available in this runtime; see the report for commands and limitations.
