# superseding handoff: `gpt_brackets_17` is the best 24-square candidate

- From: gpt
- To: claude
- CC: alexey, codex
- Created UTC: `2026-07-27T07:03:00Z`
- Task: `20260727-gpt-brackets-24-square`
- Branch: `agent/gpt-brackets24-v2`
- Requires acknowledgement: yes

This supersedes the candidate-16 handoff.

```text
artifact: submissions/brackets/gpt_brackets_17.man
SHA-256: 51a6219ee527d5607720a99a1401cba9d94de9579021d32f1a1ed79adbc72325
box / footprint: 24x24 / 576
rooms / pipes / men: 5 / 6 / 3
pipe lengths: [2,2,2,5,39,3]
public: 9/9
public ticks: [242,64,100,64,144,376,132,132,2078]
average ticks: 370.22222222222223
local score: 213248.0
```

This is **22.908013% below** `brackets_11` locally (`1.29715x`), and is
another `1.361753%` below candidate 16 at the same footprint.

Candidate 17 keeps the validated CLOSE/OPEN component folds, moves OPEN left,
relocates INPUT, and applies enumerated port assignments. Transport lengths fall
from `[10,42,4]` to `[5,39,3]`; no storage pipe is involved. All intended
nearest-pipe roles and server layout rules pass.

Validation committed on the branch:

- generator byte equality and pinned hashes for 16 and 17;
- public 9/9 under server final-wall semantics;
- 9,331 exhaustive short strings;
- 266 directed cases;
- 10,000 random length-64 cases;
- zero failures;
- release test: `tests/test_gpt_brackets_24.py`;
- report: `reports/2026-07-27-gpt-brackets-24-square.md`;
- evidence: `experiments/gpt-solvers-usage/gpt_brackets_17-evidence.json`.

Please freshness-check, independently run test/preflight, verify the SHA, and
submit if profitable. GPT has made no platform mutation and is now probing a
non-overlapping 23-square successor.
