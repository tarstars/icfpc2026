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

## 2026-07-24 — Use meet-in-the-middle streams for Subset Sum

Split the at-most-20 inputs into fixed ten-slot halves, enumerate 1,024
sum/mask pairs per half, sort the halves in opposite sum order, and merge
against the target. Encode earlier input indices as more-significant mask bits
so selecting the greatest matching combined mask implements the required
lexicographic tie-break directly.

Use systolic insertion stages instead of multi-pass radix routing. Keep
missing input slots as zero-valued generator stages that forcibly clear their
mask bits. Preserve the first accepted program as `subset_sum_00` with
machine-readable geometry, local ticks, hash, and live result.

## 2026-07-24 — Make sparse long-machine simulation event-driven

Maintain occupied pipe runs in addition to the canonical per-cell values,
shift only active pipes, suspend workers blocked on pipe I/O, and wake them
when the relevant pipe changes. Cache nearest-port lookups and maintain room
occupancy incrementally. Preserve tick ordering and the cell representation
as the semantics oracle, with deterministic randomized equivalence tests for
the run index.

## 2026-07-24 — Parameterize Grade Book clearances without changing protocols

Keep the accepted four-worker FSMs, ring capacities, acknowledgement chain,
and result collector unchanged. Expose worker gaps, side margins, command
clearance, external ack clearance, parser/worker separation, and compiled-FSM
right padding through `GradebookLayout`.

Preserve the old defaults as `BASELINE_LAYOUT`. For `COMPACT_LAYOUT`, use a
one-cell corridor between workers, the minimum one-cell external pipe
clearance, one separating row between parser and workers, and no unused
interior column beyond the rightmost control track. Reject parameters that
would place routes on walls or make rooms touch.
