# Handoff: preserved MatMul and Sudoku `.man` candidates

- From: gpt
- To: codex
- CC: claude, alexey
- Created UTC: `2026-07-26T17:50:33Z`
- Task: `20260726-gpt-preserve-local-candidates`
- Branch: `agent/gpt`
- Payload commit: `a25edd900b93067988c47d8a2f53126299e67dcb`
- Requires acknowledgement: yes

## Summary

At the user's direct request, I committed the two locally validated `.man`
candidates that had previously existed only under `/mnt/data`. They are stored
under `experiments/gpt-submission-candidates/` because GPT cannot perform the
repository's mandatory contest-API freshness query. No catalogue or live-result
metadata was changed.

## Exact artifacts

### Matrix Multiply

```text
experiments/gpt-submission-candidates/matmul_08.man
SHA-256 6d77cb4dac845d620a3f39804c345cb818c17de3d7577af848bc0ea8a9cc685e
Git blob 486dc988a9b21dc3e6b5c24c204ea8d1aa2e8ecc
```

Local result:

- parent: `matmul_07`
- dimensions: `99x98`
- public: `7/7`
- average ticks: `489,590.142857`
- local score: `4,798,472,990.142857`
- exact local reduction: `29.6869349%`
- directed suite previously recorded: `35/35`
- server compatibility and minimum-pipe gates previously passed

This candidate preserves room logic and the 256/268-cell matrix-ring
capacities; it is the lower-risk candidate.

### Sudoku Auditor

```text
experiments/gpt-submission-candidates/sudoku_05_single_ring.man
SHA-256 16860f965aa0e57c1b2e031a6a650c3bde2ae195961e8a164a2fe8e1cc58b49d
Git blob 722302cd8ccd78a809b43b6324a20845bd1254f0
```

Local result:

- comparison parent: `sudoku_04`
- dimensions: `75x131`
- public: `6/6`
- average ticks: `533,614.333333`
- local score: `9,157,355,574.333334`
- exact local reduction: `17.8326001%`
- directed suite previously recorded: `17/17`
- server compatibility and minimum-pipe gates previously passed

This is a single-27-mask-ring algorithm replacement and therefore carries more
hidden-case risk.

## Diff scope

New files only:

```text
experiments/gpt-submission-candidates/matmul_08.man
experiments/gpt-submission-candidates/generate_matmul_08.py
experiments/gpt-submission-candidates/matmul_08_benchmark.json
experiments/gpt-submission-candidates/sudoku_05_single_ring.man
experiments/gpt-submission-candidates/generate_sudoku_05.py
experiments/gpt-submission-candidates/sudoku_single_generator.py
experiments/gpt-submission-candidates/sudoku_single_benchmark.json
reports/2026-07-26-gpt-local-submission-candidates.md
coordination/tasks/20260726-gpt-preserve-local-candidates.md
```

GPT status/messages were updated in GPT-owned paths. No existing solution,
shared state, package, simulator or peer-owned file was modified.

## Validation repeated during handoff

### Byte-exact generation

```bash
cd <uploaded-snapshot>
PYTHONPATH=src python3 \
  /mnt/data/generate_matmul_08.py \
  submissions/matmul/matmul_07.man /tmp/repro_matmul_08.man
PYTHONPATH=src python3 \
  /mnt/data/generate_sudoku_05.py /tmp/repro_sudoku_05.man
cmp /tmp/repro_matmul_08.man /mnt/data/matmul_08.man
cmp /tmp/repro_sudoku_05.man /mnt/data/sudoku_05_single_ring.man
```

Observed: both comparisons passed and both SHA-256 values matched exactly.

### Public benchmark

```bash
PYTHONPATH=src python3 scripts/benchmark_candidates.py matmul \
  /mnt/data/matmul_08.man \
  --parent submissions/matmul/matmul_07.man

PYTHONPATH=src python3 scripts/benchmark_candidates.py sudoku-validity \
  /mnt/data/sudoku_05_single_ring.man \
  --parent submissions/sudoku-validity/sudoku_04.man
```

Observed again: MatMul `7/7`; Sudoku `6/6`; exact metrics above.

### Git preservation

For every committed file, the blob SHA fetched back from GitHub equals
`git hash-object` over the original local file. The committed bytes are exact.

## Unverified / required before promotion

- No fresh contest API query was possible from GPT.
- No hidden cases or live score are claimed.
- No same-name collision audit across every active peer branch was performed;
  use a collision-safe immutable name during promotion.
- Sudoku deserves additional random/adversarial review because it replaces the
  architecture rather than only geometry.

## Requested Codex action

1. Acknowledge this handoff.
2. Fetch `agent/gpt` and rerun the risk-proportionate checks.
3. Query current MatMul and Sudoku live state through the contest API.
4. If still beneficial, create a separate freshness-gated solution task,
   promote with collision-safe immutable filenames and update catalogues.
5. Submit only with explicit user authorization for the exact SHA-256 and
   preserve the terminal response JSON.

## Contest mutation

None.
