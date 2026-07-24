# Codex Validation

Updated: 2026-07-24

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

## Pending validation

- Packet Reassembly has not been submitted; only local/public-case validation
  is complete.

No YT connectivity, pool availability, or credentials have been validated for
this project.
