# 20260725-pathfinder-machine: build, gate, and submit

- Status: active
- Record owner: codex
- Work owner: codex
- Reviewer: Claude
- Integrator: codex
- Problem: `pathfinder`
- Base main commit: `3473e7bf906eeb92ff594be5a0f7db180a252ace`
- Branch: `agent/codex-pathfinder`
- Created UTC: 2026-07-25T15:05:07Z
- Last updated UTC: 2026-07-25T16:10:00Z

## Outcome

Build a correctness-first Pathfinder Littleman machine using the released
bitboard design and distance-mod-3 frontier correction, validate it against
Claude's 7/7 reference plus generated adversarial games, run composite
preflight and freshness checks, then submit under the user's standing
authorization if every gate passes.

## Exclusive write set

- `src/littleman/pathfinder.py`
- `tests/test_pathfinder.py`
- `submissions/pathfinder/`
- `reports/2026-07-25-pathfinder.md`
- Codex task/status/message bookkeeping

## Read-only inputs

- `origin/agent/claude:claude/pathfinder-reference.py`
- `data/small/problems/pathfinder.json`
- shared simulator, canvas, preflight, API tooling, and documentation

## Acceptance gates

1. Generator artifact reproduction test.
2. All seven public games frame-exact against the independent reference.
3. Generated/adversarial games cover unreachable flags, tie-breaking, border
   masks, long paths, and distance-mod-3 selection.
4. `uv run python scripts/preflight.py <artifact> pathfinder` is ready.
5. Before solution commit/submission: fresh `origin/main` integration and
   live Pathfinder score/latest-submission query.
6. Submitted bytes and SHA-256 are preserved with the terminal JSON response.

## Contest authority

Standing user authorization covers one gated Pathfinder submission. Anything
failing a gate is not submitted.

## WIP checkpoint

The first generated bitboard machine parses and is frame-exact wherever it
finishes.  At commit time it passes five public cases; `the long way` and
`there and back again` reach the 15,000,000-tick cap.  It is therefore not a
submission candidate yet.  Current measurements and the next optimization
target are in `reports/2026-07-25-pathfinder.md`.
