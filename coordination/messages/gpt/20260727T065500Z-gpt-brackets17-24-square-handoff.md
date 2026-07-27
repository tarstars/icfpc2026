# handoff: `gpt_brackets_17` is a true 24x24 Brackets candidate

- From: gpt
- To: claude
- CC: alexey, codex
- Created UTC: `2026-07-27T06:55:00Z`
- Task: `20260727-gpt-brackets-24-square`
- Branch: `agent/gpt-solvers-usage`
- Requires acknowledgement: YES

## Exact candidate

```text
submissions/brackets/gpt_brackets_17.man
SHA-256 51a6219ee527d5607720a99a1401cba9d94de9579021d32f1a1ed79adbc72325
589 bytes
24x24, footprint 576
5 rooms / 6 pipes / 3 men
pipe lengths [2, 2, 2, 5, 39, 3]
```

Public result under server-compatible final-wall semantics:

```text
9/9
case ticks [242, 64, 100, 64, 144, 376, 132, 132, 2078]
average 370.22222222222223
score max(24,24)^2 * average = 213248.0
```

Comparison:

```text
brackets_11 local 276615.0       -> -22.908013%
gpt_brackets_15  233333.333333   ->  -8.608000%
```

## Why this is a solver result

The 25-square placement could not simply be squeezed. Two component variants
were synthesized first:

1. CLOSE shares its mismatched-close and unmatched-open result tail, removing
   one outer column and relying on the already server-proven final-wall drain.
2. OPEN routes end-of-stream through unused columns and the ordinary pair
   sender, removing one outer row.

A bounded same-wall port/placement search then fits the resulting variants into
a 24-square and shortens the state, transport, and input routes.

## Independent replay

```text
9,331 / 9,331 exhaustive strings over ()[]{}, lengths 0..5
10,000 / 10,000 deterministic random strings, lengths 0..64
random maximum 926 ticks, mean 108.314
```

Exact generation, SHA, parser structure, server layout, no shared walls,
exactly one input-adjacent pipe, and minimum two-cell pipe checks pass.

Reproduce:

```bash
PYTHONPATH=src uv run pytest -q -n 0 tests/test_gpt_brackets_24.py
PYTHONPATH=src uv run python scripts/preflight.py \
  submissions/brackets/gpt_brackets_17.man brackets
```

Please fetch this branch, repeat the repository-native replay and exact live
Brackets freshness check, then submit the pinned SHA if it still improves the
counted result. GPT made no contest API call.

The 24-square write set is released. I am moving to a separate 23-square
component-synthesis task without touching this immutable candidate.
