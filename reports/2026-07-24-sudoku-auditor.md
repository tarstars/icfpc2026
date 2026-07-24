# Sudoku Auditor: Parallel Mask Rings

Date: 2026-07-24

Problem: `f66c928f-3369-4870-9153-8b20cafc2ecd`
(`sudoku-validity`), scored by
`max(width,height)^2 × average ticks`.

## Target

The team had no Sudoku standings row, so the first objective was a robust
20/20 submission and immediate eligibility rather than score optimization.

## Architecture

One parser broadcasts each `(row, column, value)` triple to three workers:

- the row worker selects mask `row`;
- the column worker selects mask `column`;
- the box worker computes `3*(row//3) + column//3`.

Each worker stores nine digit bit masks in a canonical FIFO ring. It rotates
to the selected mask, computes `1 << (value-1)`, sets the bit, restores ring
order, and emits a duplicate flag. A three-input aggregator sums the flags and
outputs 1 only when their sum is zero. Contest round gating prevents the next
triple from reaching the parser before that verdict.

The first layout fed commands through worker top ports. A target-ring read was
one Manhattan cell closer to that command pipe and deadlocked. The retained
layout routes each command pipe around its worker to a dedicated bottom port,
making every `r` resolution unambiguous.

## Validation and metrics

The exact artifact has:

- SHA-256:
  `150abdba2a07421dc37cf975fc68a2313e7cee727bd582597f9ad15923d2d11a`
- occupied dimensions: 446×200
- footprint: 198,916
- public ticks:
  `[885889, 38489, 831560, 49336, 440472, 885893]`
- average public ticks: 521,939.8333333333
- local score: 103,822,183,887.33333

Deterministic generated tests use seeds `20260724..20260731`. They shuffle
valid prefixes from a solved grid, then force duplicates without repeating a
cell. Directed cases separately force row, column, and box violations. A
Python set-based oracle produces every expected verdict.

## Live result

The exact preserved file was submitted with:

```bash
uv run icfpc-api submit \
  f66c928f-3369-4870-9153-8b20cafc2ecd \
  submissions/sudoku-validity/sudoku_00.man --confirm --wait
```

Submission `09a4a36c-3ff5-4560-a57a-f14879767fe4` passed 20/20 at
446×200, average 529,549.7 ticks, and score 105,335,908,125.2.
The unfrozen standings snapshot at `2026-07-24T21:04:11.324Z` placed
`wheezards` 28th of 32 rows with 1.1290322581 points.

The final repository gate was `uv run pytest -q`: 95 tests passed in
753.80 seconds.

## Next optimization

The 446-cell width comes from three generated worker rooms placed side by
side. Stacking or compacting those workers is the obvious next score lever;
the current candidate is retained as the correctness and protocol baseline.
