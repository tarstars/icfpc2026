# GPT local submission candidates: MatMul and Sudoku

Date: 2026-07-26

Branch: `agent/gpt`

Task: `20260726-gpt-preserve-local-candidates`

## Scope and status

At the user's direct request, this branch preserves two complete `.man`
candidates that had already been generated and locally validated from the
uploaded repository snapshot. Their exact artifacts, generators and benchmark
JSON are committed under `experiments/gpt-submission-candidates/`.

These are **unsubmitted candidates**, not live results. GPT has GitHub access
but no contest API connector or usable repository `.env` execution path, so the
mandatory live-score freshness gate was not performed. No shared submission
catalogue, terminal response JSON or `docs/current-state.md` entry was changed.
Codex must query the live problem state before promotion or submission.

## Exact preservation check

The Git blob SHA returned by GitHub for every committed file equals the blob
SHA computed over the original local file with `git hash-object`. Therefore the
branch contains byte-identical copies of the validated local artifacts.

| File | Git blob SHA |
|---|---|
| `matmul_08.man` | `486dc988a9b21dc3e6b5c24c204ea8d1aa2e8ecc` |
| `sudoku_05_single_ring.man` | `722302cd8ccd78a809b43b6324a20845bd1254f0` |
| `generate_matmul_08.py` | `007e00fe00a2955df950721ea6af236ed0443f63` |
| `generate_sudoku_05.py` | `4962f7df958334b5412aab964a0c3def9ef61fc7` |
| `sudoku_single_generator.py` | `0b7b493f5ae50e7a7d774893d5215cd0c94d7779` |
| `matmul_08_benchmark.json` | `96860427b6d65ce8e0d1404ad190502f3b1a697a` |
| `sudoku_single_benchmark.json` | `e452837910c6cfe3e3b10a7dacbff8edb06d35bd` |

## Matrix Multiply candidate

Artifact:

```text
experiments/gpt-submission-candidates/matmul_08.man
```

Parent: `submissions/matmul/matmul_07.man`.

Transformation:

1. delete 16 globally squeezable columns;
2. reroute the A ring inside the resulting `99x98` box;
3. preserve exactly 256 A-ring cells, so the maximum `16x16` input fits;
4. preserve the 268-cell B ring and every compute-room program.

Exact identity and measurements:

- SHA-256: `6d77cb4dac845d620a3f39804c345cb818c17de3d7577af848bc0ea8a9cc685e`
- dimensions: `99x98`
- footprint: `9,801`
- rooms / men / pipes: `12 / 10 / 19`
- minimum pipe length: `3`
- matrix-ring capacities: `256` and `268`
- public cases: `7/7`
- public ticks: `16,019; 21,531; 72,679; 2,476,351; 460,351; 125,153; 255,047`
- average public ticks: `489,590.142857`
- local score: `4,798,472,990.142857`
- exact local score reduction versus `matmul_07`: `29.6869349%`
- additional deterministic matrices previously run: `35/35`, including
  `16x16x16`, skinny dimensions and signed extrema
- `littleman.server_compat`: passed in the original validation
- minimum-pipe gate: passed in the original validation

This is the lower-risk candidate: it preserves machine logic and storage
capacity and changes geometry/routing only.

Reproduction:

```bash
cd <repo>
PYTHONPATH=src python3 \
  experiments/gpt-submission-candidates/generate_matmul_08.py \
  submissions/matmul/matmul_07.man /tmp/matmul_08.man
sha256sum /tmp/matmul_08.man
cmp /tmp/matmul_08.man \
  experiments/gpt-submission-candidates/matmul_08.man
```

Observed during this handoff:

```text
6d77cb4dac845d620a3f39804c345cb818c17de3d7577af848bc0ea8a9cc685e
byte-exact reproduction: PASS
```

Public recheck command:

```bash
PYTHONPATH=src python3 scripts/benchmark_candidates.py matmul \
  experiments/gpt-submission-candidates/matmul_08.man \
  --parent submissions/matmul/matmul_07.man
```

Observed again during this handoff: `7/7`, `99x98`, score
`4,798,472,990.142857`, with the exact SHA-256 above.

Problem ID: `58f54636-3ec4-497d-8102-b486f13a1ed1`.

## Sudoku Auditor candidate

Artifact:

```text
experiments/gpt-submission-candidates/sudoku_05_single_ring.man
```

Parent for score comparison: `submissions/sudoku-validity/sudoku_04.man`.

Architecture:

- one canonical FIFO ring stores all 27 row, column and box masks;
- each `(r,c,v)` input computes four skip counts;
- row `r`, column `c` and box `3*(r//3)+c//3` are updated in one canonical
  state-ring scan;
- duplicate flags are combined before the verdict;
- the state ring returns to canonical order before the next cell.

Exact identity and measurements:

- SHA-256: `16860f965aa0e57c1b2e031a6a650c3bde2ae195961e8a164a2fe8e1cc58b49d`
- dimensions: `75x131`
- footprint: `17,161`
- rooms / men / pipes: `11 / 9 / 18`
- minimum pipe length: `2`
- public cases: `6/6`
- public ticks: `904,546; 40,888; 849,168; 51,958; 450,588; 904,538`
- average public ticks: `533,614.333333`
- local score: `9,157,355,574.333334`
- exact local score reduction versus `sudoku_04`: `17.8326001%`
- additional deterministic cases previously run: `17/17`, including a full
  valid grid and directed row, column and box duplicates
- `littleman.server_compat`: passed in the original validation
- minimum-pipe gate: passed in the original validation

This is an algorithm replacement. It has stronger directed testing but more
hidden-case risk than the geometry-only MatMul candidate.

Reproduction:

```bash
cd <repo>
PYTHONPATH=src python3 \
  experiments/gpt-submission-candidates/generate_sudoku_05.py \
  /tmp/sudoku_05_single_ring.man
sha256sum /tmp/sudoku_05_single_ring.man
cmp /tmp/sudoku_05_single_ring.man \
  experiments/gpt-submission-candidates/sudoku_05_single_ring.man
```

Observed during this handoff:

```text
16860f965aa0e57c1b2e031a6a650c3bde2ae195961e8a164a2fe8e1cc58b49d
byte-exact reproduction: PASS
```

Public recheck command:

```bash
PYTHONPATH=src python3 scripts/benchmark_candidates.py sudoku-validity \
  experiments/gpt-submission-candidates/sudoku_05_single_ring.man \
  --parent submissions/sudoku-validity/sudoku_04.man
```

Observed again during this handoff: `6/6`, `75x131`, score
`9,157,355,574.333334`, with the exact SHA-256 above.

Problem ID: `f66c928f-3369-4870-9153-8b20cafc2ecd`.

## Integration and submission checklist

Before either artifact becomes a numbered solution or is submitted, Codex
should:

1. fetch `agent/gpt` and verify the Git blob and SHA-256 identities;
2. fetch/integrate current `origin/main` and check for same-name artifacts on
   all active branches;
3. query the exact problem through the contest API and compare the current
   counted score and latest submission with these local candidates;
4. rerun reproduction, public benchmark, server compatibility and the focused
   directed suites in the integration environment;
5. choose a collision-safe immutable filename and update the problem catalogue;
6. submit only with explicit user authorization for the exact SHA-256;
7. preserve the terminal response JSON beside the promoted artifact.

No contest-side mutation occurred in this task.
