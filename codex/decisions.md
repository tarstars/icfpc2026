# Codex Decisions

## 2026-07-24 — Keep initialization language-neutral

The contest task is unknown. Create stable directories and policies now, but
defer build-system and language selection until the statement reveals the
dominant constraints.

## 2026-07-24 — Separate compact repository state from bulk storage

Use `medium_data` through stable repo-relative symlinks for bulk data. Keep
source, small cases, manifests, aggregate results, and reports in Git.

## 2026-07-24 — Fail closed on external storage

Resolve the disk by label and validate every logical root before writes.
Broken links must never silently become local directories.

## 2026-07-24 — Reuse neighboring YT conventions

Use the root `//home/delivery_ml/research/tarstars/icfpc2026`, consolidated
table-native data, canonical shared inputs, secure-vault worker credentials,
and roughly one hour of expected local wall time as the point to evaluate YT.

## 2026-07-24 — Keep assistant bookkeeping separate

Codex owns `codex/`; Claude owns `claude/`. Shared facts are promoted into
`docs/` rather than editing the other assistant's private handoff area.

## 2026-07-24 — Keep contest credentials local

Store the web login, password, and bearer key only in the Git-ignored root
`.env` with mode `0600`. Normal tools read only the bearer key, never accept it
as a command-line argument, and never include it in output.

## 2026-07-24 — Guard submission mutations

Public API reads omit authorization. Submission reads use the bearer key.
Creating a submission requires the explicit `--confirm` flag, enforces the
documented size limit locally, and is never retried automatically because an
ambiguous POST failure could otherwise create duplicates.

## 2026-07-24 — Partition Grade Book by subject

Use four parallel subject workers instead of one ring containing every grade.
This makes subject selection spatial, keeps each stored record to an ID/grade
pair, and gives GET, SET, AVG, and TOP one common scan protocol. Chain worker
acknowledgements so the parser waits for all workers through one pipe without
letting an any-pipe receive consume future contest input.

Generate the control rooms from an explicit finite-state graph. Keep the
correctness-first state machine independent from geometry, then compact bands
and edge tracks mechanically.
