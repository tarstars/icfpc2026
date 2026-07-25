# 20260725-yt-five-minute-preference: reconcile compute policy

- Status: completed
- Record owner: codex
- Work owner: codex
- Reviewer: user
- Integrator: codex
- Base main commit: `bccc9f9b0eaa34626d4bc08781201cdba5858d9b`
- Branch: `agent/codex-yt-policy`
- Created UTC: 2026-07-25T14:57:58Z
- Completed UTC: 2026-07-25T14:57:58Z

## Outcome

Record the user's clarification that roughly five local minutes is the
preferred point to evaluate YT, not a hard execution cutoff, and reconcile
the authoritative root and storage policies with the architecture decision.

## Write set

- `AGENTS.md`
- `docs/storage-and-compute.md`
- `codex/instructions.md`
- this task and Codex-owned status/message bookkeeping

## Acceptance checks

- Both authoritative policy files use the same five-minute preference.
- The language preserves local judgment for interactive work and YT setup
  overhead.
- The instruction audit marks the prior one-hour/five-minute conflict
  resolved.
- No solution or contest state is changed.

## Contest authority

No contest API call or mutation is required; this is a policy-only change.
