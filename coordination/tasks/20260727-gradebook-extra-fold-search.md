# 20260727-gradebook-extra-fold-search: improve the live codex_3 Grade Book again

- Status: active
- Record owner: codex_3
- Work owner: codex_3
- Reviewer: claude
- Integrator: claude
- Problem: gradebook
- Base main commit: b240cc2d67a125a31cc50c167283b7049de47210
- Branch: agent/codex_3-gradebook-v2
- Progress lease: 15 minutes without concrete evidence
- Created UTC: 2026-07-27T10:20:00Z
- Last updated UTC: 2026-07-27T10:20:00Z

## Outcome

Starting from the live `submissions/gradebook/codex3_gradebook_06.man`, search
for additional behaviour-preserving staircase folds inside the parser and four
subject engines. Produce one exact candidate only if it improves the
like-for-like public score while leaving the outer box and every pipe length
unchanged.

The live baseline is 20/20 at 379x315, score `34,760,655,166.75`, submission
`c2a5a3e9-0341-4f67-9127-ce0c035eb21d`. The authoritative assignment is
`coordination/ASSIGNMENTS.md` at main commit
`0198ebc110500a4298d86c9a498f37a9b5b2cabf`.

## Exclusive write set

- `coordination/tasks/20260727-gradebook-extra-fold-search.md`
- `coordination/status/codex_3.md`
- `coordination/messages/codex_3/`
- `experiments/codex_3-gradebook-v2/`
- `tests/test_codex3_gradebook_v2_search.py`
- `submissions/gradebook/codex3_gradebook_07.man`
- `reports/2026-07-27-codex3-gradebook-v2.md`

## Shared read-only paths

- `coordination/ASSIGNMENTS.md`
- `submissions/gradebook/codex3_gradebook_06.man`
- `submissions/gradebook/codex3_gradebook_06-submit.json`
- `experiments/codex_3-gradebook/build.py`
- `experiments/codex_3-gradebook/stress.py`
- `src/littleman/gradebook_components.py`
- `src/littleman/alexey_stairfold.py`
- `src/littleman/sim.py`
- `src/littleman/fastsim.py`
- `src/littleman/server_compat.py`
- `scripts/subdb.py`
- `scripts/wasm_judge.py`
- `data/small/problems/gradebook.json`

## Do not touch

- `main`
- old `agent/codex_3*` branches
- other agents' task, status, message, report, experiment, and solution paths
- existing immutable Grade Book artifacts and terminal responses
- shared catalogs and live-result metadata
- contest API

## Deliverables

- deterministic beam/greedy search over additional room folds
- exact candidate `codex3_gradebook_07.man` when an improvement is found
- machine-readable search report plus concise Markdown handoff
- immutable message to Claude naming the payload commit and decisive commands

## Acceptance checks

- baseline reproduction matches 379x315 and 31 pipe lengths
- candidate dimensions stay 379x315
- candidate room, pipe, and man counts match baseline
- candidate pipe-length tuple is byte-for-byte identical to baseline
- all seven public cases pass under the current repository judge
- adversarial randomized and ordered-transition suites from the first handoff pass
- `scripts/subdb.py compare` says the candidate is not worse than live
- `scripts/wasm_judge.py` passes 7/7; Grade Book is value-output based

## Contest authority

Read-only live-state reconciliation: allowed for Claude/integrator.

Contest submission: forbidden for codex_3. Claude remains the sole submission
controller.

## Handoff

Hand over the exact candidate, SHA-256, added fold vector, public ticks/score,
pipe-length equality result, stress results, and full commands. If no additional
fold survives, publish the negative frontier and release immediately.