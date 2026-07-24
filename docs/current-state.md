# Current State

Updated: 2026-07-24

## Objective

Compete in ICFPC 2026 (live 2026-07-24 → 07-27). The task is the
**littleman** language: 2D ASCII-grid programs walked by "little men",
communicating through pipes, with I/O rooms and an LM-75 display.

## Contest facts

- Task docs archived: `docs/textbook.md`, `docs/language-reference.md`,
  `docs/grading.md`, `docs/rules.md`, `docs/api.md`.
- 16 problems released so far (12 graded in "Semester 1–3", 4 practice);
  specs + public test data in `data/small/problems/`.
- Scoring per problem: up to 1 point for test-case fraction + up to 1 point
  for ranking vs other teams. Program score = `max(width,height)² × avg
  ticks` (footprint-tick; lower is better); a few problems are
  footprint-only. Step cap usually 5M ticks; programs ≤ 10 MB.
- Submissions via editor or REST API (`/api/v1`), bearer token per team,
  best submission counts, max 5 pending. Scoreboard freezes at hours 22–26
  and from hour 70.
- Values are signed 64-bit, wrapping. Execution is deterministic.

## Repository

- Shared layout and operating policy are initialized.
- Small tracked data belongs in `data/small`.
- Bulk data is separated behind five external-backed logical roots.
- Python 3.10+ and `uv` manage the simulator, judge harness, tests, and contest
  API client.
- `uv run icfpc-api` provides JSON problem reads and guarded submission/polling
  commands; local credentials remain in the ignored `.env`.
- Before committing any solution version, agents must pull and integrate the
  current GitHub branch and query the exact problem's current score/submission
  state through the contest API; the mandatory freshness policy is in
  `AGENTS.md`.
- Three submitted Sort variants passed all 25 server cases. The current best is
  the 27×24 shrinking-ring `sort_02`, with server score 3,460,708.8. The
  earlier pipeline variants and their geometry-only optimization are preserved
  under `submissions/sort/`; their experiment is summarized in
  `reports/2026-07-24-sort-pipeline.md`.
- The server-safe 89×89 History Lesson program passed 1/1 with footprint score
  7,921 and is tied at rank 7 in its recorded standings snapshot.
- The submitted 38×41 Packet Reassembly paired-value ring passed all 20 server
  cases with score 20,028,106.4; the immutable source and properties are under
  `submissions/tcp/`.
- The submitted 494×462 Grade Book candidate passed all 20 server cases with
  average 508,628.7 ticks and score 124,123,713,433.2. Its exact source and
  properties are under `submissions/gradebook/`, with architecture and metrics
  in `reports/2026-07-24-grade-book.md`.
- Three Matrix Multiply candidates are preserved under `submissions/matmul/`.
  The best compact nested-ring geometry occupies 183×180, passes all seven
  public cases, including 16×16×16 in 4,198,400 ticks, and improves the local
  score 60.25× over the parallel baseline. Details are in
  `reports/2026-07-24-matrix-multiply.md`. `matmul_02` passed all 20 live
  cases at server score 33,286,994,352.
- The first Sudoku Auditor candidate passed all 20 live cases at 446×200,
  average 529,549.7 ticks, and score 105,335,908,125.2. Its parallel mask-ring
  architecture and exact source are documented in
  `reports/2026-07-24-sudoku-auditor.md` and
  `submissions/sudoku-validity/`.
- Memory `memory_01` preserves the submitted pipeline logic but relocates one
  room to shrink the machine from 67×38 to 46×47. It passed 24/24 live and
  improved the server score from 181,952,075.875 to 91,372,247.625. Details
  are in `reports/2026-07-24-memory-compaction.md`.
- Plotter is solved by a generated symmetric-Bresenham pipeline. The first
  correctness baseline passed all 20 live cases at 394×535 and score
  75,794,498,065. Its exact source and private-test-oriented validation are
  documented in `reports/2026-07-24-plotter.md`.

## Storage

- The filesystem labeled `medium_data` is mounted at the observed path
  `/media/tarstars/medium_data`.
- `/etc/fstab` identifies it by UUID, uses `nofail`, and preserves `nosuid` and
  `nodev`; boot is not blocked when the USB disk is absent.
- Its provisioned project root is
  `/media/tarstars/medium_data/database/icfpc2026`.
- All five repository symlinks resolve beneath that root and are writable by
  `tarstars`.
- The mandatory preflight passed with a 400 GiB required-free-space floor;
  observed free space was `457867780096` bytes (about 426 GiB).

## Tooling gaps

- Git LFS 3.0.2 is installed and initialized for the current user. Common
  heavyweight formats are covered by `.gitattributes`.
- YT access and credentials have not been probed for this new project.

## Active workflow

1. Develop and judge candidate `.man` programs against the archived public
   cases.
2. Before any submission, verify the graded problem ID and preserve the exact
   locally judged source.
3. Submit only through the confirmed API command and poll its terminal result.
