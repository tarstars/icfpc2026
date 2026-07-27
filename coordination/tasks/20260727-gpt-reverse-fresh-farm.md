# 20260727-gpt-reverse-fresh-farm: multi-round Y reversal below live score

- Status: active
- Record owner: gpt
- Work owner: gpt
- Reviewer/integrator/submission controller: claude
- Problem: `reverse-a-list`
- Base main commit: `e6ed1423a7fb0cda17d1f3db79e82e8831b08244`
- Branch: `agent/gpt-reverse-fresh`
- Progress lease: 15 minutes without concrete evidence
- Created UTC: `2026-07-27T04:45:00Z`
- Last updated UTC: `2026-07-27T04:45:00Z`

## Outcome

Build or rigorously reject a reusable multi-round `Y`-spawned Reverse machine.
The preferred architecture reads `n`, spawns exactly `n` fresh workers, assigns
one list value to each, and turns inherited backpack counts into reverse-order
send times. Fresh workers eliminate the fixed-farm rotation/reset problem.

## Authoritative constraints

`data/small/problems/reverse-a-list.json` states `1 <= n <= 16`; a 17-token
round is the length prefix plus 16 values. Therefore at most 16 value workers
are required.

## Hard score gate

Project scoring is:

```text
max(width, height)^2 * average ticks
```

The current live result is 84,423.95. No candidate is useful unless its exact
local/public score credibly beats that value; practical target is max dimension
20 or less. Stop early if geometry cannot reach the gate.

## Exclusive write set

- `coordination/tasks/20260727-gpt-reverse-fresh-farm.md`
- `coordination/status/gpt.md`
- `coordination/messages/gpt/`
- `experiments/gpt-reverse-fresh/`
- `reports/2026-07-27-gpt-reverse-fresh.md`

## Shared read-only paths

- `experiments/gpt-reverse-y/`
- `submissions/reverse-a-list/`
- Reverse fixtures and reports
- `src/littleman/split_probe.py`
- `claude/official-sim/`

## Do not touch

- `main`
- existing numbered `.man`, response JSON, or variant catalogues
- Alexey's Reverse files and message/status namespace
- other agents' active Memory, TCP, Pathfinder, LLLM, History, and submission paths
- generic simulator/parser/package/lock/API infrastructure

## Deliverables

- Exact event/timing model for dynamic spawning and reverse send order.
- Deterministic `.man` generator and candidate if the score gate is reachable.
- Organizer-WASM validation for every `n=1..16` and all eight public multi-round
  cases.
- Dimensions, public ticks, exact score, SHA-256, structure/layout/pipe gates.
- Immutable handoff to Claude or an early negative-result release.

## Acceptance checks

- Exact output for every one-round length 1..16 with distinct values.
- Exact output for all public multi-round workloads without reset.
- No hidden workers from a previous round can consume a later round's values.
- Official organizer WASM and repository judge agree where both support `Y`.
- Every pipe has at least two cells and server layout passes.
- Candidate score is strictly below 84,423.95 using `docs/grading.md`.

## Contest authority

GPT will not submit. Claude is the sole submission controller and must perform
freshness, independent validation, immutable naming, and terminal-result
preservation.
