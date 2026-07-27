# 20260727-gradebook-rank-step: produce a submittable Grade Book rank gain

- Status: active
- Record owner: codex_3
- Work owner: codex_3
- Reviewer: claude
- Integrator: claude
- Problem: gradebook
- Base main commit: ad0324bb6ef915c195a1cde9a3115689131c99a2
- Branch: agent/codex_3
- Progress lease: 15 minutes without concrete evidence
- Created UTC: 2026-07-27T08:48:06Z
- Last updated UTC: 2026-07-27T08:48:06Z

## Outcome

Produce one independently reproducible Grade Book candidate that improves on
live `gradebook_05` enough to target the next rank. The freshly measured live
threshold is score `46,112,231,167`, approximately a 1.022x improvement over
`47,115,780,603.6`.

## Exclusive write set

- `coordination/tasks/20260727-gradebook-rank-step.md`
- `coordination/status/codex_3.md`
- `coordination/messages/codex_3/`
- `experiments/codex_3-gradebook/`
- `tests/test_codex3_gradebook_rank_step.py`
- `submissions/gradebook/codex3_gradebook_06.man`
- `reports/2026-07-27-codex3-gradebook-rank-step.md`

## Shared read-only paths

- `submissions/gradebook/gradebook_05.man`
- `submissions/gradebook/gradebook_05-submit.json`
- `submissions/gradebook/variants.json`
- `src/littleman/gradebook.py`
- `src/littleman/gradebook_components.py`
- `src/littleman/gradebook_press.py`
- `src/littleman/alexey_squeeze.py`
- `src/littleman/alexey_stairfold.py`
- `src/littleman/sim.py`
- `src/littleman/room_lab.py`
- `src/littleman/room_shrink.py`
- `src/littleman/room_compact.py`
- `src/littleman/room_reflow.py`
- `scripts/preflight.py`
- `scripts/wasm_judge.py`
- `data/small/problems/gradebook.json`

## Do not touch

- `main`
- `codex/`
- `claude/`
- other agents' status, messages, task records, branches, and write sets
- existing immutable Grade Book artifacts and submit responses
- shared Grade Book catalogs and live-result metadata
- contest submission API

## Deliverables

- deterministic experiment or generator under `experiments/codex_3-gradebook/`
- exact candidate `submissions/gradebook/codex3_gradebook_06.man`
- focused validation and measured public-case score in
  `reports/2026-07-27-codex3-gradebook-rank-step.md`
- immutable handoff message to Claude naming the full commit

## Acceptance checks

- `uv run python scripts/preflight.py submissions/gradebook/codex3_gradebook_06.man gradebook` passes all seven public cases with no structural error
- `uv run python scripts/wasm_judge.py submissions/gradebook/codex3_gradebook_06.man gradebook` passes 7/7 under the organizers' WASM
- candidate public score is lower than the like-for-like public score of `gradebook_05`; target at least 1.022x to cross the current live next-rank threshold
- deterministic regeneration reproduces the exact candidate SHA-256

## Contest authority

Read-only API access: allowed for freshness reconciliation by the integrator.

Contest submission: forbidden unless the user separately authorizes the exact
candidate and the submission controller accepts the handoff.

## Handoff

Push one scoped commit with the generator, exact `.man`, focused tests, report,
and immutable `handoff` message. Claude reviews, runs the mandatory WASM gate,
performs live freshness reconciliation, and alone decides integration and any
submission.