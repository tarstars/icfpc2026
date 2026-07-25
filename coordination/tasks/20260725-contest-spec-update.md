# 20260725-contest-spec-update: recapture and audit live instructions

- Status: deferred
- Record owner: codex
- Work owner: codex
- Reviewer: Claude and user
- Integrator: codex
- Base main commit: `9c3a87cbacf96f0c6e3ac341d0b974844bf50515`
- Branch: `agent/codex-spec-update`
- Created UTC: 2026-07-25T15:01:48Z
- Last updated UTC: 2026-07-25T15:05:07Z

## Outcome

Independently recapture the updated live contest language reference, compare
it with the checked-in capture, document every semantic change, and update
integrator-owned reference/cookbook material without editing Claude-owned
paths.

## Write set

- `docs/language-reference.md`
- `docs/littleman-cookbook.md`
- one focused report under `reports/`
- this task and Codex-owned status/message bookkeeping

## Read-only inputs

- current live contest documentation
- `src/littleman/sim.py` and focused tests
- `origin/agent/claude:claude/spec-update-20260725.md`

## Acceptance checks

- Live source URL and capture time are recorded.
- Full old/new semantic diff is reduced to exact changed rules.
- Simulator behavior is checked against each changed rule.
- Cookbook claims distinguish newly specified facts from historical server
  observations.
- No solution or contest state changes.

## Contest authority

Read-only public contest documentation access is authorized. No contest API
mutation or submission is permitted.

## Deferral

The live bundle and `/api/v1/split/docs` were independently fetched and
Claude's two-delta report was read. No reference/cookbook file was changed.
The user then made Pathfinder P1 and `Y` simulator support P2; recapture is
deferred to P3 without releasing Codex ownership of the listed documentation
paths.
