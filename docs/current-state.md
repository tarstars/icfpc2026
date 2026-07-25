# Current State

Updated: 2026-07-25

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
- All 12 graded problems are solved. In the standings snapshot updated at
  `2026-07-25T05:56:56Z`, every counted result passed all private cases; the
  weakest ranks were Sudoku 42/46, Plotter 37/43, Subset Sum 29/35, and
  Matrix Multiply 24/36.
- Before committing any solution version, agents must pull and integrate the
  current GitHub branch and query the exact problem's current score/submission
  state through the contest API; the mandatory freshness policy is in
  `AGENTS.md`.
- Concurrent work now uses the repository-backed protocol in
  `docs/two-agent-protocol.md`: isolated agent worktrees, one integrator for
  `main`, one serialized submission controller, explicit task write sets, and
  owner-specific status and immutable messages under `coordination/`.
- The current live Sort best is the 19×19 shrinking-ring `sort_03`; it passed
  all 25 server cases at score 1,455,739.72. The validated local `sort_05`
  carries its remaining count as an in-band FIFO token and folds the return
  pipe into an 18×18 square. It passes all public and 308 deterministic stress
  workloads at local score 778,062.86, 16.20% below `sort_03`; it has not been
  submitted.
- The server-safe 89×89 History Lesson program passed 1/1 with footprint score
  7,921.
- Packet Reassembly `tcp_00` passed 20/20 at 38×41 and score 20,028,106.4.
  Five platform downloads recovered the missing tag-through-ring lineage:
  `tcp_01/tcp_05 -> tcp_04 -> tcp_03 -> tcp_02`. The 38×38 `tcp_02` is
  uniquely identified as the counted 5,981,625.6 winner and now reproduces
  byte-for-byte from a structural generator. All recovered sources have
  stable hashes, pass public cases and a 45-case boundary suite, and are
  catalogued under `submissions/tcp/`. Only its submission UUID remains
  unavailable.
- Grade Book `gradebook_01` compacts the accepted four-worker baseline from
  494×462 to 454×450 without changing its protocols. It passed all 20 live
  cases and improved the server score 15.97%, from 124,123,713,433.2 to
  104,303,579,599.6. The exact variants are under
  `submissions/gradebook/`; the optimization is documented in
  `reports/2026-07-24-grade-book-optimization.md`.
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
- The Memory packing feasibility model proves that three signed cell values
  fit in one signed-64 word using base `2**21`, reducing the record ring from
  100 values to 34 words. Twenty-six focused tests pass. A corrected
  conservative projection estimates a 17.19% score reduction; a real
  `memory_02` machine remains to be built and measured.
- Plotter is solved by a generated symmetric-Bresenham pipeline. The first
  correctness baseline passed all 20 live cases at 394×535 and score
  75,794,498,065. A geometry-only 388×441 successor, `plotter_01`, passes all
  public and deterministic oracle cases locally and improves the measured
  local score by 32.98%; it has not been submitted.
- Subset Sum is solved by a generated meet-in-the-middle machine with two
  1,024-stage systolic sorters. Its compact 3,646×3,029 artifact passed all
  20 live cases at score 91,769,596,778,389.8. The exact Git-LFS source,
  variant properties, and validation are documented under
  `submissions/subset-sum/` and in
  `reports/2026-07-24-subset-sum.md`.
- Reverse has a validated local geometry successor: `reverse_02` preserves the
  corridor-free room programs, reroutes the 17-cell FIFO above the relay, and
  shrinks 16×16 to 15×15. It passes all public and 260 deterministic stress
  workloads at local score 261,393.75, 12.15% below live `reverse_01`; it has
  not been submitted.
- TCP-derived transfer audits are complete for Grade Book, Matrix, Brackets,
  Plotter, Sudoku, and Subset Sum. They record two rejected standalone
  protocol changes, a 306-square Sudoku packing bound, and a Subset Sum
  relocation probe that reaches the 3,029 height bound but exposes a specific
  pipe-route collision. See `reports/2026-07-25-tcp-transfer-audits.md`.
- `littleman.server_compat` is the pre-submission judge for the two confirmed
  parser differences: it rejects locally accepted shared-wall rooms and
  permits a final wall step after a send while the output pipe drains.

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
