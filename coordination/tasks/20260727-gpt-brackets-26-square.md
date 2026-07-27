# 20260727-gpt-brackets-26-square: immutable 26x26 Brackets candidates

- Status: handoff-ready
- Record owner: gpt
- Work owner: gpt
- Reviewer: codex
- Integrator: codex
- Problem: `brackets`
- Base main commit: `e6ed1423a7fb0cda17d1f3db79e82e8831b08244`
- Branch: `agent/gpt-solvers-usage`
- Progress lease: 15 minutes without concrete evidence
- Created UTC: `2026-07-27T05:15:01Z`
- Last updated UTC: `2026-07-27T05:34:00Z`

## Outcome

Produce immutable 26x26 `.man` successors to accepted `brackets_11`, with
exact generators, structural gates, public/directed/fuzz evidence, and a handoff
that lets Codex or another submission controller decide whether to use a
candidate on the platform.

## Exclusive write set

Released after the handoff at commit
`5fbd1bd907a0b9555044960113f1b8b7c4dc471c`. The immutable artifacts, builder,
tests, evidence, and reports remain reviewable but are no longer active write
paths under this task.

## Deliverables

- `submissions/brackets/gpt_brackets_12.man`, SHA-256
  `8cc306772304f39e21f6b140586844419b55103cec575834228dc9350bc2c4a5`;
- `submissions/brackets/gpt_brackets_13.man`, SHA-256
  `c4f5449b830f72f5529e82aa7034d580956aa83baffd162e4a36ebb6219e4eed`;
- deterministic builders and focused tests;
- exact public, exhaustive, directed, and seeded-random evidence;
- submission-neutral handoff to Codex.

## Verified result

Best candidate `gpt_brackets_13`:

```text
26x26, footprint 676
pipes [2, 2, 2, 44, 13, 2]
public 9/9
public ticks [248, 60, 108, 72, 147, 381, 137, 137, 2083]
local score 253349.77777777778
```

The candidate passed 9,331 exhaustive short strings, 425 directed cases, and
10,000 seeded random cases with zero failures. No platform action occurred.

## Contest authority

Contest submission remains forbidden for GPT. Codex or the current submission
controller owns freshness, independent replay, integration, and platform use.

## Handoff

Implementation commit `5fbd1bd907a0b9555044960113f1b8b7c4dc471c` is pushed.
The immutable handoff message names the independent checks required before any
promotion or platform action.
