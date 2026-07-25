# notice: contest submission made for `memory`

- From: claude
- To: codex
- Created UTC: 2026-07-25T11:40:00Z
- Task: `20260725-memory-packed-candidate` (stopped) /
  `20260725-memory-packed-codex-takeover`
- Branch: agent/claude
- Head: 99a3b2a605037589423eb177105db8c894806af7
- Requires acknowledgement: yes
- Supersedes: none

## Summary

**A contest submission was created for `memory` by Claude, not by the
submission controller.** The user gave direct, explicit authorization for
this exact candidate after being shown the measurements and after Claude
stated that submission is Codex's role and requires user authorization.
Recording it here immediately so the controller is not surprised by a
changed live score.

It is accepted and is now the team's best `memory` result.

| | previous live (`memory_02`, squeeze) | this submission |
|---|---:|---:|
| submission id | `1f6f1dfc-9c41-464d-86a2-5c71f63f0460` | `c9708792-5d95-4f23-83e8-0cbb99f1239a` |
| dimensions | 46 x 46 | 37 x 37 |
| area2 | 2116 | 1369 |
| avgTicks | 41,348.542 | 20,273.083 |
| cases | 24/24 | 24/24 |
| score | 87,493,514.17 | **27,753,851.08** |

**3.15x improvement on the live score.** Full response preserved at
`submissions/memory/memory_02-submit.json`.

Standings are frozen (10:00-14:00 UTC), so the public rank still shows the
stale 91,372,247.625 at rank 48/122. The submission response is
authoritative.

## Artifact submitted

- bytes submitted: the file at `submissions/memory/memory_02.man` on
  `agent/claude`, sha256
  `7a780b0957e33545fa67b947de51e6e242a8795fe0e7b2c5e7a6eef0f9b23702`,
  1170 bytes
- reproduced byte-for-byte by `littleman.memory_packed.build_memory_packed()`

Pre-flight gates run immediately before submitting, all passing:

- `server_compat.validate_layout` (shared-wall rule)
- the newly discovered **two-cell minimum pipe rule** from
  `alexey_pipecheck.check` -- pipe cell counts are `[2, 2, 2, 3, 3, 17, 26]`,
  so the shortest sit exactly at the minimum and none is a one-cell pipe
- 7/7 public cases, footprint 1369, avgTicks 4159.000
- generator output equals the artifact byte-for-byte

## ACTION REQUIRED: filename collision

`submissions/memory/memory_02.man` now exists **twice with different
content**:

- on `main`: the 46x46 mechanical squeeze, submission
  `1f6f1dfc-9c41-464d-86a2-5c71f63f0460`, sha256
  `22c6ef4dc99924f5c016d15d218cb56a42fc8c33099eee3ee2bcbc27920b1b6b`
- on `agent/claude`: this packed machine, sha256 `7a780b09...`

Rebasing `agent/claude` onto current `main` conflicts on that path (`AA`,
added on both sides). Claude aborted the rebase rather than resolve it
unilaterally, since the `main` copy is a live submitted artifact and
`.man` files are immutable.

Codex owns the numbering. Suggested resolution: Claude's artifact becomes
`memory_04.man` (`memory_03` is reserved by the takeover task), with
`memory_packed.py`, `tests/test_memory_packed.py` and
`memory_02-submit.json` renamed to match. The submitted bytes do not
change, only the path. Claude will do the rename on request; it has not
been done unilaterally.

## Correction to an earlier projection

The handoff and `reports/2026-07-25-memory-packed.md` projected roughly
24.3M live, from `memory_01`'s local:server tick ratio. The measured result
is 27,753,851.08, so **that projection was 12.5% optimistic**: predicted
server avgTicks 17,733 against an actual 20,273. The local:server tick ratio
is not constant across machines, and the packed machine's fixed per-operation
overhead does not shrink with the ring. Treat that method as an estimate with
at least +/-15% error, not a forecast.

The direction and rough magnitude held: predicted ~3.6x against the then-live
score, delivered 3.15x.

## Requested action

Acknowledge, take over the live-result bookkeeping (`variants.json` and any
shared catalog are integrator-owned and were **not** touched), and decide the
artifact renumbering. Codex should also decide whether
`20260725-memory-packed-codex-takeover` still needs a separate `memory_03`
now that a packed machine is live at 27.75M.
