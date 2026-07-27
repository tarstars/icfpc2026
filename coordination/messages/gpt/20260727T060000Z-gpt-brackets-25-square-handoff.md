# handoff: solver-guided 25-square Brackets lineage

- From: gpt
- To: codex
- CC: claude, alexey
- Created UTC: `2026-07-27T06:00:00Z`
- Task: `20260727-gpt-brackets-25-square`
- Branch: `agent/gpt-solvers-usage`
- Commit: `93f80d3b1703f22c88b105374a42ee1ce3c09942`
- Requires acknowledgement: yes

## Best candidate

```text
submissions/brackets/gpt_brackets_15.man
SHA-256 826553c4a58fd1ef83f81e8b05e9c3d54b575f2030d89c566cd5d9a99c09e605
25x25, footprint 625
rooms/pipes/men 5/6/3
pipe lengths [2, 2, 2, 10, 42, 2]
public 9/9
public ticks [246, 58, 106, 70, 146, 380, 136, 136, 2082]
local score 233333.3333333333
```

The same locally reconstructed current simulator reproduces checked-in
`brackets_11` at local score `276615.0`; the candidate is 15.646898% lower.
The candidate also passed 9,331 exhaustive length-0..5 strings, 425 directed
boundary cases, and 10,000 seeded random length-0..64 cases with zero failures.
Logical operation-to-pipe role counts by room pair equal `brackets_11`; no wall
cells are shared and exactly one pipe runs against the input.

## Independent gates before any platform action

GPT has no contest credential access and made no platform mutation. Before
integration or submission, independently:

```bash
PYTHONPATH=src uv run pytest -q -n 0 tests/test_gpt_brackets_25.py
PYTHONPATH=src uv run python scripts/preflight.py \
  submissions/brackets/gpt_brackets_15.man brackets
```

Fetch and integrate current `origin/main`, query the exact live Brackets score
and latest submission state, inspect the branch diff, and verify the pinned
artifact hash. Codex or the current submission controller decides whether the
candidate is safe and profitable to submit.

## Continuation

The 25-square write set is released. GPT has separately claimed a 24-square
component/placement search so review of this candidate does not block further
contest work.
