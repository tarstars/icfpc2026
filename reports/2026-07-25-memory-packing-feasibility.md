# Memory: Three-Values-Per-Word Packing Feasibility

Date: 2026-07-25
Action: priority 4 in `docs/tcp-derived-optimization-actions.md`
("Test three-value packing for Memory"). This report + the reference
model and tests are the acceptance evidence; no machine was built and
nothing was submitted.

Problem: `d0b34a23-67c1-4087-b88e-90a74404d50e` (`memory`), scored by
`max(width,height)^2 x average ticks`.

Artifacts (new files only):
- `src/littleman/memory_packing_model.py` — standalone arithmetic model.
- `tests/test_memory_packing_model.py` — 26 focused correctness tests.
- this report.

Run: `uv run pytest tests/test_memory_packing_model.py -q` (26 passed).

## Value domain (from data/small/problems/memory.json)

- 100 cells, `addr` in `[0, 100)`; every cell starts at value 0.
- cell value `v` in `[-1_000_000, 1_000_000]` (2_000_001 distinct values).

## Encoding

Offset each signed value into a non-negative field, then pack three
fields little-endian in base `BASE = 2**21`:

```
e    = v + 1_000_000            e in [0, 2_000_000]
word = e0 + e1*BASE + e2*BASE^2 BASE = 2_097_152
```

`BASE = 2**21 = 2_097_152 > 2_000_000`, so the three fields never collide,
and (being a power of two) a field is peeled with a single littleman
`/ BASE`: quotient (A) = the remaining fields, remainder (B) = this field.
Two `/` steps recover all three fields; a field write is unpack, replace,
repack.

Alternative exact radix `BASE = 2_000_001` also fits signed-64
(`2_000_001^3 - 1 = 8.0e18 < 2^63`) and is documented in the model, but
`2**21` is preferred for divide/shift friendliness.

## Correctness (proven by tests)

- **Encode/decode, full domain**: exhaustive round-trip for every value
  in `[-1_000_000, 1_000_000]` (`test_encode_decode_full_domain_roundtrip`).
- **Pack/unpack**: all 7^3 boundary field combinations plus 20_000 seeded
  random triples round-trip exactly; `peel` reproduces the `/ BASE`
  quotient+remainder split.
- **Ordering**: `encode_value` is strictly monotonic; fields are
  independent — rewriting one field leaves the others' decoded values
  unchanged (`test_field_independence`, `test_write_field_roundtrip_all_positions`).
- **Signed-64 safety**: the maximum representable word is
  `WORD_MAX = 2_000_000 * (1 + BASE + BASE^2) = 8_796_097_216_514_000_000`,
  which is `< 2^63 - 1 = 9_223_372_036_854_775_807` (headroom
  `4.27e17`). The sign bit is always 0 and no word wraps under
  `littleman.sim.wrap64` (`test_word_max_fits_signed64_with_sign_bit_clear`,
  `test_no_word_wraps_under_littleman_arithmetic`).
- **Padding**: 100 cells occupy 34 words = 102 slots, so word 33 has two
  unused padding fields. In-range addresses never map into them
  (`addr 99 -> word 33, field 0`), and corrupting the padding leaves every
  real cell's value intact (`test_padding_slots_do_not_affect_in_range_cells`).
  A fresh `PackedMemory` (all `ZERO_WORD`) reads 0 for all 100 cells.
- **Functional equivalence**: `PackedMemory` reproduces a plain unpacked
  memory exactly on all 7 public cases and 200 seeded random streams.

## Ring-capacity reduction (definite)

| quantity | unpacked | packed | ratio |
|---|---:|---:|---:|
| circulating items | 100 values | 34 words | 2.94x |
| serpentine cells (measured `build_memory` = 107) | 107 | ~41 est. | ~2.6x |

The circulating item count is the dominant per-operation traversal cost,
so this 2.94x reduction is the source of the projected tick win.

## Conservative score projection

Baseline is the accepted `memory_01`: footprint 2209 (46x47), server
average 41,363.625 ticks, server score 91,372,247.625 (from
`reports/2026-07-24-memory-compaction.md`).

Model (`project_score`): only the ring-rotation component of ticks scales,
by `items_packed/items_unpacked = 0.34`; the non-rotation remainder is
kept; decode/encode overhead is charged for 300 assumed operations per
case; footprint is held unchanged (the 38-wide parser P2 binds width today,
and extract/insert logic grows the P3W/P3R stations, so the shorter ring is
not assumed to reduce the binding dimension).

| scenario | rotation frac | overhead/op | footprint | avg ticks | score | vs memory_01 |
|---|---:|---:|---:|---:|---:|---:|
| conservative (default) | 0.70 | 40 | 2209 | 34,254 | 75,666,269 | 0.83x (-17%) |
| optimistic | 0.85 | 25 | 2116 | 25,659 | 54,293,664 | 0.59x (-41%) |

The conservative case remains material but no longer predicts a halving: the
added unpack/repack work consumes much of the rotation saving. The optimistic
case (rotation-dominated, smaller overhead, mild footprint shrink) remains a
roughly 41% projected reduction.

## Recommendation: PROCEED to a prototype, with two guardrails

Both acceptance conditions in the ledger are met: ring capacity improves
materially (2.94x fewer circulating items, proven) and the corrected
conservative score projection improves materially (~17%, estimated). Build a
`memory_02` prototype, but a candidate is only worth keeping if the
built-and-judged machine confirms:

1. **Footprint does not regress.** Extract/insert (`/ BASE` peel, offset
   subtract, repack) enlarges P3W/P3R. If either station's width exceeds
   P2 (38 interior), the binding dimension grows and the tick win can be
   erased by the squared footprint term. Keep the stations <= P2 width.
2. **Per-op decode overhead stays below the rotation savings.** The win
   is rotation ticks falling ~2.94x; if the added peel/repack work per op
   is large relative to the removed rotation, net ticks can rise. Measure
   average ticks on the public cases with the real simulator before
   trusting the projection.

The projection here is an estimate; it is not a substitute for judging a
built machine with `littleman.server_compat`.
