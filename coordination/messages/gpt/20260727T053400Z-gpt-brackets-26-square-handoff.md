# handoff: solver-guided 26-square Brackets lineage

- From: gpt
- To: codex
- CC: claude, alexey
- Created UTC: `2026-07-27T05:34:00Z`
- Task: `20260727-gpt-brackets-26-square`
- Branch: `agent/gpt-solvers-usage`
- Commit: `5fbd1bd907a0b9555044960113f1b8b7c4dc471c`
- Requires acknowledgement: yes

## Best candidate

```text
submissions/brackets/gpt_brackets_13.man
SHA-256 c4f5449b830f72f5529e82aa7034d580956aa83baffd162e4a36ebb6219e4eed
26x26, footprint 676
rooms/pipes/men 5/6/3
pipe lengths [2, 2, 2, 44, 13, 2]
public 9/9
public ticks [248, 60, 108, 72, 147, 381, 137, 137, 2083]
local score 253349.77777777778
```

Local replay also passed 9,331 exhaustive length-0..5 strings, 425 directed
boundary cases, and 10,000 random length-0..64 cases, seed `2026072703`, with
zero failures. Logical operation-to-pipe role counts by room pair equal
`brackets_11`; no shared walls and exactly one pipe runs against the input.

## Review and freshness gates

GPT cannot access the contest credentials or the native checkout. Before
integration or submission, independently:

```bash
PYTHONPATH=src uv run pytest -q -n 0 tests/test_gpt_brackets_26.py
PYTHONPATH=src uv run python scripts/preflight.py \
  submissions/brackets/gpt_brackets_13.man brackets
```

Fetch/integrate current `origin/main`, query the exact live Brackets score and
latest submission, inspect the branch diff, and verify the pinned artifact
hash. No platform mutation occurred.

## Continuation

The 26-square write set is released. I have separately claimed a 25-square
successor task so this handoff can be reviewed without blocking continued work.
