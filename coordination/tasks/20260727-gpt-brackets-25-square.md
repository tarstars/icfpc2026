# 20260727-gpt-brackets-25-square: fold terminal paths into 25x25 candidates

- Status: handoff-ready
- Record owner: gpt
- Work owner: gpt
- Reviewer: codex
- Integrator: codex
- Problem: `brackets`
- Base main commit: `e6ed1423a7fb0cda17d1f3db79e82e8831b08244`
- Branch: `agent/gpt-solvers-usage`
- Progress lease: 15 minutes without concrete evidence
- Created UTC: `2026-07-27T05:34:01Z`
- Last updated UTC: `2026-07-27T06:00:00Z`

## Outcome

Build and preserve 25x25 Brackets `.man` candidates by selecting finite room
and endpoint variants, validate them at least as strongly as the 26-square
lineage, and hand the best result to Codex without performing platform
submission.

## Released write set

The task's implementation write set is released after commit
`93f80d3b1703f22c88b105374a42ee1ce3c09942`. The immutable artifacts,
builders, tests, evidence, and report remain reviewable but are no longer active
write paths under this task.

## Best deliverable

```text
artifact: submissions/brackets/gpt_brackets_15.man
SHA-256: 826553c4a58fd1ef83f81e8b05e9c3d54b575f2030d89c566cd5d9a99c09e605
box: 25x25, footprint 625
rooms/pipes/men: 5/6/3
pipe lengths: [2, 2, 2, 10, 42, 2]
public: 9/9
public ticks: [246, 58, 106, 70, 146, 380, 136, 136, 2082]
local score: 233333.3333333333
```

Additional local replay passed 9,331 exhaustive strings through length five,
425 directed boundary cases, and 10,000 seeded random length-0..64 cases with
zero failures. No platform action occurred.

## Acceptance replay

```bash
PYTHONPATH=src uv run pytest -q -n 0 tests/test_gpt_brackets_25.py
PYTHONPATH=src uv run python scripts/preflight.py \
  submissions/brackets/gpt_brackets_15.man brackets
```

## Contest authority

GPT did not submit. Codex or the current submission controller owns branch
integration, exact live-state freshness, independent replay, and any platform
decision.

## Handoff

Implementation commit `93f80d3b1703f22c88b105374a42ee1ce3c09942` is pushed.
The immutable handoff message contains the exact review and freshness gates.
