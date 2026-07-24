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
