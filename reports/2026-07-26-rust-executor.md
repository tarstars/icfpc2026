# Exact Rust executor acceptance

Date: 2026-07-26

## Outcome

The Rust executor meets the goal's performance gate while retaining the
Python parser as the source-language authority. The frozen 46-module LLM
workload fell from 621.31 seconds to 17.53 seconds (**35.44x faster**).
The later 69-module, 2,012-test workload fell from 858.86 seconds to
53.08 seconds (**16.18x faster**), below the required 60-second wall time.

The implementation has three layers:

1. `littleman.fastsim` lowers the parsed Python machine into a dense,
   versioned IR.
2. `littleman.rustexec` passes that IR through PyO3 and provides cached,
   deterministic process batches plus a pytest plugin.
3. `littleman-rust` consumes either JSON IR or a zstd-compressed IR cache and
   executes independent jobs with a Rayon thread pool, without Python.

The source parser was deliberately not duplicated in Rust. This keeps loading
and backtick-pairing behavior tied to the established Python oracle.

## Acceptance metrics

Measurements were made at `33ce47bb2aa43336c83978716c0f92997cabac4f`
on an Intel Core i7-13700H with 20 logical CPUs, Python 3.11.15, and
Rust/Cargo 1.75.0.

| Workload | Python baseline | Rust result | Result |
| --- | ---: | ---: | ---: |
| Frozen goal suite: 46 modules, 1,623 current assertions | 621.31 s | 17.53 s | 35.44x |
| Expanded final LLM suite: 69 modules, 2,012 assertions | 858.86 s | 53.08 s | 16.18x |
| Full 14-public-case LLM batch, 173,569,526 judged ticks | — | 18.56 s at 1 worker; 4.93 s at 8 | 3.76x multicore |

The 14-case batch returned the same ordered results at one and eight workers,
and all cases passed. Compiling the 9,137,982-byte LLM artifact took 2.04
seconds. Its reusable compressed IR is 33,149,652 bytes and took 0.63 seconds
to encode.

Raw, machine-readable measurements are in:

- `reports/2026-07-26-rust-executor-metrics.json`
- `reports/2026-07-26-rust-executor-current-metrics.json`

## Exactness evidence

- `uv run pytest -q -n 8 tests/test_rust_executor.py --durations=10`:
  **86 passed, 1 skipped in 61.01 s**. Every loadable preserved submission was
  compared against `sim.py` over every public-case prefix, including complete
  representative Max Element, Reverse, and LLM runs. The comparison includes
  status, error, ticks, output and timing, frames and timing, men and
  registers, pipe queues, blocking, and display state. The skip is an
  intentionally preserved unloadable historical experiment.
- With `_fastsim_rust` injected as the `fastsim` native loop,
  `tests/test_fast_sim_equivalence.py -k 'random_inputs or mutated_programs'`
  produced **10 passed, 89 deselected in 41.18 s**.
- Directed official-semantics tests cover Split birth geometry, register
  inheritance, creation order, wall-birth errors, the 65,536-man cap,
  same-cell arrivals, swap-through, walking onto a halted man, a split born
  onto a halted man, and conflicting births.
- `tests/test_rust_cli.py` compares one- and two-thread standalone CLI
  execution with PyO3, exercises compressed IR loading, and checks a complete
  frame-bearing LLM public case.
- IR version mismatches fail closed rather than being interpreted under an
  unknown layout.

No parity mismatch was observed in the accepted corpus, randomized cases,
mutated programs, official Split cases, or CLI comparison.

## Integrated repository validation

The clean integration branch then merged current `origin/main`, the complete
LLM/Rust lineage, and Claude's score and compact-LLM lineage at `b9df2ad`.
The repository-wide command

```text
uv run pytest -q -p littleman.rustexec -n 8 --durations=25
```

finished with **3,804 passed, 2 skipped, 4 expected xfails, and 0 failures in
457.51 seconds**. This run includes all preserved submission artifacts, the
decompiler round trip, both executor differential suites, LLLM, complete LLM,
compact-LLM work packages, server compatibility, and the score builders.

The first pre-reconciliation run found one real plugin-scoping defect:
redirecting the server wall-tolerant oracle to Rust bypassed its deliberate
`Machine._tick` patch. The plugin now imports and protects that specialized
oracle before replacing ordinary test bindings, and a directed Triangle
regression pins the contest-confirmed 13-tick final-wall-drain behavior. Three
other failures were a missing `llm_03.man` fixture and disappeared when the
Claude artifact lineage was merged.

Focused merge gates additionally produced:

- 366 LLLM tests passed;
- 317 compact-LLM tests passed with one expected xfail;
- 106 score-builder tests passed;
- 71 server/Rust directed tests passed;
- three LLM fuzz-oracle comparisons passed.

## Reproduction

Build the Python extension and the standalone CLI:

```text
uv run maturin develop --release --manifest-path rust/Cargo.toml
cargo build --release --manifest-path rust/Cargo.toml \
  --no-default-features --features cli --bin littleman-rust
```

Run the accelerated pytest workload:

```text
uv run pytest -q -p littleman.rustexec -n 8 tests/test_llm*.py
```

Regenerate the frozen and expanded reports:

```text
uv run python scripts/benchmark_rust_executor.py \
  --suite frozen --llm-batch --workers 8 \
  --output reports/2026-07-26-rust-executor-metrics.json
uv run python scripts/benchmark_rust_executor.py \
  --suite current --workers 8 \
  --output reports/2026-07-26-rust-executor-current-metrics.json
```

Python callers should parse once with `rustexec.CompiledMachine`, reuse its
IR across cases, and call `run_rounds_parallel`. The standalone CLI reads a
request JSON from a file or standard input and accepts `--ir CACHE` for the
compressed IR produced by `CompiledMachine.encoded_ir()`.

## Scope and limitations

- Semantic version 1 preserves the pre-Split Python simulator, including its
  historical stop-on-collision behavior, so the established corpus stays a
  valid regression oracle.
- Semantic version 2 implements the published Split and annihilation rules.
- PyO3 runs retain Python callbacks for round judging. Those callbacks require
  the GIL, so Python multicore batches use `fork`; the standalone CLI uses
  native Rust threads and has no Python/GIL dependency.
- Parallelism is only across independent jobs. Tick execution remains
  sequential and deterministic.
- The standalone binary consumes prepared IR, not `.man` source. Source
  parsing remains intentionally centralized in Python.
