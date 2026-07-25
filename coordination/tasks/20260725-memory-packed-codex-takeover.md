# 20260725-memory-packed-codex-takeover

- Status: active
- Record owner: codex
- Work owner: codex
- Reviewer: codex
- Integrator: codex
- Problem: `memory` (`d0b34a23-67c1-4087-b88e-90a74404d50e`)
- Base main commit: `f8f448529df0629207154aef9b20d369245a9e45`
- Branch: `main`
- Progress lease: four-hour goal session
- Created UTC: 2026-07-25T08:31:20Z
- Last updated UTC: 2026-07-25T08:31:20Z

## Outcome

Continue the packed Memory prototype after the Claude liveness takeover.
Build and measure a real machine using three values per signed-64 word, and
retain it only if it improves measured local score over immutable
`memory_01`.

## Exclusive write set

- `src/littleman/memory_packed_codex.py`
- `tests/test_memory_packed_codex.py`
- new `submissions/memory/memory_03.man`
- `reports/2026-07-25-memory-packed-codex.md`
- `coordination/status/codex.md`
- `coordination/messages/codex/`
- `codex/`
- final integrator-owned Memory catalog and shared-state updates

## Shared read-only paths

- `src/littleman/memory.py`
- `src/littleman/memory_packing_model.py`
- existing Memory tests
- `submissions/memory/memory_01.man`
- `submissions/memory/variants.json`
- `reports/2026-07-24-memory-compaction.md`
- `reports/2026-07-25-memory-packing-feasibility.md`
- generic simulator, canvas, parser, API, and package files

## Do not touch

- `claude/`
- the stopped Claude paths `src/littleman/memory_packed.py`,
  `tests/test_memory_packed.py`, `submissions/memory/memory_02.man`, and
  `reports/2026-07-25-memory-packed.md`
- `.env`
- unrelated user files

## Acceptance checks

- Generator output equals the checked-in artifact byte-for-byte.
- All public Memory cases and deterministic randomized oracle cases pass.
- Signed-64 extremes and all field positions are covered.
- Ring and route capacities cover worst-case streams.
- Layout passes `littleman.server_compat`.
- Exact hash, bytes, dimensions, footprint, per-case ticks, average ticks,
  local score, and comparison with `memory_01` are recorded.

## Contest authority

Read-only API access is allowed and required before a solution commit.
Contest submission is forbidden by the active goal.

## Handoff

Codex integrates and pushes a validated `memory_03`, or records the smallest
reproducible machine-level blocker and releases the task.
