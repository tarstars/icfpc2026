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
- No solver, build system, or language toolchain has been selected.

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

## Next trigger

When the contest materials arrive:

1. archive the original statement and input checksum;
2. record constraints and scoring in this file;
3. choose the smallest suitable toolchain;
4. implement parser/validator and tiny fixtures before optimization;
5. establish a reproducible submission command and baseline.
