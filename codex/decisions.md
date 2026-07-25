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

## 2026-07-25 — Make confirmed server differences one submission gate

Keep the shared simulator semantics stable, but expose
`littleman.server_compat` as the pre-submission judge. Reject layouts whenever
two locally parsed rooms share border cells, since the server fails to load
that geometry. Delegate execution to the wall-tolerant judge, since the server
halts a man after a final wall step while continuing to drain output already
in flight.

Use a coordinate-owner index rather than pairwise room intersections so the
check remains practical for the 2,121-room Subset Sum artifact.

## 2026-07-25 — Compact Plotter through explicit layout parameters

Do not change the validated symmetric-Bresenham state machines. Parameterize
the inter-room pipe clearances and compiler right padding, preserve the former
constants as `BASELINE_LAYOUT`, and define a separate `COMPACT_LAYOUT` at the
smallest values that keep routes disjoint and pipe parsing unchanged.

Preserve both generated artifacts and reject a geometry candidate unless it
matches the public cases, the deterministic 20-segment frame oracle, and the
server-compatibility layout check.

## 2026-07-25 — Treat recovered platform sources as immutable lineage

Preserve all four newly downloaded Packet Reassembly sources with their exact
hashes, including the `tcp_05 == tcp_01` duplicate. Represent the winning
`tcp_02` structurally as room programs, placements, and pipe routes, and
require the generator to reproduce the recovered bytes exactly.

Do not invent the missing submission UUID. Identify `tcp_02` as the counted
winner only from the arithmetic proof supplied by its 38×38 footprint and the
displayed 5,981,625.6 score.

## 2026-07-25 — Prefer in-band control to timing probes

When FIFO order and the value domain permit, carry phase/count tokens behind
the data and synchronize with blocking receive. The retained `sort_05`
applies this rule to remove `q` and its settling corridor. Preserve protocol
and geometry as one new numbered candidate because both contribute to its
measured improvement.

Keep layout semantics explicit: nearest-pipe selection, pipe capacity, and the
bounding square are acceptance conditions, not post-processing details.

## 2026-07-25 — Separate measured candidates from packing bounds

Retain `reverse_02` because a generated artifact passes full local validation
and improves score. Record the Sudoku rectangle calculation and Subset Sum
coordinate probe only as bounds: neither is a candidate until all routes parse
and public judging succeeds.

For analytical score models, charge per-operation overhead for the full
assumed operation count. Label projections as estimates and correct them
before using them to authorize a machine build.

## 2026-07-25 — Coordinate two agents through ownership, not shared editing

Require separate Git worktrees and agent branches for concurrent writers.
Designate one integrator as the only writer to `main` and one submission
controller as the only agent allowed to perform an explicitly authorized
contest mutation.

Split work into independently verifiable tasks with one owner and an exclusive
write set. Use owner-specific status files and immutable sender-owned messages
instead of a jointly edited live checklist. A handoff is complete only when it
names a pushed commit, exact validation evidence, measurements, assumptions,
and integration notes.

## 2026-07-25 — Use a 15-minute concrete-progress lease for Claude

Claude may stop voluntarily. When an active Claude task has no new inspectable
evidence for 15 minutes, Codex may issue a stop/takeover and reassign the work
without requesting further user approval.

Do not treat timestamp churn as progress. Inspect the peer branch and any
announced long-running job first, preserve Claude's worktree and commits, and
establish a new exclusive owner before continuing from a separate branch or
solution version.

## 2026-07-25 — Retain Sudoku state machines and fold only their geometry

Preserve `sudoku_00` and every compiled room program byte-for-byte. Place the
row and column worker modules in an upper row, center the box worker below,
and regenerate only the broadcaster, command, result, and output routes.

Keep four columns between upper worker envelopes: three would put a command
corridor adjacent to a room wall. Accept the fold only after exact artifact
reproduction, ring-capacity assertions, public and directed duplicate tests,
and the server-compatibility gate. Preserve the result as unsubmitted
`sudoku_01`.
