# 20260725-coordination-two-agent-protocol

- Status: completed
- Record owner: codex
- Work owner: codex
- Reviewer: user
- Integrator: codex
- Problem: none
- Base main commit: `832ce90022da9010c299901df2748c9743c5845f`
- Branch: `main`
- Created UTC: 2026-07-25T07:38:24Z
- Last updated UTC: 2026-07-25T07:43:40Z

## Outcome

Establish a safe, repository-backed two-agent protocol, synchronization
artifacts, and a ready-to-paste onboarding prompt for the second agent.

## Exclusive write set

- `AGENTS.md`
- `docs/two-agent-protocol.md`
- `docs/current-state.md`
- `coordination/`
- `codex/state.md`
- `codex/decisions.md`
- `codex/validation.md`
- `codex/worklog.md`

## Shared read-only paths

- `src/`
- `tests/`
- `submissions/`
- `reports/`
- `claude/`

## Do not touch

- `.env`
- `claude/`
- unrelated untracked user files

## Deliverables

- Normative protocol and project-policy link.
- Task, status, message, and handoff templates.
- Initial per-agent status snapshots.
- Peer onboarding prompt.

## Acceptance checks

- `git diff --check`
- Internal path, role, ownership, and prompt consistency audit.

## Contest authority

Read-only API access: not needed.

Contest submission: forbidden; this is coordination-only work.

## Handoff

The user receives the prompt path and the key operating rules. Claude should
acknowledge onboarding through its own message namespace before accepting
implementation work.
