# 20260726-gpt-subset-sum-fine-bisect: fine deletion search

- Status: active
- Record owner: gpt
- Work owner: gpt
- Reviewer: codex
- Integrator: codex
- Candidate owner: alexey
- Problem: `subset-sum`
- Base main commit: `5ba6c3376b76103484d5ded289f2fa2dce3df6a3`
- Branch: `agent/gpt-subset-bisect-fine`
- Progress lease: 15 minutes without concrete evidence
- Created UTC: `2026-07-26T18:27:29Z`
- Last updated UTC: `2026-07-26T18:27:29Z`

## Outcome

Run the judge-driven deletion search at finer granularity than Alexey's active
M4 run: 32 contiguous row groups and 64 contiguous column groups, then combine
and peel only groups that passed independently. Return exact safe deletions,
artifact hash, public metrics and interaction failures to Alexey/Codex.

## Non-overlap

Alexey's `bisect_remote.py` uses 8 row groups and 16 column groups. GPT owns
only the 32/64 refinement under `experiments/gpt-subset-sum-fine-bisect/`.
Alexey retains all candidate and submission authority.

## Exclusive write set

- `coordination/tasks/20260726-gpt-subset-sum-fine-bisect.md`
- `coordination/status/gpt.md`
- `coordination/messages/gpt/`
- `experiments/gpt-subset-sum-fine-bisect/`
- `reports/2026-07-26-gpt-subset-sum-fine-bisect.md`

## Shared read-only paths

- `experiments/alexey-subset-sum/`
- `submissions/subset-sum/`
- `src/littleman/subset_sum.py`
- judge and fastsim sources
- Alexey task/status/messages

## Do not touch

- `main`
- Alexey-owned experiments, solution artifacts, catalogues and messages
- existing numbered `.man` or response JSON
- `codex/`, `claude/`, package/lock files and shared state

## Deliverables

- Parallel fine-group evaluator with deterministic group definitions.
- Per-group pass/fail, dimensions, footprint, score and wall time.
- Passing-group union result and interaction-removal trace.
- If correct and smaller: reproducible candidate hash and result JSON; the
  large `.man` may remain reconstructible rather than committed.
- Focused report and immutable handoff to Alexey/Codex/Claude.

## Acceptance checks

- Regenerated baseline passes all public cases before search.
- Exactly 32 row groups and 64 column groups are defined from the same
  deletable-line lists as `bisect_remote.py`.
- Independent groups are evaluated on the full public suite.
- The retained union is judged after each interaction-removal step.
- Any final candidate passes every public case and structural server gates.
- Results are deterministic and distinguish group-local safety from union
  safety.

## Compute plan

Use four worker processes on the five-core host for independent group tests.
Each worker uses the C fastsim extension. Union/peeling remains serialized.
Memory and worker failures are recorded; no ambiguous partial result is
promoted.

## Contest authority

No contest submission. Alexey retains submission control. GPT returns only
independent evidence and an optional unsubmitted candidate.

## Handoff

Push script, compact result JSON, report and immutable message. Coordinate any
winning deletion set with Alexey before a solution-version commit.
