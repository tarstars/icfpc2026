# Matrix Multiply: Parallel Baseline and Compact Rings

Date: 2026-07-24

Problem: `58f54636-3ec4-497d-8102-b486f13a1ed1` (`matmul`), scored by
`max(width,height)^2 × average ticks`, with the default 5,000,000-tick cap.

Selected target: first earn Matrix eligibility with a correct live submission,
then reduce the passing baseline by at least 10%. The final local improvement
is 98.34% (60.25×), well above that target.

## Public contract

Input is `N M K`, followed by row-major A (`N×M`) and row-major B (`M×K`).
All dimensions are between 2 and 16. Output is row-major C (`N×K`).

## `matmul_00`: parallel correctness baseline

The parser stores A in a ring and broadcasts B as `(column, value)` pairs to
16 column workers. For each A row it broadcasts the M values; every active
worker computes one dot product. A token through workers 1–16 serializes
active results in row-major order.

This architecture made correctness and ordering easy to inspect, but produced
a 1,982×291 field. Its measured local properties are:

- footprint: 3,928,324
- ticks: `[43976, 54494, 138024, 1660920, 482316, 208409, 327120]`
- average ticks: 416,465.5714285714
- local score: 1,636,011,699,416.5713
- SHA-256:
  `35e825d744e4f4e70fc234e231ae090db5081fb4f75c909b979aaa4336f2391f`

## `matmul_01`: compact nested rings

The compact algorithm uses one controller and canonical FIFO rings:

1. Store A and B row-major.
2. For one A row, initialize K zero partial sums.
3. For each of its M values, cycle K consecutive B values and the K sums,
   updating `sum[j] += a × b`.
4. After M iterations, B has made one complete `M×K` rotation and is back in
   canonical order. Emit the K sums.
5. A advances exactly M values per output row and returns to canonical order
   after N rows.

The A return pipe is an outer U and the B return pipe is nested inside it.
Their measured capacities are 350 and 276 values, respectively, above the
256-value maximum. Six short scalar/sum rings use vertically oriented relays
and disjoint two-column corridors.

Measured local properties:

- dimensions: 109×289
- footprint: 80,656
- ticks: `[23726, 31502, 109586, 4198442, 718378, 189656, 405220]`
- average ticks: 810,930
- local score: 65,406,370,080
- SHA-256:
  `7f17ac2d7ce8977c28854a01de7619eecf7cd7a0a4b78fc45de1818c26778149`

The compact version has 45.77 times less footprint and a 25.01 times smaller
local footprint-tick score. Its full 16×16×16 public case remains below the
tick cap with 801,558 ticks of headroom.

## `matmul_02`: balanced geometry

This is a geometry-only successor to `matmul_01`. A forms an outer 334-cell
rectangular return pipe. B folds inside it with 268 cells, and output is
relayed through a clear side corridor. The controller state machine and
matrix algorithm are unchanged.

Measured local properties:

- occupied dimensions: 183×180
- footprint: 33,489
- ticks: `[23684, 31460, 109544, 4198400, 718336, 189614, 405178]`
- average ticks: 810,888
- local score: 27,155,828,232
- SHA-256:
  `4d4b47c05a39fa1f428d45748e1a0d5b8af4de240eec6aad2d76adb9b8570e5b`

The geometry is 2.41 times better by local score than `matmul_01` and 60.25
times better than `matmul_00`.

## Hypotheses and experiments

- Architecture: replace spatial column replication with canonical A/B rings
  and a K-element partial-sum ring. This traded ticks for a much smaller
  squared footprint and was retained.
- Component: rotate the relay so every compact ring uses top input and bottom
  output. This reduced controller port spacing and transition distance.
- Geometry: first use nested vertical U pipes, then balance the bounding square
  by making A an outer rectangle and folding B inside it.

| Experiment | Result | Decision |
| --- | ---: | --- |
| 16 parallel workers (`matmul_00`) | 1,982×291; score 1.636T | Correct baseline; too wide |
| First single-ring layout, top input | first case hit tick cap after wrong input resolution | Rejected; input moved below |
| Wide-zone single-ring layout | 6/7; full case hit tick cap | Rejected; compact ports/relays |
| Compact vertical-U rings (`matmul_01`) | 109×289; score 65.406B | Retained algorithm baseline |
| Balanced nested geometry (`matmul_02`) | 183×180; score 27.156B | Final candidate |

The placement search was deterministic and bounded; no randomized geometry
search was used (`seed: none`). The retained parameters are encoded in
`build_matmul_ring_compact()`.

## Validation

In addition to all seven public cases, deterministic generated cases use seed
`20260724` and cover M=16, K=16, N=16, alternating ±99 values, mixed signs,
and five different matrix shapes. A Python reference multiplication oracle
produces every expected result. Static tests require both matrix return pipes
to exceed the 256-value maximum.

## Reproducibility

The immutable programs and machine-readable properties are in
`submissions/matmul/`. `tests/test_matmul.py` checks parsing, matrix-pipe
capacity, footprint, all seven public cases for all three generators, and the
generated adversarial cases.

The final repository gate was `uv run pytest -q`: 92 tests passed in
657.25 seconds.

Exact benchmark command:

```bash
uv run python scripts/benchmark_candidates.py matmul \
  submissions/matmul/matmul_02.man \
  --parent submissions/matmul/matmul_01.man
```

## Live result

The exact `matmul_02` file was submitted with:

```bash
uv run icfpc-api submit \
  58f54636-3ec4-497d-8102-b486f13a1ed1 \
  submissions/matmul/matmul_02.man --confirm --wait
```

Submission `c2e95f37-585d-41b2-8f71-a255345fa784` passed 20/20 at
183×180, average 993,968 ticks, and score 33,286,994,352. The unfrozen
standings snapshot at `2026-07-24T20:32:11.660Z` placed `wheezards` ninth of
19 rows with 1.5555555556 points.

Known risk: the full-size public case uses 4,198,400 of the 5,000,000 ticks,
so private workloads with the same maximum dimensions but materially slower
data-dependent behavior would have limited headroom. The algorithm's control
flow is dimension-dependent rather than value-dependent, and all 20 live
cases passed.
