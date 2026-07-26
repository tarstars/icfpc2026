# Current State

Updated: 2026-07-26

## Objective

Compete in ICFPC 2026 (live 2026-07-24 → 07-27). The task is the
**littleman** language: 2D ASCII-grid programs walked by "little men",
communicating through pipes, with I/O rooms and an LM-75 display.

## Contest facts

- Task docs archived: `docs/textbook.md`, `docs/language-reference.md`,
  `docs/grading.md`, `docs/rules.md`, `docs/api.md`.
- 20 problems released so far (16 graded in "Semester 1–4", 4 practice);
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
- All 12 Semester 1–3 graded problems are solved. In the standings snapshot
  updated at `2026-07-25T05:56:56Z`, every counted result passed all private
  cases; the weakest ranks were Sudoku 42/46, Plotter 37/43, Subset Sum
  29/35, and Matrix Multiply 24/36.
- Semester 4 added four graded 16×16-display problems: `snake`, `pathfinder`,
  `little-little-little-man` (LLLM), and `little-little-man` (LLM). Their
  exact API specifications and 36 total public cases are attached under
  `data/small/problems/`. Snake `snake_03` is accepted 17/17 at 150×129 and
  score 854,937,794.1176472. Pathfinder submission
  `0c04a141-a73b-443c-a274-741bfe67d857` is accepted 18/18. Claude's pressed
  LLLM submission `efce1ac1-ece0-4557-a08e-4d34edd9dd4d` is accepted 21/21
  at 307×312 and score 22,187,469,586.285713. LLM submission
  `be96c6eb-e2bd-40a7-b5d2-a3aadbaf2b9b` is accepted 28/28 at server score
  8,775,033,253,482,888; its exact artifact and response are preserved. See
  `reports/2026-07-25-semester-4-release.md` and the latest immutable
  messages under `coordination/messages/`.
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
- History Lesson's live `history_02` is 85×85, passed 1/1, and scores 7,225.
  The validated `history_03` asymmetric archive is 84×84, passes the public
  case in 1,783,519 ticks, and scores 7,056 locally; see
  `reports/2026-07-26-history-asymmetric-archive.md`.
- Packet Reassembly `tcp_00` passed 20/20 at 38×41 and score 20,028,106.4.
  Five platform downloads recovered the missing tag-through-ring lineage:
  `tcp_01/tcp_05 -> tcp_04 -> tcp_03 -> tcp_02`. The 38×38 `tcp_02` is
  uniquely identified as the counted 5,981,625.6 winner and now reproduces
  byte-for-byte from a structural generator. All recovered sources have
  stable hashes, pass public cases and a 45-case boundary suite, and are
  catalogued under `submissions/tcp/`. The later `tcp_08` geometry keeps all
  six room interiors unchanged, compacts the machine to 31×31, and is the
  current live best: 20/20 at score 1,640,475.05, independently refreshed
  through the API. Only the older `tcp_02` submission UUID remains
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
  average 529,549.7 ticks, and score 105,335,908,125.2. The unsubmitted
  geometry-only `sudoku_01` folds its unchanged workers into two rows,
  occupies 286×285, passes the focused compatibility and adversarial gates,
  and improves measured local score 59.15%. Details and exact sources are in
  `reports/2026-07-25-sudoku-two-row.md` and
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
  Plotter, Sudoku, and Subset Sum. The Sudoku packing bound has since become
  the validated 286-square `sudoku_01`; the Subset Sum relocation probe still
  reaches the 3,029 height bound but exposes a specific pipe-route collision.
  See `reports/2026-07-25-tcp-transfer-audits.md`.
- `littleman.server_compat` is the pre-submission judge for the two confirmed
  parser differences: it rejects locally accepted shared-wall rooms and
  permits a final wall step after a send while the output pipe drains.
- The exact Rust executor on `agent/codex-rust` retains the Python parser,
  lowers to a versioned dense IR, and executes through PyO3 or a standalone
  Rayon CLI. It reduced the expanded 2,012-test LLM suite from 858.86 to
  53.08 seconds, and ran all 14 public LLM cases (173.6 million judged ticks)
  deterministically in 4.93 seconds with eight workers. Acceptance evidence
  is in `reports/2026-07-26-rust-executor.md`. A missing-extension fallback
  found by Claude's independent review is fixed in `a899e03`; forced fallback
  now passes 108 tests with 11 native-only skips. The clean
  `agent/codex-main-integration` candidate merges current `origin/main`, both
  agent lineages, and passes the full repository suite: 3,822 passed, two
  skipped, four expected xfails, zero failures. Peer review is approved;
  the guarded non-force promotion placed release commit `6efbc49` on
  `origin/main`.

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
