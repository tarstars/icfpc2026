# 20260727-gpt-llm-blankline-bisection: judge-safe global squeeze

- Status: active
- Record owner: gpt
- Work owner: gpt
- Reviewer: codex
- Integrator: codex
- Problem: `little-little-man`
- Base main commit: `e6ed1423a7fb0cda17d1f3db79e82e8831b08244`
- Branch: `agent/gpt-llm-squeeze`
- Progress lease: 15 minutes without concrete evidence
- Created UTC: `2026-07-27T04:00:34Z`
- Last updated UTC: `2026-07-27T04:00:34Z`

## Outcome

Find and preserve a judge-safe subset of globally blank rows and columns in the
accepted 749×25,797 `llm_codex_01` machine. Use the Rust/fast executor to test
behavior, preserve every logical pipe binding, and hand off only a strictly
better full-public candidate.

## Exclusive write set

- `coordination/tasks/20260727-gpt-llm-blankline-bisection.md`
- `coordination/status/gpt.md`
- `coordination/messages/gpt/`
- `experiments/gpt-llm-squeeze/`
- `reports/2026-07-27-gpt-llm-squeeze.md`

## Shared read-only paths

- `submissions/llm/llm_codex_01.man`
- `scripts/build_codex_llm.py`
- LLM fixtures, reports, binding certificate, Rust executor and fastsim sources
- `src/littleman/alexey_squeeze.py`
- `src/littleman/server_compat.py`

## Do not touch

- `main`
- existing numbered `.man` artifacts, response JSON, or catalogues
- Memory/TCP/Reverse/Snake paths claimed by other agents
- `codex/`, `claude/`, `alexey/`, and other agents' status/message namespaces
- generic simulator, parser, package, lock, or contest API infrastructure

## Deliverables

- Reproducible blank-line inventory and candidate builder.
- Independent row-only, column-only, and interaction measurements.
- Full public result under the fastest available exact executor.
- Logical binding comparison, parser/server-layout/minimum-pipe gates.
- Exact candidate, SHA-256, dimensions, footprint, ticks and score if improved.
- Immutable handoff or negative-result message.

## Acceptance checks

- Accepted baseline reproduces 14/14 public cases.
- Candidate retains 145 rooms, 231 pipes, and 143 men unless a separately
  justified structural transformation is recorded.
- Every `s/S/r/R/U/q` instruction resolves to the same logical pipe role.
- `server_compat.validate_layout` passes; every pipe has at least two cells.
- All 14 public cases pass at the official 50,000,000-tick cap.
- Candidate score is strictly below the accepted local baseline.
- Local, projected, and live facts remain separate.

## Contest authority

Read-only contest API: unavailable to GPT.

Contest submission: forbidden. Codex must perform Git/API freshness, release
validation, immutable naming, and terminal-result preservation.

## Handoff

Push exact experiment code, candidate/result artifacts, report, status and an
immutable message to Codex, with Claude and Alexey copied.