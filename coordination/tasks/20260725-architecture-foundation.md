# 20260725-architecture-foundation: Littleman synthesis foundation

- Status: completed
- Record owner: codex
- Work owner: codex
- Reviewer: user and high-level peer models
- Integrator: codex
- Problem: none
- Base main commit: 47c4fa20780d908699a43cbc811543aa37d51e33
- Branch: main
- Progress lease: not applicable
- Created UTC: 2026-07-25T12:50:00Z
- Last updated UTC: 2026-07-25T14:13:05Z

## Outcome

Establish a repository-backed architecture discussion for a component language,
component factory, Rust optimization toolchain, large-program synthesis flow,
and YT-backed search.

## Exclusive write set

- `docs/architecture/introduction.md`
- `docs/architecture/codex_*.md`
- Codex-owned coordination and bookkeeping paths

## Shared read-only paths

- Existing source, tests, reports, contest documentation, and solution
  artifacts used as architectural evidence

## Do not touch

- `claude/`
- `docs/architecture/claude_*.md`
- Semester 4 solution paths assigned to Claude agents

## Deliverables

- The user's introduction preserved verbatim
- Codex-prefixed architecture notes
- Explicit open questions for review by other high-level models
- A staged roadmap whose early milestones produce measurable value

## Acceptance checks

- The notes distinguish measured project facts from proposals.
- Component contracts include semantics, protocol, timing, capacity, and
  physical port geometry.
- The contest plan preserves Python parsing as authoritative and introduces a
  Rust IR executor only after a measured need.
- YT work is local-first and limited to reproducible, shardable CPU work
  projected above roughly five local minutes, with compact records and safe
  credential handling.

## Contest authority

Read-only API access: not needed.

Contest submission: forbidden; this is a brainstorming task.

## Handoff

Claude's five deltas were reviewed and endorsed with an IR-completeness gate.
The reconciled contest decisions are recorded in
`docs/architecture/codex_03_rust_toolchain.md` and
`docs/architecture/codex_06_yt_search.md`.
