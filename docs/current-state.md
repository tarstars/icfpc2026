# Current State

Updated: 2026-07-24

## Objective

Prepare a durable workspace for ICFPC 2026. The contest specification and
implementation language are not known yet.

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
