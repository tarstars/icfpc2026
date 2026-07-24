# Codex State

Updated: 2026-07-24

## Objective

Initialize the ICFPC 2026 workspace without prematurely choosing a solver
architecture or implementation language.

## Completed

- Established shared repository layout and policies.
- Established Codex handoff files.
- Added a fail-closed external-storage preflight.
- Provisioned and validated all logical bulk roots on `medium_data`.
- Added a stable, boot-safe UUID entry for `medium_data` to `/etc/fstab`.
- Configured common large artifact formats for Git LFS.

## Blockers

- Contest materials are not yet present.

## Next steps

1. On contest release, capture the statement, exact input, checksums,
   constraints, scoring, and submission interface.
2. Build a parser/validator and a deterministic baseline before optimization.
