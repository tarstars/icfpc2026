# handoff: 24-square Brackets candidate beats the next-rank threshold

- From: gpt
- To: claude
- CC: alexey, codex
- Created UTC: `2026-07-27T06:44:00Z`
- Task: `20260727-gpt-brackets-24-square`
- Branch: `agent/gpt-brackets24-v2`
- Base: current integrated `main@e6ec08d3b5a72cfcf6ee2ae5c8a4de2ec3c075a8`
- Requires acknowledgement: yes

The earlier 25-square handoff is superseded by a complete 24-square candidate.

```text
artifact: submissions/brackets/gpt_brackets_16.man
SHA-256: 706ec513016503a48cd793a48d43fee17e0caf71c4d476b875eeaef66fe62845
box: 24x24
footprint: 576
rooms / pipes / men: 5 / 6 / 3
pipe lengths: [2,2,2,10,42,4]
public: 9/9
public ticks: [248,70,106,70,150,380,136,136,2082]
average ticks: 375.3333333333333
local score: 216192.0
```

The checked-in live parent `brackets_11` is 27x27, local score `276615.0`, live
score `484532.65`. The candidate is **21.843718% lower locally** (`1.27949x`),
comfortably beyond your measured `1.131x` next-rank requirement.

## What changed

- CLOSE outer width 23 -> 22 by merging two terminal result paths into one final
  send; this intentionally relies on the server-confirmed final-wall-after-send
  behavior.
- OPEN outer height 9 -> 8 by routing end-of-stream through two spare columns,
  reusing the ordinary pair sender for `(0,4)`, and halting through the BP branch.
- OPEN -> CLASSIFY remains exactly 42 pipe cells; OPEN -> CLOSE remains at its
  ten-cell Manhattan minimum. No storage/timing route was shortened.

## Evidence

- exact generator and pinned artifact are committed;
- `tests/test_gpt_brackets_24.py`: 3 tests, including 9,331 exhaustive strings
  and 1,000 exact random strings, passed locally;
- additional 266 directed and 10,000 fast wall-semantics random cases passed;
- `server_compat.validate_layout`, minimum pipe, input adjacency and shared-wall
  gates pass;
- full report: `reports/2026-07-27-gpt-brackets-24-square.md`;
- evidence JSON: `experiments/gpt-solvers-usage/gpt_brackets_16-evidence.json`.

GPT has no contest credentials and made no platform mutation. Please run current
freshness, independent test/preflight, and hash checks, then submit if the live
baseline is still `brackets_11` or otherwise worse than this projected result.
I am continuing only on non-overlapping successor paths.
