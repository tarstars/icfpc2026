# Task 20260802-chatgpt1-server-loader-validation

- Status: active
- Owner: chatgpt_1
- Reviewer/integrator: repository maintainer
- Base: `main` at branch creation
- Branch: `agent/chatgpt-1-server-loader-validation`

## Outcome

Consolidate the organizer-only loader rules in `littleman.server_compat` so one parser-like entry point rejects every preserved layout that was locally parseable but server-invalid:

- `submissions/reverse-a-list/reverse_02.man` — one-cell pipes;
- `submissions/reverse-a-list/reverse_03.man` — more than one pipe against the input-room wall;
- `submissions/sort/sort_05.man` — one-cell pipe;
- `submissions/triangle/triangle_03.man` — shared room wall / interrupted-pipe geometry.

The core simulator parser remains intentionally unchanged because the repository records divergences in both directions; strict organizer behavior belongs in the server-compatibility layer.

## Exclusive write set

- `src/littleman/server_compat.py`
- `tests/test_server_compat.py`
- `tests/test_server_compat_pipe_lengths.py`
- `reports/2026-08-02-chatgpt1-server-loader-validation.md`
- `coordination/status/chatgpt_1.md`
- `coordination/messages/chatgpt_1/20260802T*-20260802-chatgpt1-server-loader-validation-*.md`
- this task record

## Read-only dependencies

- `src/littleman/sim.py`
- `src/littleman/alexey_pipecheck.py`
- `scripts/preflight.py`
- preserved `.man` artifacts and submission responses

## Acceptance checks

1. A new `parse_server_compatible(text)` entry point returns a `Machine` for valid layouts.
2. The four preserved server-invalid layouts above raise `ServerCompatibilityError` through that entry point and through `validate_layout`.
3. Known fixed successors (`reverse_01`, `sort_06`, `triangle_04`) remain accepted.
4. Existing `find_shared_walls`, `validate_io_pipe_counts`, `validate_layout`, and judge APIs retain their public signatures.
5. No contest-side mutation and no integration into `main` by chatgpt_1.
