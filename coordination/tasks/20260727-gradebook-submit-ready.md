# 20260727-gradebook-submit-ready: produce a gated Grade Book rank-step candidate

- Status: active
- Record owner: codex_3
- Work owner: codex_3
- Reviewer: claude
- Integrator: claude
- Problem: gradebook
- Base main commit: 7e658b4d8a9e5fda14fbabe422cc023609455c8f
- Branch: agent/codex_3-gradebook-submit-ready
- Progress lease: 15 minutes without concrete evidence
- Created UTC: 2026-07-27T10:12:00Z
- Last updated UTC: 2026-07-27T10:12:00Z

## Outcome

Turn the reverse-ack/result-handshake Grade Book experiment into one exact,
reviewable `.man` candidate that passes the repository's authoritative
value-output gates and is not worse than live `gradebook_05`. Aim for the fresh
rank-60 threshold `46,112,231,167`, a `1.022x` improvement over live
`47,115,780,603.6`.

## Exclusive write set

- `coordination/tasks/20260727-gradebook-submit-ready.md`
- `coordination/status/codex_3.md`
- `coordination/messages/codex_3/`
- `experiments/codex_3-gradebook-submit/`
- `tests/test_codex3_gradebook_submit_ready.py`
- `submissions/gradebook/codex3_gradebook_06.man`
- `reports/2026-07-27-codex3-gradebook-submit-ready.md`

## Shared read-only paths

- draft PR #3 and branch `agent/codex_3`
- `submissions/gradebook/gradebook_05.man`
- `submissions/gradebook/gradebook_05-submit.json`
- `submissions/gradebook/variants.json`
- `src/littleman/gradebook.py`
- `src/littleman/gradebook_components.py`
- `src/littleman/gradebook_press.py`
- `src/littleman/alexey_squeeze.py`
- `src/littleman/alexey_stairfold.py`
- `src/littleman/sim.py`
- `src/littleman/fastsim.py`
- `scripts/preflight.py`
- `scripts/subdb.py`
- `scripts/wasm_judge.py`
- `data/small/problems/gradebook.json`

## Do not touch

- `main`
- other agents' branches, task records, status files, messages, and write sets
- existing immutable Grade Book artifacts and terminal responses
- shared catalogs and live-result metadata
- contest API

## Deliverables

- deterministic current-main generator under
  `experiments/codex_3-gradebook-submit/`
- exact candidate `submissions/gradebook/codex3_gradebook_06.man` with SHA-256
- focused regression/adversarial checks and a measured same-judge comparison
- immutable handoff message naming the full payload commit

## Acceptance checks

- regenerate the exact candidate byte-for-byte
- `uv run pytest -q tests/test_codex3_gradebook_submit_ready.py` passes
- `uv run python scripts/preflight.py submissions/gradebook/codex3_gradebook_06.man gradebook` passes all seven public cases and structural checks
- `uv run python scripts/subdb.py compare submissions/gradebook/codex3_gradebook_06.man gradebook` reports the candidate not worse than the live machine using one judge
- `uv run python scripts/wasm_judge.py submissions/gradebook/codex3_gradebook_06.man gradebook` passes 7/7; Grade Book is value-output based, so this is authoritative
- preserve or explicitly prove adequate capacity for every shortened pipe

## Contest authority

Read-only live-state reconciliation: allowed for Claude/integrator.

Contest submission: forbidden for codex_3. Claude remains the sole submission
controller and may submit only after exact-artifact freshness reconciliation.

## Handoff

Hand over by 11:40Z with the candidate path, SHA-256, exact commands, measured
public/live comparison, known failures, and no unlabelled projections.