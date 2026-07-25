# 20260725-memory-packed-candidate

- Status: stopped by liveness takeover
- Record owner: codex
- Work owner: claude
- Reviewer: codex
- Integrator: codex
- Problem: `memory` (`d0b34a23-67c1-4087-b88e-90a74404d50e`)
- Base main commit: `86ac36a010fa0d53ea947941b4c91fb1ac6cfbfa`
- Branch: `agent/claude`
- Progress lease: 15 minutes without concrete evidence
- Created UTC: 2026-07-25T08:10:44Z
- Last updated UTC: 2026-07-25T08:31:20Z

## Outcome

Build, measure, and hand off a real packed `memory_02` Little Man candidate
that improves measured local score over immutable `memory_01`.

## Exclusive write set

- `src/littleman/memory_packed.py`
- `tests/test_memory_packed.py`
- new `submissions/memory/memory_02.man`
- `reports/2026-07-25-memory-packed.md`
- `claude/`
- `coordination/status/claude.md`
- `coordination/messages/claude/`

The final `submissions/memory/variants.json`, shared state, and live-result
metadata remain integrator-owned unless Codex explicitly transfers them.

## Shared read-only paths

- `src/littleman/memory.py`
- `src/littleman/memory_packing_model.py`
- existing Memory tests
- `submissions/memory/memory_01.man`
- `submissions/memory/variants.json`
- `reports/2026-07-24-memory-compaction.md`
- `reports/2026-07-25-memory-packing-feasibility.md`
- generic simulator, canvas, parser, API, and package files

Claude may request an explicit path transfer if modifying a shared read-only
file becomes necessary.

## Do not touch

- `main`
- `codex/`
- Codex's Sudoku source, tests, artifacts, report, status, and messages
- `AGENTS.md`
- `docs/current-state.md`
- `.env`
- unrelated user files

## Deliverables

- New generator/module and exact generated `memory_02.man`.
- Directed signed-64 boundary coverage, public cases, deterministic randomized
  oracle cases, worst-shape capacity checks, and server-compatibility result.
- Exact hash, bytes, dimensions, footprint, capacities, per-case ticks,
  average ticks, local score, and comparison with `memory_01`.
- Pushed payload commit and immutable handoff message.

## Acceptance checks

- Generator output equals the checked-in artifact byte-for-byte.
- All public Memory cases and focused oracle/stress cases pass.
- Layout passes `littleman.server_compat`.
- Measured local score improves over `memory_01`.
- The handoff distinguishes measurements from projections and records failed
  alternatives.

## Contest authority

Read-only API access: allowed and required before a solution commit.

Contest submission: forbidden by both active goals.

## Handoff

Push the payload and handoff to `origin/agent/claude`. Codex repeats freshness
and risk-proportionate validation before integration.

## Liveness disposition

Claude acknowledged the task in local branch commit
`8eb52e9951ea0d084dd454368a96f0e60b39cbb9`, but no subsequent commit,
diff, result, narrowed blocker, message, or announced running job appeared
through `2026-07-25T08:31:20Z`. Codex issued the recorded 15-minute
stop/takeover. Claude's branch and clean worktree are preserved unchanged.

Continuation belongs to Codex task
`20260725-memory-packed-codex-takeover`, using disjoint source, test,
artifact, and report paths.
