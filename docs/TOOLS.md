# Tool registry

This is the integrator-owned registry of shared project tools. Status reflects
evidence and scope, not implementation effort. A tool is mandatory only on
the workflows named in its `Mandatory on` field and only after the listed
path is present on `main`.

Agents propose registry changes through immutable coordination messages;
Codex integrates them with evidence. A contradiction from the contest server
demotes a tool immediately.

## Status ladder

| Status | Meaning | Promotion requirement |
| --- | --- | --- |
| `draft` | Exists, but consumers must audit it themselves. | None. |
| `verified` | May be relied on for the stated scope. | Pinned tests plus at least one recorded real use. |
| `gold` | Mandatory on the declared workflow. | Verified; compared with a ground-truth corpus, oracle, or server evidence; stable invocation/import API; owner and displaced path recorded. |
| `errata` | Useful, but a known-wrong part is listed. | Fix and pin every listed error before promotion. |
| `retired` | Do not use. | Replacement is named. |

Gold is scoped, not universal. For example, `sim.py` is authoritative for
local execution, while release validation must additionally use
server-compatibility checks because server/parser divergences are known.

## Active tools on `main`

| Tool | Path | Owner | Status | Mandatory on | Evidence and limits | Displaces |
| --- | --- | --- | --- | --- | --- | --- |
| Littleman parser/simulator | `src/littleman/sim.py` | integrator | **gold** | executing or diagnosing a `.man` artifact | Broad repository corpus; signed-64 and engine tests; live `brackets_00` corroborates B survival. Known server load differences remain outside this scope. | ad-hoc `.man` interpreters |
| Round-controller judge | `src/littleman/judge.py` | integrator | **gold** | output/frame timing and public-case scoring | `tests/test_judge.py`; round completion and wrong-output behavior pinned. Use server-compatible wrapper for release. | timing inferred from bare `Machine.run()` |
| Server-compatible judge/layout gate | `src/littleman/server_compat.py` | integrator | **gold** | every release candidate | `tests/test_server_compat.py`; preserved shared-wall and final-wall server divergences; 18 focused API/judge/compat tests passed 2026-07-25. | trusting the plain parser/judge for submission |
| Two-cell pipe gate | `src/littleman/alexey_pipecheck.py` | integrator | **gold** | every release candidate | Server rejection identified from `sort_05` and `reverse_02`; exercised by candidate benchmark tests. | eyeballing pipe lengths |
| Contest API client/CLI | `src/icfpc_api/` | integrator | **gold** | every API read and contest mutation | `tests/test_api_client.py`; authenticated responses and submission artifacts are preserved by the established workflow. | curl, bespoke HTTP, unrecorded UI submission |
| Canvas assembler | `src/littleman/canvas.py` | integrator | `verified` | — | Used by checked-in generators and their byte-exact artifact tests; pipe-resolution and server gates remain downstream. | duplicated grid-padding/overlay code |
| Squeeze/trim helpers | `src/littleman/alexey_squeeze.py`, `src/littleman/alexey_trimrooms.py` | integrator | `draft` | — | Real sweeps exist, but no general equivalence or release gate has been demonstrated. | — |
| Littleman cookbook | `docs/littleman-cookbook.md` | integrator | `verified` | design review | B write-set corrected with engine/spec/live-artifact evidence; two-cell rule added 2026-07-25. Prose remains subordinate to executable gates. | rediscovering established idioms |

Stable invocations:

```text
uv run python -m littleman <program.man> <problem-slug>
uv run pytest tests/test_judge.py tests/test_server_compat.py
uv run icfpc-api --help
uv run icfpc-api submit <problem-id> <program.man> --confirm --wait
```

The first command is useful for development but is not the complete release
gate: pair it with `server_compat.validate_layout` and
`alexey_pipecheck.check` until the composite preflight below reaches `main`.

## Reviewed candidates not yet on `main`

These paths exist at `origin/agent/claude` and are not active shared tools
until integrated.

| Tool | Branch path | Owner | Status | Intended mandatory on | Evidence / blocking erratum |
| --- | --- | --- | --- | --- | --- |
| Composite preflight | `scripts/preflight.py` | Claude until handoff, then integrator | `verified` | every submission after integration | Chains parse, shared-wall, two-cell, server-compatible judge, metrics, and hashes. Semester 4 rounds/frames and stray-output rejection were independently reviewed. It lacks a direct CLI regression test and is absent from `main`. |
| Machine IR exporter | `src/littleman/ir_export.py` | Claude | **errata** | geometry/binding queries after repair | 94 tests and corpus round-trip pass. Confirmed bug: `R`/`U` list order loses destination reading-order priority. Display side and literal semantics are missing for a parser-free executor. |
| Opcode-effects generator/table | `scripts/gen_effects.py`, `docs/architecture/claude_effects.json` | Claude | **errata** | register-model questions after repair | Regeneration hash matches and B conclusion is server-corroborated. Direct pipe-array initialization leaves sparse counts wrong, so nonzero `q` behavior is not tested. |
| LLM/LLLM reference oracle | `src/littleman/llm.py` | Claude | `verified` | interpreter-machine differential judging after integration | 35 focused tests passed; public frames, wrap64, collision, and inherited semantics reviewed. Add directed two-cell blocked-send regression. |
| LLLM pipe-free fuzz | `src/littleman/llm_fuzz.py` | Claude | `verified` for pipe-free LLLM; `draft` for LLM | LLLM submission; only the pipe-free subset of LLM | Five generator tests passed. A pipe-bearing directed generator is required before LLM submission. |
| Exact Rust executor | `src/littleman/rustexec.py`, `rust/` | integrator | `verified` pending peer review/integration | accelerated differential tests and independent simulation batches after integration | Versioned dense IR; PyO3 and standalone Rayon CLI; 2,012-test LLM suite passed in 53.08 s versus 858.86 s under Python; whole-state corpus, mutation, Split, cache, and 1/N-worker parity tests pass. Python remains the parser. |

Review evidence is preserved in:

- `coordination/messages/codex/20260725T141300Z-semester4-llm-oracle-second-review.md`
- `coordination/messages/codex/20260725T141301Z-semester4-llm-fuzz-gap-review.md`
- `coordination/messages/codex/20260725T141302Z-semester4-preflight-frame-review.md`
- `coordination/messages/codex/20260725T141303Z-ir-export-gold-gate-review.md`
- `coordination/messages/codex/20260725T141304Z-opcode-effects-methodology-review.md`

Rust executor build and acceptance invocations:

```text
uv run maturin develop --release --manifest-path rust/Cargo.toml
uv run pytest -q -p littleman.rustexec -n 8 tests/test_llm*.py
cargo build --release --manifest-path rust/Cargo.toml --no-default-features --features cli --bin littleman-rust
uv run python scripts/benchmark_rust_executor.py --suite frozen --llm-batch --workers 8
```

The standalone binary reads batch JSON from a file or standard input.
`--ir PATH` loads the zstd-compressed, versioned cache returned by
`littleman.rustexec.CompiledMachine.encoded_ir()`. See
`reports/2026-07-26-rust-executor.md` for the request API, parity scope, and
reproducible measurements.

## Enforcement

- Submission task acceptance checks must name the composite preflight once it
  is on `main`; until then they must name the server-compatible judge and
  two-cell pipe gate explicitly.
- A new gold tool must include its stable invocation/import API in this file.
- A known contradiction changes status to `errata` in the same integration
  commit and links a failing fixture or immutable evidence message.
- Tool output never overrides server results. Local projections rank
  candidates; only recorded submissions measure live behavior and score.
