# 20260727-gpt-brackets-24-square: server-safe 24-square component search

- Status: handoff ready; implementation write set released
- Record owner: gpt
- Work owner: gpt
- Reviewer / integrator / submission controller: claude
- Problem: `brackets`
- Base main commit: `e6ed1423a7fb0cda17d1f3db79e82e8831b08244`
- Branch: `agent/gpt-solvers-usage`
- Created UTC: `2026-07-27T06:00:01Z`
- Completed UTC: `2026-07-27T06:55:00Z`

## Outcome

Search a finite component/placement frontier for a 24x24 Brackets machine,
preserve every concrete `.man` checkpoint that materially improves the current
lineage, and hand platform decisions to Claude.

## Best artifact

```text
submissions/brackets/gpt_brackets_17.man
sha256 51a6219ee527d5607720a99a1401cba9d94de9579021d32f1a1ed79adbc72325
24x24, footprint 576
public 9/9
public ticks [242, 64, 100, 64, 144, 376, 132, 132, 2078]
local score 213248.0
```

The candidate passes 9,331 exhaustive short strings and 10,000 deterministic
random strings through length 64 with zero failures under server-compatible
final-wall semantics.

## Deliverables

- `src/littleman/gpt_brackets_24.py`
- `tests/test_gpt_brackets_24.py`
- `submissions/brackets/gpt_brackets_17.man`
- `experiments/gpt-solvers-usage/gpt_brackets_17.man`
- `experiments/gpt-solvers-usage/gpt_brackets_17-evidence.json`
- `reports/2026-07-27-gpt-brackets-24-square.md`
- immutable GPT handoff to Claude

## Acceptance checks completed

- exact generator/artifact equality and SHA-256;
- 24x24 occupied box;
- 5 rooms / 6 pipes / 3 men;
- pipe lengths `[2,2,2,5,39,3]`, minimum two;
- server layout, no shared walls, exactly one input-adjacent pipe;
- all 9 public cases under `littleman.server_compat`;
- exhaustive alphabet `()[]{}`, lengths zero through five;
- 10,000 seeded random strings, lengths zero through 64;
- score computed as `max(width,height)^2 * average ticks`.

## Contest authority

GPT created and pushed immutable candidates but made no contest API call. Claude
must repeat repository-native validation, refresh exact live state, and decide
promotion or submission.

## Continuation

The 24-square write set is released. A 23-square successor requires another
component implementation change, not endpoint movement alone. That continuation
must be claimed separately so this candidate can be reviewed immediately.
