# 20260726-gpt-subset-sum-verify: independently verify reinflated candidate

- Status: active
- Record owner: gpt
- Work owner: gpt
- Reviewer: codex
- Integrator: codex
- Candidate owner: alexey
- Problem: `subset-sum`
- Base main commit: `0410f654f71425990bf3e1c7d70a0bc2317d3e39`
- Branch: `agent/gpt-subset-verify`
- Progress lease: 15 minutes without concrete evidence
- Created UTC: `2026-07-26T17:53:53Z`
- Last updated UTC: `2026-07-26T17:53:53Z`

## Outcome

Independently build and judge Alexey's full-squeeze-plus-reinflation Subset Sum
candidate, preserving Alexey's ownership. Produce structural gates, backend,
case results, ticks, score and a review of whether same ports plus restored pipe
lengths preserve the relevant semantics.

## Exclusive write set

- `coordination/tasks/20260726-gpt-subset-sum-verify.md`
- `coordination/status/gpt.md`
- `coordination/messages/gpt/`
- `experiments/gpt-subset-sum-verify/`
- `reports/2026-07-26-gpt-subset-sum-verify.md`

## Shared read-only paths

- `experiments/alexey-subset-sum/`
- `submissions/subset-sum/`
- `src/littleman/subset_sum.py`
- `src/littleman/alexey_squeeze.py`
- `src/littleman/alexey_piperoute.py`
- simulator, judge, fastsim and Rust executor sources
- Alexey's task, status and messages

## Do not touch

- `main`
- Alexey's candidate files, experiment directory, status or message namespace
- existing numbered `.man` artifacts, responses or catalogues
- `codex/`, `claude/`, package/lock files and shared state

## Deliverables

- Independent generated candidate under `experiments/gpt-subset-sum-verify/`.
- Structural report: rooms, men, pipes, min pipe, shared walls, dimensions,
  footprint, per-pipe length comparison and binding caveats.
- Full public judge result using the fastest available local backend.
- Exact artifact hash and deterministic result JSON.
- Immutable response to Alexey and Codex.

## Acceptance checks

- Candidate builds from `build_subset_sum()` plus full squeeze and reinflation.
- Every rerouted pipe retains its original source/destination attachment and
  target cell count, or failures are listed explicitly.
- Parsed counts remain `2121 rooms / 2164 pipes / 2119 men`.
- All pipes have at least two cells and no shared walls.
- Full public result records cases passed, failures, ticks, footprint and score.
- No claim that equal length alone preserves behavior without checking pipe
  identity/order, endpoint binding and whole-machine judge behavior.

## Contest authority

Read-only contest API: not needed.

Contest submission: forbidden. Alexey retains candidate and submission control;
GPT only returns independent evidence.

## Handoff

Push the exact verification script, candidate hash/result JSON, focused report
and immutable message. Alexey may use the evidence; Codex reviews integration.
