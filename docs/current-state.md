# Current State

Updated: 2026-07-27

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
  `data/small/problems/`. Snake `snake_04` is accepted 17/17 at 150×129 and
  score 848,516,029.4117646; its four-cell state-ring reduction is documented
  in `reports/2026-07-26-snake-ring-margin.md`. Pathfinder `pathfinder_02`
  deletes 84 judge-safe rows and is accepted 18/18 at 187×1,873, score
  16,071,390,291,617.668, and rank 42 in the
  `2026-07-27T00:32:10.377Z` snapshot; its submission is
  `4b714c9e-d0e0-455a-857e-b06a30fa0e39`. Claude's pressed
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
- Sort `tarstars_sort_08` removes one inert return column while preserving the
  17-cell shrinking ring. It is live 25/25 at 18×18, score 802,301.76, and
  rank 45 in the `2026-07-26T23:56:10.445Z` snapshot. See
  `reports/2026-07-27-sort-18-square.md`.
- History Lesson `history_05` uses a joint exact-DP dictionary and lookup-slot
  search to fit the fixed archive into 82×82. It is live 1/1 at score 6,724
  and rank 17 in the `2026-07-26T23:44:10.311Z` snapshot. See
  `reports/2026-07-27-history-82-square.md`.
- Packet Reassembly `tcp_00` passed 20/20 at 38×41 and score 20,028,106.4.
  Five platform downloads recovered the missing tag-through-ring lineage:
  `tcp_01/tcp_05 -> tcp_04 -> tcp_03 -> tcp_02`. The 38×38 `tcp_02` is
  uniquely identified as the counted 5,981,625.6 winner and now reproduces
  byte-for-byte from a structural generator. All recovered sources have
  stable hashes, pass public cases and a 45-case boundary suite, and are
  catalogued under `submissions/tcp/`. The `tcp_08` geometry compacts the
  machine to 31×31. Its `tcp_09` successor adds a two-cell shortcut to the
  packed controller's insertion-return path without changing the footprint
  or any pipe binding. It is the current live best: 20/20 at score
  1,575,127.05 and rank 29/98 in the refreshed snapshot. Only the older
  `tcp_02` submission UUID remains unavailable. See
  `reports/2026-07-27-tcp-hotpath.md`.
- Grade Book `gradebook_05` replaces fixed worker delays with blocking ring
  receives. It is live 20/20 at 382×307, score 47,115,780,603.6, and rank 55
  in the `2026-07-27T00:12:10.405Z` snapshot. Its room contracts and
  substitution tests are in
  `reports/2026-07-26-gradebook-components.md`.
- Matrix Multiply `matmul_08` preserves the folded-controller logic and
  compacts its rings to 99×98. It passed all 20 live cases at server score
  5,931,034,965.9, improving the preceding counted score by 29.70%.
- Sudoku Auditor `sudoku_05` uses one canonical 27-mask state ring in a
  75×131 machine. It passed all 20 live cases at server score 9,290,407,667.5,
  improving the preceding counted score by 17.84%. Its algorithm replacement
  also passed 17 directed order and duplicate workloads locally.
- Memory `tarstars_memory_14` keeps the three-cells-per-word shared relay and
  shortcuts two bounded WRITE paths. It is live 24/24 at 29×30 with score
  14,009,062.5, a 2.64% improvement over `memory_13`, and rank 16 in the
  `2026-07-27T00:22:10.356Z` snapshot. The exact response is
  `submissions/memory/tarstars_memory_14-submit.json`.
- Plotter `plotter_08` fuses error testing, error updating, address generation,
  and the display driver into a compact racetrack. It is live 20/20 at
  130×130, score 1,097,878,080, and rank 58 in the
  `2026-07-27T00:04:10.359Z` snapshot. See
  `reports/2026-07-27-plotter-fused-racetrack.md`.
- Subset Sum is solved by a generated meet-in-the-middle machine with two
  1,024-stage systolic sorters. Its compact 3,646×3,029 artifact passed all
  20 live cases at score 91,769,596,778,389.8. The exact Git-LFS source,
  variant properties, and validation are documented under
  `submissions/subset-sum/` and in
  `reports/2026-07-24-subset-sum.md`.
- Reverse `reverse_08` shortens the input-side ring while keeping the 13×13
  footprint. It is live 20/20 at score 84,423.95 and rank 39 in the
  `2026-07-27T00:34:10.477Z` snapshot; the exact response is
  `submissions/reverse-a-list/alexey-reverse_08-submit.json`. A separate
  `Y`-spawned spatial schedule reverses every one-round length 1–16 under the
  organizer WASM, but still needs a proven multi-round lifecycle before it
  can replace the counted machine; see
  `reports/2026-07-26-gpt-reverse-y.md`.
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
