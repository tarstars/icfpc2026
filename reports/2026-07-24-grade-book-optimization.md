# Grade Book Geometry and FSM Compaction

## Outcome

`gradebook_01` preserves the four-worker architecture and every finite-state
transition from accepted `gradebook_00`, while parameterizing and tightening
the physical layout. It improves the exact local footprint-tick score by
15.9980% and the live score by 15.9680%.

The exact candidate passed all seven public cases, a deterministic generated
maximum-roster workload, all 137 repository tests, and all 20 live cases.

## Baseline and target

The baseline was reproduced byte-for-byte before optimization:

| Variant | SHA-256 | Width × height | M | Average ticks | Score |
|---|---|---:|---:|---:|---:|
| `gradebook_00` | `16a9fe2c…ada522` | 494×462 | 494 | 151,935.00 | 37,077,609,660.00 |

An equal-tick 5% improvement required `M <= 481`. The selected stretch target
was to make the worker layout no wider than its vertical stack, without
changing worker protocols or ring capacities.

## Hypotheses

- Architecture: a sequential or differently sharded grade store could reduce
  width, but would change throughput and correctness protocols substantially.
  It was deferred after physical compaction cleared the stretch goal.
- Component: the FSM compiler reserved three cells beyond its rightmost
  control track. The track always turns vertically or left, so the compact
  variant safely uses zero extra right padding.
- Geometry: worker gaps need carry only one vertical command pipe, left and
  right margins need only protect those routes, the outer acknowledgement
  needs one column beyond the parser wall, and the parser/worker bands need
  only one separating row.

All parameters live in `GradebookLayout`. `BASELINE_LAYOUT` retains the old
values exactly; `COMPACT_LAYOUT` supplies the selected values.

## Experiments

| Experiment | Result | M | Average ticks | Score | Gain |
|---|---|---:|---:|---:|---:|
| accepted baseline | retained | 494 | 151,935.00 | 37,077,609,660.00 | — |
| gaps 4, margins 5, outer ack 2 | passed 7/7 | 481 | 151,751.14 | 35,109,296,162.57 | 5.31% |
| one-cell command corridors | passed 7/7 | 466 | 151,510.29 | 32,901,367,604.57 | 11.26% |
| command corridors after workers | rejected while parsing | 462 | — | — | — |
| one-cell FSM right padding | passed 7/7 | 462 | 151,385.43 | 32,312,311,416.00 | 12.85% |
| parser/worker vertical gap 2 | passed 7/7 | 458 | 151,171.14 | 31,710,263,610.29 | 14.48% |
| zero FSM right padding | selected; passed 7/7 | 454 | 151,108.71 | 31,145,923,753.71 | 16.00% |

The attempted 462-square route rendered but failed `Machine.parse` with
`bad pipe glyph '|' at (406, 72)`: its below-worker horizontal command leg
crossed a result pipe. It was rejected before simulation and not preserved.

## Final local metrics

`uv run python scripts/benchmark_candidates.py gradebook
submissions/gradebook/gradebook_01.man --parent
submissions/gradebook/gradebook_00.man` measured the exact files:

| Public case | Baseline ticks | Candidate ticks |
|---|---:|---:|
| tiny roster walkthrough | 40,753 | 40,334 |
| TOP demotion | 125,295 | 124,472 |
| tie-break | 131,664 | 130,841 |
| floor rounding | 103,892 | 102,968 |
| mixed batch | 148,646 | 147,839 |
| K=1 minimal | 68,874 | 68,354 |
| N=16 K=4 max | 444,421 | 442,953 |

Final properties:

```text
SHA-256              f159eaf92ea37d9df9e66f814e8248c9ce10bb23eb9dbec591fc58f10f98c91f
bytes                 201291
width × height        454 × 450
M / footprint         454 / 206116
average ticks         151108.7142857143
worst public ticks    442953
local score           31145923753.714287
M improvement         8.0971659919%
footprint improvement 15.5386910128%
tick improvement      0.5438415864%
score improvement     15.9980267355%
```

## Invariants and adversarial validation

- `gradebook_00.man` still reproduces exactly from `build_gradebook()`.
- `gradebook_01.man` reproduces exactly from `build_gradebook_compact()`.
- Both machines parse as 16 rooms and 30 pipes.
- All four compact data-return pipes retain 98 cells, above the conservative
  33-value full-roster requirement.
- Invalid command clearances, margins, ack clearance, right padding, and
  vertical separation are rejected by `GradebookLayout.validate()`.
- A generated seed-`20260724` case uses `N=16`, `K=4`, six eight-operation
  batches, all four operations, grade boundaries 0 and 100, TOP ties, and
  floor averages. It matches a Python oracle in 1,344,885 ticks.
- `uv run pytest tests/test_gradebook.py -q` passed 13 tests.
- `uv run pytest -q` passed all 137 tests in 57.63 seconds.

The main remaining risk was server parsing of the one-cell corridors and
wall-adjacent FSM track. The live grader accepted both. Private workload mix
can change average ticks, but shorter routes improved every public case and
also reduced the live average.

## Live result

The exact candidate was submitted with:

```bash
uv run icfpc-api submit \
  d1415447-bf8d-49ef-924e-e024b06a504d \
  submissions/gradebook/gradebook_01.man --confirm --wait
```

Submission `321cd740-3f00-49f2-9321-36330ab0fe6f` returned `done`, 20/20,
454×450, average 506,043.1 ticks, score 104,303,579,599.6, and no error.
The unfrozen standings snapshot at `2026-07-25T01:14:57.234Z` placed
`wheezards` 21st of 31 rows with 1.3333333333 points.
