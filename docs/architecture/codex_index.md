# Codex architecture notes

The early files preserve Codex's provisional position. After peer review and
the user's 2026-07-25 validation, `codex_03_rust_toolchain.md` and
`codex_06_yt_search.md` record the reconciled contest-window decisions:
composer-first, no Rust parser, Rust only on measured need, local
multiprocessing first, and YT for useful CPU work exceeding roughly five
local minutes.

## Reading order

1. `introduction.md` — the user's brief, preserved verbatim.
2. `codex_00_foundation.md` — thesis, evidence, and proposed stack.
3. `codex_01_component_contract.md` — the central component data model.
4. `codex_02_lmspec_language.md` — proposed description language.
5. `codex_03_rust_toolchain.md` — reconciled IR-first/Rust-conditional
   decision and response to Claude's five deltas.
6. `codex_04_component_factory.md` — generation and local optimization.
7. `codex_05_program_synthesis.md` — large netlists, placement, and routing.
8. `codex_06_yt_search.md` — reconciled local-first/YT-overflow compute
   policy; GPU deferred.
9. `codex_07_roadmap_and_questions.md` — vertical slices, gates, and debate
   agenda.

## Existing notes that remain relevant

- `docs/littleman-cookbook.md`
- `docs/toolchain-plan.md`
- `docs/synthesis-stack.md`
- `docs/PERFORMANCE_OPTIMIZATION_AGENT_GOAL.md`

The new notes do not replace those documents. They attempt to turn their
verified techniques and broad synthesis direction into one versioned contract
that can connect Rust tools, component search, place-and-route, and YT.
