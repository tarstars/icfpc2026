# Sudoku Auditor: Two-Row Worker Packing

Date: 2026-07-25

Problem: `f66c928f-3369-4870-9153-8b20cafc2ecd`
(`sudoku-validity`), scored by
`max(width,height)^2 × average ticks`.

## Result

`sudoku_01` keeps every state machine and ring protocol from accepted
`sudoku_00`, but folds the three worker modules into two rows. It occupies
286×285 instead of 446×200 and improves measured local score by 59.15%.
It is validated and submission-ready but has not been submitted.

## Geometry

The row and column modules share the upper row; the taller box module is
centered below. The parser and broadcaster remain above both rows.

Three routing details make the fold valid:

- the two upper workers retain independent bottom-entry command routes;
- the box command uses a dedicated pipe down the far left;
- the row result crosses the empty inter-row band, passes to the right of the
  box module, and enters the aggregator from above.

The box result also enters from above and the column result enters from the
right. The aggregator's any-pipe receive makes those ports order-independent.
Every worker still owns four private 41-cell rings.

## Exact artifact and measurements

- path: `submissions/sudoku-validity/sudoku_01.man`
- generator: `src/littleman/sudoku.py:build_sudoku_two_row`
- parent: `sudoku_00`
- SHA-256:
  `c14eff02498f37c56c56bc78ff7a9f7b6cb98613bc8b744d3546accf9498244a`
- bytes: 70,926
- dimensions: 286×285
- footprint: 81,796
- public ticks:
  `[880073, 38211, 826099, 48987, 437567, 880077]`
- average public ticks: 518,502.3333333333
- local score: 42,411,416,857.33333

Against `sudoku_00`, max dimension falls 35.87%, footprint falls 58.88%,
average ticks fall 0.66%, and local score falls 59.15%.

## Validation

`uv run pytest tests/test_sudoku.py -q` passed all six focused tests in
19.00 seconds. They establish:

- byte-exact reproduction of both immutable artifacts;
- 20 rooms, 33 pipes, 18 men, and twelve 41-cell ring pipes;
- the `littleman.server_compat` layout gate;
- all six public cases;
- eight seeded valid shuffled prefixes and forced duplicates;
- directed row, column, and box duplicates.

The exact-file benchmark command was:

```bash
uv run python scripts/benchmark_candidates.py sudoku-validity \
  submissions/sudoku-validity/sudoku_01.man \
  --parent submissions/sudoku-validity/sudoku_00.man
```

Immediately before preparing the solution commit, the read-only API check at
`2026-07-25T08:26:57.258Z` showed the live counted result was still
submission `09a4a36c-3ff5-4560-a57a-f14879767fe4`: 20/20, 446×200,
average 529,549.7 ticks, score 105,335,908,125.2, rank 46 of 50.

## Packing experiments

The first routed fold was 292×309 and already passed the focused suite. A
vertical-clearance pass produced working 292×287 and 292×285 versions.
Reducing the upper inter-module gap from eight to four cells and side margin
from eight to six cells produced the retained 286×285 layout.

A three-cell upper gap was rejected without retention: its command corridor
would sit adjacent to a worker wall, making pipe parsing and nearest-port
resolution unsafe. The retained four-cell gap leaves one blank separating
column and preserves the original room programs byte-for-byte.

No contest submission was created.
