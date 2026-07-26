# Fast executor (`littleman.fastsim`)

`sim.py` is the specification and is unchanged. `fastsim.Machine` is a
subclass of `sim.Machine` that inherits parsing verbatim and replaces only
`run()`. `judge.py`, `python -m littleman` and `scripts/preflight.py` now
import `Machine` from `fastsim`, so every existing call site got faster
with no change in behaviour.

Three layers, each falling back to the one below:

1. **C extension** `src/littleman/_ext/fastsim_ext.c`, built to
   `src/littleman/_fastsim_ext.so` by
   `uv run python scripts/build_fastsim_ext.py`.
2. **Pure-Python fast loop** `fastsim.run_program` — the same flattened
   design, no toolchain needed. Used automatically when the extension is
   absent or `LITTLEMAN_FASTSIM_EXT=0`.
3. **`sim.Machine.run`** — used when `compile_machine` raises `Unsupported`,
   or when `LITTLEMAN_FASTSIM=0`.

Nothing is blocked by a missing compiler: with no `.so` present the import
of `_fastsim_ext` fails silently and layer 2 takes over.

## Measured

Ticks/sec, same host, same artifacts (`judge.RoundController`, i.e. the
real judging path).

| workload | `sim.py` | fastsim (C) | speedup |
| --- | ---: | ---: | ---: |
| matmul_03 `16x16x16 full size` (4.20 M ticks) | 0.99 M t/s | 93 M t/s | **94x** |
| matmul_03 `skinny 16x2x16` (0.72 M ticks) | 0.96 M t/s | 72 M t/s | 75x |
| subset_sum_00, all 7 cases run to completion (48.9 M ticks) | 46 k t/s | 1.37 M t/s | **30x** |
| all 78 `submissions/**/*.man`, 1 M-tick budget (55.3 M ticks) | 195 k t/s | 3.15 M t/s | 16x |

Whole-judge wall clock (`python -m littleman <artifact> <problem>`,
including interpreter start-up and `sim`'s own parser):

| judge run | before | after |
| --- | ---: | ---: |
| matmul (7 cases, 5.7 M ticks) | 5.76 s | **0.13 s** (44x) |
| subset-sum (7 cases, ~48 M ticks) | 15 m 25 s | **41 s** (22x) |

The pure-Python layer alone is ~1.8x on matmul; it exists as the
no-toolchain fallback and as the readable reference for the C.

Why subset-sum gains 30x on the loop but only 22x end-to-end: that
artifact is 2 121 rooms / 2 164 pipes / 2 119 men on a 3029x4046 grid.
Per-tick cost there is dominated by the number of *simultaneously running
men*, not by per-op overhead, so both executors are far off their
single-man peak. On top of that `sim.Machine.parse` — which fastsim reuses
unchanged, and which is not part of this work — costs 1.7 s per case, about
12 s of the 41 s judge run.

## What changed

* **Opcode arrays.** The grid is compiled once into four `int` arrays, one
  per heading. That folds `_literal_load`, the `hdigits`/`vdigits` test and
  the ~35-branch character chain in `_execute` into one array read and a
  `switch`. Backtick literals are pre-evaluated per direction.
* **Dense interior-cell ids.** Cells are numbered room-major/row-major over
  room *interiors* only, and `step[d][cell]` gives the destination cell or
  `-1` for `sim`'s "wall" error. Indexing the full `W*H` rectangle instead
  costs ~1.5 GB on subset-sum; this costs ~7x less and removes the wall
  bounds check. Man-on-man collision is still keyed by absolute grid
  position, so it is exact even if two rooms' interiors were to overlap.
* **Pipes without a dense `values` list.** A pipe is a flat run list
  `[s0,e0,s1,e1,...]` plus a ring buffer of the values in index order.
  `shift()` becomes O(#runs) integer increments with no list slicing;
  `put` is always at index 0 and `take` always at the last index (that is
  all `sim` ever does), so both are O(1).
* **Scheduling.** `sim`'s per-tick `heapq` + three fresh `set()`s are
  replaced by a reusable binary heap, a "processed this tick" stamp array
  and a flag+buffer runnable set. The rule that a man unblocked by a
  *lower-indexed* man runs in the same tick is preserved exactly.
* **Waiters.** Per-pipe waiter lists, with the same edge-triggered wake
  points `sim` uses (`shift`, `put` on a full destination, `take` on an
  empty source), and the same re-check of the full wait condition.

One deliberate specialisation: when the controller is exactly
`judge.RoundController` and its `queue` list is empty, `pop_input()` is not
called (it provably returns `None` with no side effect). Any other
controller is called every tick as before.

## What the equivalence proof covers

`tests/test_fast_sim_equivalence.py`. Every check compares the *whole*
observable state after a run and fails naming the artifact, the case and
the first differing field:

`RunResult.status`, `.error`, `.ticks`, `.output`, `.output_ticks`,
`.frames`, `.frame_ticks`; every man's `(r, c, direction, A, B, BP,
halted, blocked)`; every pipe's full `values` list; every display's
`cursor`, `current` and `next`.

Covered:

* **All 78 `.man` artifacts under `submissions/**`** against every public
  case of their problem, through `judge.RoundController` (one artifact,
  `history/history_00.man`, does not load under `sim` at all and is
  skipped). Bounded by `FASTSIM_TEST_BUDGET` ticks per case (default
  30 000; raise it for a deeper run).
* The same set at a 1 M-tick budget was run offline: **55.3 M ticks,
  0 divergences**. subset-sum was separately run to completion on all seven
  cases: **48.9 M ticks, 0 divergences** (sim 1 053 s, fastsim 35.6 s).
  The pure-Python layer was also swept over all artifacts separately:
  10.3 M ticks, 0 divergences.
* Pure-Python layer, separately (`USE_EXTENSION` monkeypatched off).
* LLLM/LLM fuzz corpus (`llm_fuzz.corpus`) — this is what exercises
  displays, `on_frame` verdicts and frame equality; the test asserts that
  frames were actually produced.
* Random input vectors (including ±2^63-1 magnitudes) fed to 14 real
  artifacts with no controller — pipe blocking, `q`/`R`/`U`, signed-64
  wrapping on hostile data, `tick-cap` status.
* Single-character mutations of small artifacts — this is what reaches the
  `wall`, `bad-op` and `no-pipe` error paths and man-on-man collisions.

## What is NOT covered

* **Parsing and load errors** are not part of the proof because they are
  not reimplemented: `fastsim.Machine` inherits `sim.Machine.parse`,
  `_find_rooms`, `_find_pipes` and `_build_literals` unchanged.
* **Machines resumed mid-run.** `compile_machine` raises `Unsupported`
  (-> falls back to `sim`) if any man is already blocked or waiting when
  `run()` is called. Calling `run()` twice on the same machine is exact
  only through that fallback.
* **Post-run internals other than the ones listed above.** `_writeback`
  restores men (including `Man.blocked` and `Man.wait_kind`, which
  `decompile`/`gen_effects`/`lllm_assemble` read to classify deadlocks),
  pipes (`values`, `runs`, `value_count`) and displays. It does *not*
  restore `Man.wait_pipes`, `machine._occupied`, `_active_pipes`,
  `_runnable_men`, `_receive_waiters`, `_send_waiters` or `_tick_heap`.
  Nothing in the repo reads those after a run, but a new caller that did
  would see stale values. Likewise, pre-seeding `machine._runnable_men`
  *before* calling `run()` (as `tests/test_subset_sum.py` does on a plain
  `sim.Machine`) is ignored by the fast path — use `sim.Machine` for that.
* **Multi-display ordering beyond one pipe per side.** If a display had two
  pipes attached to the same side, `sim` keeps the last one in iteration
  order; fastsim reproduces that choice at compile time, but no artifact
  in the repo exercises it, so it is untested.
* **Tick counts above 2^31 and grids above 2^31 cells** — the C layer uses
  `int32_t` for cells and pipe indices (tick counts are `int64_t`). Far
  beyond anything the contest tick caps allow.
* **Load errors raised at run time** cannot occur: fastsim only produces
  the same four run-time errors `sim` does (`wall`, `bad-op`, `no-pipe`,
  `display`).
