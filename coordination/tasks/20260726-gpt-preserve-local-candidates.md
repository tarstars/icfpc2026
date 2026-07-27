# 20260726-gpt-preserve-local-candidates: preserve validated `.man` candidates

- Status: handoff ready; write set released except GPT status/messages
- Record owner: gpt
- Work owner: gpt
- Reviewer: codex
- Integrator: codex
- Problems: `matmul`, `sudoku-validity`
- Base main commit: `36f4778deef6635314705b3d018568ee4969c24d`
- Branch: `agent/gpt`
- Progress lease: complete
- Created UTC: `2026-07-26T17:42:55Z`
- Last updated UTC: `2026-07-26T17:50:33Z`

## Outcome

Preserve the exact bytes of two already locally validated candidates, together
with their reproduction scripts and benchmark evidence, so other agents can
review and promote them. This is a user-directed preservation task, not a live
submission or shared-catalog update.

## Delivered paths

- `experiments/gpt-submission-candidates/matmul_08.man`
- `experiments/gpt-submission-candidates/generate_matmul_08.py`
- `experiments/gpt-submission-candidates/matmul_08_benchmark.json`
- `experiments/gpt-submission-candidates/sudoku_05_single_ring.man`
- `experiments/gpt-submission-candidates/generate_sudoku_05.py`
- `experiments/gpt-submission-candidates/sudoku_single_generator.py`
- `experiments/gpt-submission-candidates/sudoku_single_benchmark.json`
- `reports/2026-07-26-gpt-local-submission-candidates.md`

## Exact artifact identities

- MatMul SHA-256:
  `6d77cb4dac845d620a3f39804c345cb818c17de3d7577af848bc0ea8a9cc685e`
- MatMul Git blob:
  `486dc988a9b21dc3e6b5c24c204ea8d1aa2e8ecc`
- Sudoku SHA-256:
  `16860f965aa0e57c1b2e031a6a650c3bde2ae195961e8a164a2fe8e1cc58b49d`
- Sudoku Git blob:
  `722302cd8ccd78a809b43b6324a20845bd1254f0`

The GitHub-returned blob SHAs equal `git hash-object` over the original local
files, proving byte-identical preservation.

## Acceptance evidence

### Reproduction

Both generators were rerun from the uploaded repository snapshot:

```text
matmul_08: 6d77cb4dac845d620a3f39804c345cb818c17de3d7577af848bc0ea8a9cc685e
sudoku_05: 16860f965aa0e57c1b2e031a6a650c3bde2ae195961e8a164a2fe8e1cc58b49d
byte-exact reproduction: PASS
```

### Public benchmark recheck

MatMul:

- `7/7`
- `99x98`
- local score `4,798,472,990.142857`
- exact score reduction versus `matmul_07`: `29.6869349%`

Sudoku:

- `6/6`
- `75x131`
- local score `9,157,355,574.333334`
- exact score reduction versus `sudoku_04`: `17.8326001%`

The original directed suites remain recorded as `35/35` for MatMul and `17/17`
for Sudoku. Original `littleman.server_compat` and minimum-pipe gates passed.

## Freshness limitation

GPT has GitHub access but no contest API connector or usable repository `.env`
execution path. Therefore these files are preserved under `experiments/`, not
promoted into shared submission catalogues. Codex must perform the mandated
fresh contest query before integration, renaming, or submission.

## Contest authority

No contest-side mutation occurred. No terminal response JSON exists for either
candidate.

## Handoff

The focused report contains exact commands, measurements, risks and the
promotion checklist. An immutable handoff message to Codex, Claude and Alexey
names the final branch head and requests Codex review.
