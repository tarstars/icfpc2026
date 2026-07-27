# Verified three-column packed Matrix Multiply kernel

Date: 2026-07-26

Task: `20260726-gpt-matmul-packed-kernel`

Branch: `agent/gpt`

This report contributes a verified arithmetic kernel and a bounded implementation
plan. It does **not** claim a complete Littleman machine, a measured `.man`
score, or a live contest result.

## Result

Three adjacent output columns can be accumulated with one signed-64 multiply
and add per inner-dimension element by packing them into independent 20-bit
lanes.

For legal matrix values `-99..99`, define:

```text
SHIFT = 100
L = 2^20
x_t = a[i,t] + SHIFT
P_t = (b[t,j]   + SHIFT)
    + (b[t,j+1] + SHIFT) * L
    + (b[t,j+2] + SHIFT) * L^2
R = sum_t x_t * P_t
```

The lane bound is:

```text
M <= 16
0 <= x_t, b_shifted <= 199
16 * 199^2 = 633,616 < 2^20 = 1,048,576
```

Therefore no lane can carry into its neighbour. The whole packed accumulator is
also strictly below `2^63`, so it remains a nonnegative signed-64 value.

For lane `l`:

```text
raw_l = (R >> (20*l)) & (2^20 - 1)
```

Let:

```text
A_shift_sum = sum_t (a[i,t] + 100)
B_shift_sum[j] = sum_t (b[t,j] + 100)
```

Then the exact unshifted result is:

```text
C[i,j] = raw_l
       - 100 * A_shift_sum
       - 100 * B_shift_sum[j]
       + 10,000 * M
```

This identity handles negative inputs without signed sub-lanes and supports a
partial final group of one or two columns.

## Executable evidence

Reference implementation:

```text
experiments/gpt-matmul-packed/packed_matmul_reference.py
```

Validation command:

```bash
python3 experiments/gpt-matmul-packed/packed_matmul_reference.py
```

Observed output before publication:

```text
packed three-lane MatMul reference: all tests passed
```

The self-test covers:

- all four combinations of constant `-99` and `99` at `16x16x16`;
- 5,000 deterministic random legal matrices;
- every matrix dimension independently sampled from `2..16`;
- exact comparison against naive multiplication;
- the lane-carry bound;
- the signed-64 accumulator bound.

## Machine direction

The current accepted architecture spends nearly all of its time walking through
a large multi-zone controller. The packed arithmetic only matters if it is
paired with a streaming topology that removes that controller from the hot
path.

### Phase 1: one-lane component

Build an isolated component pair:

```text
MUL3: receive shifted A factor and packed B token, emit packed product
ACC3: retain packed accumulator, add products, emit/reset on ordered tag
```

Required measurements:

- steady-state initiation interval at most 20 ticks;
- stretch target at most 12 ticks;
- canonical B-ring order restored after each row;
- exact extremes at `M=16` and values `-99`, `99`;
- negative control tags cannot overtake factor/product tokens;
- all pipe capacities asserted from worst-case occupancy, not guessed from
  geometric length.

Do not build a full six-lane machine before this component is measured.

### Phase 2: compare physical lane counts

Evaluate 1, 2, 3, and 6 lanes. Six lanes minimize the number of serialized
column groups, but may lose on the squared footprint term.

The six-lane form is:

```text
A-factor broadcaster --S--> lane 0 .. lane 5
```

Each lane owns an `M`-token packed-B ring and private packed accumulator.
Commands and data share a FIFO so end-of-row ordering is structural rather than
implemented by a separate acknowledgement network.

For row-major output, pass one drain token through the lanes in order; each lane
extracts and corrects its one to three columns before forwarding the token.
This avoids a six-input timing-sensitive arbiter.

## Score feasibility gate

The recorded `matmul_07` server score is approximately `8.44e9`. A 100x result
must be below approximately `8.44e7`.

Useful design frontiers are:

| Maximum dimension | Maximum average ticks for 100x |
|---:|---:|
| 40 | 52,729 |
| 45 | 41,662 |
| 50 | 33,747 |
| 60 | 23,435 |

Because local-to-server tick ratios are not stable across architectures, a
candidate that only barely crosses the 100x line locally is not sufficient. A
safer local objective is `<= 55,000,000`, for example:

```text
50x50 at <= 22,000 average ticks
45x45 at <= 27,000 average ticks
40x40 at <= 30,000 average ticks
```

An architecture that cannot plausibly satisfy one of these frontiers should be
rejected before room routing work begins.

## Risks that remain unmeasured

- Littleman extraction and correction sequences may dominate a tiny multiplier
  loop if they are placed on the per-product path instead of the per-row drain
  path.
- Logical right shifts require masking because `}` is arithmetic.
- Six-way `S` backpressure is convenient but one slow inactive lane can throttle
  every active lane.
- Packed B column sums must remain aligned with the corresponding lane group.
- The best lane count is a footprint-throughput tradeoff and must be measured.
- No complete `.man` candidate has been generated or judged by this task.

## Handoff recommendation

Assign a separate solution task with fresh paths, live-state reconciliation,
and explicit submission prohibition. Its first accepted milestone should be a
standalone one-lane component benchmark, not a whole-machine drawing.

Suggested unique implementation paths:

```text
src/littleman/gpt_matmul_packed.py
tests/test_gpt_matmul_packed.py
experiments/gpt-matmul-packed/components/
```

Only after the normal solution freshness gate should it create a numbered
artifact under `submissions/matmul/`.
