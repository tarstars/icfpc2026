# 20260727-gpt-brackets-24-square: component-folded Brackets lineage

- Status: complete; best candidate handed to Claude
- Record owner: gpt
- Work owner: gpt
- Reviewer/integrator/submission controller: claude
- Problem: `brackets`
- Base main commit: `e6ec08d3b5a72cfcf6ee2ae5c8a4de2ec3c075a8`
- Branch: `agent/gpt-brackets24-v2`
- Created UTC: `2026-07-27T06:15:00Z`
- Last updated UTC: `2026-07-27T07:00:00Z`

## Outcome

Build and preserve server-compatible 24x24 Brackets machines that improve the
accepted `brackets_11` under
`max(width,height)^2 * average_ticks`.

## Exclusive write set

- `src/littleman/gpt_brackets_24.py`
- `tests/test_gpt_brackets_24.py`
- `submissions/brackets/gpt_brackets_16.man`
- `submissions/brackets/gpt_brackets_17.man`
- `experiments/gpt-solvers-usage/gpt_brackets_16-evidence.json`
- `experiments/gpt-solvers-usage/gpt_brackets_17-evidence.json`
- `reports/2026-07-27-gpt-brackets-24-square.md`
- this task, GPT status, and GPT messages

## Best result

- artifact: `submissions/brackets/gpt_brackets_17.man`
- SHA-256: `51a6219ee527d5607720a99a1401cba9d94de9579021d32f1a1ed79adbc72325`
- dimensions: 24x24, footprint 576
- pipe lengths: `[2,2,2,5,39,3]`
- public: 9/9
- public ticks: `[242,64,100,64,144,376,132,132,2078]`
- local score: `213248.0`
- reduction from `brackets_11` local score `276615.0`: `22.908013%`

## Architecture

1. CLOSE folds two result tails into one final `s`, using the server-confirmed
   final-wall-after-send behavior; outer width 23 -> 22.
2. OPEN removes the dedicated terminal row and reuses the ordinary pair sender;
   outer height 9 -> 8.
3. Candidate 17 shifts OPEN left and chooses solver-enumerated port positions.
   OPEN->CLOSE becomes five cells, OPEN->CLASSIFY 39, and INPUT->OPEN three.
   Only transport pipes are shortened.

## Acceptance evidence

- deterministic generators reproduce both immutable artifacts;
- parser: 5 rooms, 6 pipes, 3 men;
- server layout, shared-wall, input-adjacency, and minimum-pipe gates pass;
- public 9/9 under `littleman.server_compat`;
- 9,331 exhaustive strings through length 5;
- 266 directed cases;
- 10,000 random strings through length 64;
- zero behavioral failures;
- all surviving I/O cells resolve to intended logical pipe roles; minimum
  multi-candidate binding margin is one cell.

## Contest authority

GPT has no contest API access and made no platform mutation. Claude owns
freshness, independent preflight, integration, and submission.
