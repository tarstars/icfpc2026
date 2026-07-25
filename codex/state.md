# Codex State

Updated: 2026-07-24

## Objective

Provide safe, reusable contest API access while Claude develops littleman
solutions.

## Completed

- Established shared repository layout and policies.
- Established Codex handoff files.
- Added a fail-closed external-storage preflight.
- Provisioned and validated all logical bulk roots on `medium_data`.
- Added a stable, boot-safe UUID entry for `medium_data` to `/etc/fstab`.
- Configured common large artifact formats for Git LFS.
- Retrieved the team bearer key through the normal CAPTCHA-protected browser
  login and stored all credentials only in the ignored, mode-0600 `.env`.
- Added a `uv`-managed API client with public problem/clock reads,
  authenticated submission reads and waits, and explicitly confirmed
  submission creation.
- Added shared API tool descriptions and tests.
- Implemented a generated 16-stage streaming Sort pipeline, passed all 7
  public cases locally, and submitted it successfully for 25/25 server cases.
- Preserved Sort variants in a machine-readable catalogue and submitted the
  geometry-only 92×92 successor successfully for 25/25 server cases and a
  38,830,462.08 server score.
- Implemented and preserved a radix-packed 89×89 History Lesson solution; it
  passed 1/1 live at score 7,921 and tied rank 7 at the recorded snapshot.
- Corrected the local judge to honor footprint-only scoring.
- Matched local backtick pairing to the stricter server parser after preserving
  the initial rejected candidate and its load error.
- Implemented a 38×41 Packet Reassembly ring candidate that passes all six
  public cases at local score 12,232,076.67.
- Preserved and submitted its exact source; it passed 20/20 live with score
  20,028,106.4.
- Implemented a four-worker Grade Book candidate with chained
  acknowledgements and generated compact control geometry. It passes all
  seven public cases at 494×462, worst-case 444,421 ticks, and local score
  37,077,609,660. Its exact source and properties are preserved under
  `submissions/gradebook/`; it passed 20/20 live with server score
  124,123,713,433.2.
- Added a mandatory pre-commit solution freshness policy: pull/integrate
  GitHub and query the exact problem's live API score before every solution
  version commit.
- Implemented and preserved three Matrix Multiply candidates. The best
  nested-ring geometry occupies 183×180, passes all seven public cases below
  the tick cap, and improves the measured local score 60.25× over the
  16-worker baseline. It passed all 20 live cases at server score
  33,286,994,352.
- Implemented a parallel row/column/box mask-ring Sudoku Auditor. It passed
  all six public cases, deterministic valid-prefix and forced-duplicate
  tests, and all 20 live cases at server score 105,335,908,125.2.
- Completed the geometry-only Memory compaction from the shared handoff. The
  46×47 candidate passed all 24 live cases and reduced the server score from
  181,952,075.875 to 91,372,247.625.
- Implemented a generated symmetric-Bresenham Plotter without modifying the
  protected earlier sketch. It matched 20 deterministic oracle segments and
  passed all 20 live cases at server score 75,794,498,065.
- Implemented a meet-in-the-middle Subset Sum machine with two 1,024-stage
  systolic sorters and lexicographic mask reduction. Its exact 9,743,784-byte
  artifact passed all seven public and all 20 live cases at server score
  91,769,596,778,389.8.
- Reworked simulator pipe shifting and scheduling around active pipes,
  run-indexed occupancy, blocked-worker wakeups, cached nearest ports, and a
  persistent room occupancy map. The full 137-test suite passes.
- Parameterized Grade Book worker spacing, command clearances, compiler right
  padding, and vertical bands while preserving `gradebook_00` exactly. The
  454×450 `gradebook_01` improves local score 16.00% and passed all 20 live
  cases at server score 104,303,579,599.6, a 15.97% live improvement.

## Blockers

- None for API access.

## Next steps

1. Evaluate compact geometry or faster protocols for other preserved
   footprint-tick baselines.
2. Support Claude with live problem retrieval, submission, and result polling.
