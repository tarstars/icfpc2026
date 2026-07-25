# Codex Validation

Updated: 2026-07-25

## Environment observations

- Repository branch: `main`, initially at commit `a32ef8c`.
- `medium_data` is mounted at `/media/tarstars/medium_data` as ext4.
- Observed free space at initialization: approximately 427 GiB.
- Git LFS 3.0.2 is installed from the Ubuntu Jammy repository.
- Non-interactive sudo is unavailable.

## Validation performed

- `python3 -m py_compile scripts/check_external_storage.py` — passed.
- `python3 scripts/check_external_storage.py --required-free-gib 1` — exited
  with status 2 as designed, naming the absent physical project root and all
  five missing symlink targets.
- `git diff --check` — passed.
- `git check-ignore -v` — confirmed all five external-backed symlinks are
  ignored by their explicit root rules.
- Repository layout audit — confirmed no files were added to `claude/`.
- `/etc/fstab` verification — zero parse errors; the `medium_data` UUID
  resolves to `/dev/sda1`, with `nofail`, `nosuid`, and `nodev` active in the
  persisted configuration.
- `python3 scripts/check_external_storage.py --required-free-gib 400` — passed
  for all five symlinks with `457867780096` free bytes.
- Create/resolve/delete probes through every logical bulk root — passed; every
  probe resolved beneath
  `/media/tarstars/medium_data/database/icfpc2026`.
- `git lfs install` — passed and updated the user-level Git hooks.
- `git lfs env` and `git lfs status` — passed for this repository.
- `git check-attr` — confirmed `.pt` and `.zip` use the LFS filter while
  ordinary source such as `.cpp` remains normal text.
- Browser login through the contest's normal Cloudflare Turnstile flow —
  succeeded; the API-key endpoint returned HTTP 200 and the key was stored
  without displaying it.
- `uv lock && uv sync` — resolved and installed the API client dependencies.
- `uv run pytest -q` — 33 tests passed, including six API client tests.
- `uv run icfpc-api --compact problems` — live HTTP request returned 16
  problems with the expected identifiers and status fields.
- `uv run icfpc-api --compact problem reverse-a-list` — live HTTP request
  returned the problem and eight public cases.
- `uv run icfpc-api --compact clock` — reported the contest started and
  submissions open.
- `uv run icfpc-api submission __credential_probe__` — returned
  `404 not_found`, confirming the bearer key was accepted rather than rejected
  with `401`; no submission was created.
- `uv run pytest -q` — 38 tests passed after adding the Sort stage, loader,
  reset, and multi-round integration tests.
- `uv run python -m littleman submissions/sort/sort.man sort-numbers` — passed
  all 7 public cases with footprint 10,201; per-case ticks and score are in
  `reports/2026-07-24-sort-pipeline.md`.
- Submitted SHA-256
  `668318060ad980c95b34c9cda5c2f8f9f3d377a5e777f143346c6553bd2f2bd4`
  once as submission `1a673762-fe78-4d26-bced-5063fd49b221`; the server
  reported `done`, 25/25 cases passed, width 96, height 101, and no error.
- `build_sort()` still reproduces the submitted baseline SHA-256 exactly.
- The geometry-only `sort_01` candidate passed all 7 public cases at 92×92;
  its SHA-256 is
  `ddb1341dc8321b8b9b121383e81eb27629c78ee407a82a52540cfdec7ce76877`,
  and its local score is 31,000,004.57 versus 40,379,929.86 for the baseline.
- Submitted that exact candidate once as
  `2e8dbabf-02fd-4701-b811-cf1dec8aba95`; the server reported `done`, 25/25,
  92×92, average ticks 4,587.72, score 38,830,462.08, and no error.
- The unfrozen Sort standings snapshot updated at
  `2026-07-24T16:02:12.313Z` placed `wheezards` 17th with 1.448275862 points.
- Preserved rejected History submission
  `b91aa4d8-d904-484f-9ed3-46aa2566598e`; it exposed stricter server pairing
  for vertically aligned backticks and ran no cases.
- Tightened the simulator parser and added a regression test for that rule.
- `history_01.man` passed the exact 2,810-byte output locally in 192,736 ticks
  and live as submission `7f3e13a3-99e5-42d5-bd08-24b968d0d398`, at 89×89
  and score 7,921. Its SHA-256 is
  `157be247ef582e0f761a6fac060eee3cdf82e7cb509d172b922da3b408295351`.
- Both checked-in History artifacts exactly match their recorded generators.
- A judge regression test confirms footprint-only scores ignore ticks.
- The generated Packet Reassembly candidate passed all six public cases with
  ticks `[1850, 6380, 9830, 5610, 200, 19790]`, footprint 1,681, and local
  score 12,232,076.67.
- A maximum-size stream made of three reverse-ordered 16-packet windows passed
  in 29,750 ticks.
- The Packet ring's measured parking pipe has capacity 38 values, above the
  32-value maximum; both settling corridors exceed its full round-trip path.
- `uv run pytest -q` — 67 tests passed after adding Packet Reassembly.
- `uvx ruff check` and `uvx ruff format --check` passed for the Packet source
  and tests.
- `tcp_00.man` exactly matches `build_tcp()` and retains SHA-256
  `fd8f78f09ce01b1221fb5935deb26808086029791337f5e73fe77060b38420b1`.
- Submitted that exact artifact once as
  `65939c21-197f-4124-b6eb-2043e615f665`; the server reported `done`, 20/20,
  38×41, average ticks 11,914.4, score 20,028,106.4, and no error.
- The unfrozen Packet standings snapshot updated at
  `2026-07-24T17:32:12.065Z` placed `wheezards` fifth of 25 rows with
  1.8260869565 points.
- The generated Grade Book candidate parsed as 16 rooms and 30 pipes and
  passed all seven public cases with ticks
  `[40753, 125295, 131664, 103892, 148646, 68874, 444421]`.
- Its dimensions are 494×462, footprint 244,036, average public ticks 151,935,
  local score 37,077,609,660, and generated size 224,886 bytes. The generated
  text SHA-256 is
  `16a9fe2c71ae917470c16f5021594f4573efc57266e43c399ab1215a96ada522`.
- `submissions/gradebook/gradebook_00.man` exactly matches
  `build_gradebook()` and the recorded SHA-256.
- `uv run pytest -q` — 78 tests passed after adding Grade Book and sparse pipe
  shifting.
- `uvx ruff check` passed for the Grade Book, simulator, and Grade Book tests;
  `uvx ruff format --check` passed for the new source and tests.
- `git diff --check` — passed after the Grade Book implementation and report.
- Submitted that exact Grade Book artifact once as
  `97526857-55b8-4e83-9ad5-2864afb3a02e`; the server reported `done`, 20/20,
  494×462, average ticks 508,628.7, score 124,123,713,433.2, and no error.
- `matmul_00` passed all seven Matrix Multiply public cases with ticks
  `[43976, 54494, 138024, 1660920, 482316, 208409, 327120]`, dimensions
  1,982×291, footprint 3,928,324, and local score
  1,636,011,699,416.5713.
- `matmul_01` parsed as 11 rooms, 9 men, and 18 pipes. Its two matrix return
  pipes have capacities 350 and 276 for the 256-value maximum.
- `matmul_01` passed all seven public cases with ticks
  `[23726, 31502, 109586, 4198442, 718378, 189656, 405220]`, dimensions
  109×289, footprint 80,656, and local score 65,406,370,080.
- All three checked-in Matrix artifacts exactly match their generators and
  recorded SHA-256 hashes.
- Geometry-only `matmul_02` parsed as 12 rooms, 10 men, and 19 pipes. Its A/B
  return capacities are 334 and 268.
- `matmul_02` passed all seven public cases with ticks
  `[23684, 31460, 109544, 4198400, 718336, 189614, 405178]`, occupied
  dimensions 183×180, footprint 33,489, and local score 27,155,828,232.
- Submitted exact SHA-256
  `4d4b47c05a39fa1f428d45748e1a0d5b8af4de240eec6aad2d76adb9b8570e5b`
  as `c2e95f37-585d-41b2-8f71-a255345fa784`; the server reported `done`,
  20/20, 183×180, average ticks 993,968, score 33,286,994,352, and no error.
- The unfrozen Matrix standings snapshot updated at
  `2026-07-24T20:32:11.660Z` placed `wheezards` ninth of 19 rows with
  1.5555555556 points.
- `scripts/benchmark_candidates.py` reproduced the checked-in Max Element
  candidate through the canonical judge and emitted deterministic JSON with
  exact-file hashes, dimensions, case ticks, score, and parent comparison.
- Five deterministic Matrix adversarial cases (seed `20260724`) passed against
  a Python multiplication oracle, covering boundary dimensions M=16, K=16,
  N=16, alternating ±99 values, mixed signs, and varied shapes.
- `uv run pytest -q` — 92 tests passed after Matrix, exact benchmarking,
  standings API access, adversarial coverage, and simulator movement lookup
  optimization.
- `sudoku_00` passed all six public cases with ticks
  `[885889, 38489, 831560, 49336, 440472, 885893]`, occupied dimensions
  446×200, footprint 198,916, average ticks 521,939.8333333333, and local
  score 103,822,183,887.33333.
- Eight deterministic shuffled valid-prefix cases (seeds `20260724..20260731`)
  and three directed row/column/box duplicate cases passed against the Python
  oracle.
- Submitted exact SHA-256
  `150abdba2a07421dc37cf975fc68a2313e7cee727bd582597f9ad15923d2d11a`
  as `09a4a36c-3ff5-4560-a57a-f14879767fe4`; the server reported `done`,
  20/20, 446×200, average ticks 529,549.7, score 105,335,908,125.2, and no
  error.
- The unfrozen Sudoku standings snapshot updated at
  `2026-07-24T21:04:11.324Z` placed `wheezards` 28th of 32 rows with
  1.1290322581 points.
- `uv run pytest -q` — 95 tests passed after adding and submitting Sudoku
  Auditor.
- `memory_01` reproduced exactly from `build_memory_compact`, parsed at 46×47,
  and passed all seven public cases at ticks
  `[179, 1301, 3744, 2498, 3776, 1269, 55482]`, footprint 2,209, and local
  score 21,537,434.42857143.
- `uv run pytest tests/test_memory_rooms.py tests/test_memory_compact.py -q`
  — 4 tests passed.
- Submitted SHA-256
  `68d5fb3d73f21c7171ad59dde0f6b22a493cbba297f7bc1f8dcbab04cad92089`
  as `22931081-bd2d-4c19-a733-b8035e5bf0af`; the server reported `done`,
  24/24, 46×47, average ticks 41,363.625, score 91,372,247.625, and no
  error.
- The unfrozen Memory standings snapshot updated at
  `2026-07-24T21:22:11.313Z` placed `wheezards` 25th of 85 rows with
  1.7 points.
- `uv run pytest -q` — 119 tests passed in 763.90 seconds after the Memory
  geometry change and its regression coverage.
- The generated Plotter setup pipeline emitted exact constants for four
  directed segments. All six public cases passed at ticks
  `[90404, 215202, 5759, 137648, 312647, 326976]`, footprint 286,225, and
  local score 51,932,473,183.333336.
- A deterministic 20-round test at seed `20260724` matched every frame from
  the Python symmetric-Bresenham oracle and completed at tick 1,051,453.
- `uv run pytest tests/test_codex_plotter.py -q` — 3 tests passed in
  29.16 seconds.
- Submitted SHA-256
  `13a1322961d8985bc165fd03f93070640dc4ee4b653c49c1d9f1dd4588bf8e03`
  as `4c1aa9a7-6362-46c6-a62e-8bc814d871f6`; the server reported `done`,
  20/20, 394×535, average ticks 264,807.4, score 75,794,498,065, and no
  error.
- `uv run pytest -q` — 122 tests passed in 785.02 seconds after adding the
  complete Plotter pipeline and oracle coverage.
- The unfrozen Plotter standings snapshot updated at
  `2026-07-24T21:52:57.148Z` placed `wheezards` 19th of 30 rows with
  1.3793103448 points.
- The final compact Subset Sum artifact reproduced exactly from
  `build_subset_sum()` at 9,743,784 bytes and SHA-256
  `cd1000a2b5b944e6905e991022116f5b6a6daf7729c4a93bd13f72a683c65d77`.
  It parsed as 2,121 rooms, 2,164 pipes, and 2,119 men, with occupied
  dimensions 3,646×3,029 and footprint 13,293,316.
- All seven Subset Sum public cases passed under the 15,000,000-tick cap at
  ticks `[6640497, 7199445, 6718443, 7274629, 6468694, 7263957, 7378811]`.
  Average ticks were 6,992,068 and local score was 92,947,769,417,488.
- The exact compact geometry was tested rather than relying on the earlier
  oversized layout. Focused coverage includes equal-sum ordering, padded
  slots, and a seeded core integration test choosing the greatest valid mask.
- A 10,000-operation deterministic randomized test confirmed run-indexed
  `Pipe.put`, `Pipe.take`, and `Pipe.shift` behavior against the prior
  cell-by-cell model.
- `uv run pytest -q` — 127 tests passed in 53.83 seconds after the final
  Subset Sum geometry and simulator scheduling changes.
- Submitted the exact compact artifact once as
  `edda50dc-411e-49b6-83eb-0e895d4c1f7e`; the server reported `done`, 20/20,
  3,646×3,029, average ticks 6,903,439.05, score
  91,769,596,778,389.8, and no error.
- The unfrozen Subset Sum standings snapshot updated at
  `2026-07-25T00:56:57.514Z` placed `wheezards` 20th of 26 rows with
  1.2083333333 points.
- `gradebook_00.man` still reproduces its accepted SHA-256 exactly after the
  layout parameters were introduced.
- Freshened `main` to `b2f8b58`, integrating the preserved `tcp_01` source,
  generator, model, live response, and handoff. Its exact artifact passed all
  six public cases locally at 62×62 and local score 34,380,095.3; its recorded
  live result is 20/20 at score 52,747,175.
- Queried live Packet Reassembly and Plotter standings. The final pre-commit
  Plotter response at `2026-07-25T06:22:56.768Z` unexpectedly contained an
  empty `rows` array while reporting `frozen=false`; no current team score was
  inferred from that response. A direct authenticated read of the preserved
  `plotter_00` submission confirmed 20/20 and score 75,794,498,065.
- `littleman.server_compat` rejected the known server-invalid shared-wall
  `triangle_03`, accepted the server-valid final-wall `triangle_04`, and
  judged its six public cases at 13 ticks and score 832.
- Audited every nonempty saved `.man` artifact: 27 passed the compatibility
  layout check, `triangle_03` produced the expected shared-wall rejection, and
  the previously rejected `history_00` independently retained its known
  invalid-literal load error.
- `plotter_00.man` still reproduces exactly at SHA-256
  `13a1322961d8985bc165fd03f93070640dc4ee4b653c49c1d9f1dd4588bf8e03`.
- Exact `plotter_01.man` has SHA-256
  `d2a42d508ba6c7907b98cac3ffb26228e1fd12cd596030d22fddf8165d6ebe77`,
  is 83,127 bytes, parses as 14 rooms, 18 pipes, and 12 men, and occupies
  388×441.
- `plotter_01` passed all six public cases at ticks
  `[89188, 212274, 5659, 135808, 308359, 322576]`. Its local score is
  34,807,690,764, 32.98% below `plotter_00`.
- The deterministic 20-segment Plotter frame oracle at seed `20260724` passed
  for both layouts; the compact candidate completed at tick 1,037,213.
- `uv run pytest -q` — 142 tests passed in 64.56 seconds.
- Exact-file benchmarking measured `gradebook_01` at 454×450, footprint
  206,116, SHA-256
  `f159eaf92ea37d9df9e66f814e8248c9ce10bb23eb9dbec591fc58f10f98c91f`,
  and 201,291 bytes.
- All seven Grade Book public cases passed at ticks
  `[40334, 124472, 130841, 102968, 147839, 68354, 442953]`, average
  151,108.7142857143, and local score 31,145,923,753.714287. This is a
  15.9980267355% local-score improvement over `gradebook_00`.
- A deterministic seed-`20260724`, N=16, K=4 oracle workload covered 48
  operations across six batches and passed in 1,344,885 ticks.
- All four data-return pipes retain 98 cells, and invalid clearances, padding,
  and vertical gaps are rejected by focused layout tests.
- `uv run pytest tests/test_gradebook.py -q` — 13 tests passed.
- `uv run pytest -q` — 137 tests passed in 57.63 seconds.
- Submitted exact `gradebook_01` once as
  `321cd740-3f00-49f2-9321-36330ab0fe6f`; the server reported `done`, 20/20,
  454×450, average ticks 506,043.1, score 104,303,579,599.6, and no error.
  This improves the previous live score by 15.9680477528%.
- The unfrozen Grade Book standings snapshot updated at
  `2026-07-25T01:14:57.234Z` placed `wheezards` 21st of 31 rows with
  1.3333333333 points.
- Recovered TCP hashes are fixed at
  `61613871dc69…` (`tcp_02`), `8962e6f2eaa2…` (`tcp_03`),
  `7868665ea88c…` (`tcp_04`), and `e5e45693b594…` (`tcp_05`);
  `tcp_05` is byte-identical to `tcp_01`.
- `build_tcp_recovered_best()` reproduces `tcp_02.man` byte-for-byte at
  38×38 and footprint 1,444. All four recovered sources pass six public
  cases, the server-layout gate, and 45 deterministic boundary cases. Their
  maximum boundary ticks are 9,720, 9,730, 10,900, and 30,306 respectively.
- Exact `sort_05` is 342 bytes, SHA-256
  `e8df587d0edfc47198051df54293e9ce48205d7c8b3dbbab92feb2fdd3d0d379`,
  and reproduces from `build_sort_count_token()`. It occupies 18×18 and
  passes seven public cases at ticks
  `[1038, 854, 1080, 758, 1388, 3302, 8390]`, average 2,412, and local score
  778,062.8571428572.
- `sort_05` passed eight worst-shape and 300 seeded randomized workloads; the
  maximum observed completion time was 18,920 ticks. Its layout passes
  `server_compat`.
- Exact `reverse_02` is 233 bytes, SHA-256
  `7ae75df4daa28e173f3f018e80fa98b57ea3babbe55f59ae240ffb6a3124957a`,
  and reproduces from `build_reverse3()`. It occupies 15×15, retains a
  17-cell return FIFO, and passes eight public cases at ticks
  `[331, 515, 563, 969, 429, 165, 1801, 4521]`, local score 261,393.75.
- `reverse_02` passed ten worst-shape and 250 seeded randomized workloads and
  the server-layout gate.
- The corrected Memory packing model charges 12,000 ticks for its default
  `40 ticks/op × 300 ops` assumption. Twenty-six focused tests pass; the
  proven capacity reduction is 100 values to 34 words, while the conservative
  score projection is explicitly estimated at 75,666,269.22 (17.19% lower).
- `uv run pytest -q tests/test_tcp_recovered.py
  tests/test_alexey_sort_ring3.py` — 14 tests passed in 11.23 seconds.
- `uv run pytest -q tests/test_alexey_reverse3.py` — 3 tests passed in
  1.61 seconds.
- `uv run pytest -q tests/test_memory_packing_model.py` — 26 tests passed in
  0.37 seconds.
- `uv run pytest -q` — 185 tests passed in 78.88 seconds after integrating
  recovered TCP, Sort/Reverse candidates, the Memory model, and transfer
  audits.
- Mandatory pre-commit freshness gate: `git pull --ff-only` reported current
  `main` already up to date. Exact standings updated at
  `2026-07-25T07:18:57.240Z` showed Packet Reassembly 20/20 at score
  5,981,625.6 (rank 20), Sort 25/25 at score 1,455,739.72 (rank 29), and
  Reverse 20/20 at score 472,345.6 (rank 54). Direct authenticated reads
  reconfirmed live `sort_03`, `reverse_01`, `tcp_00`, and `tcp_01`.
- Two-agent protocol artifact audit — all 11 Markdown artifacts under
  `coordination/` exist; the task base and Codex status head match
  `832ce90022da9010c299901df2748c9743c5845f`; no `.env` or `claude/` change
  is present; all direct protocol entry-point paths exist.
- `git diff --check` — passed after adding the concurrent-work policy,
  normative protocol, initial status/task records, templates, peer prompt, and
  bookkeeping links.

## Pending validation

- No pending Packet Reassembly submission validation.

No YT connectivity, pool availability, or credentials have been validated for
this project.
