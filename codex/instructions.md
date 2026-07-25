# Effective instruction-set audit

Audited: 2026-07-25T14:49:51Z

This note records which project instructions currently govern Codex, where
they came from, and which apparent changes are repository changes versus
session/runtime behavior.

## Result

The repository copy of `AGENTS.md` has **not** changed since commit
`bcf901e` at 2026-07-25T10:56:38+03:00. The apparent update is nevertheless
real for this session: the instruction excerpt presented for the `codex/`
directory ended after `Integrity`, while the root `AGENTS.md` that scopes the
whole repository has two later sections:

1. `Two-agent coordination`
2. `Solution commit freshness`

Those root rules apply inside `codex/` even when a shorter excerpt is shown.
The effective project policy is therefore the complete root file, plus the
linked `docs/two-agent-protocol.md`.

Evidence:

```text
git log --follow --format='%h %ad %s' --date=iso-strict -- AGENTS.md
bcf901e 2026-07-25T10:56:38+03:00 Add Claude task liveness policy
ec8b107 2026-07-25T10:51:48+03:00 Establish two-agent coordination protocol
ae75c76 2026-07-24T23:33:53+03:00 Solve and optimize Matrix Multiply
1002711 2026-07-24T12:53:30+03:00 Initialize contest workspace

git diff --quiet bcf901e..HEAD -- AGENTS.md
exit 0
```

Current `AGENTS.md` SHA-256:
`6a34ef463bb34521f53dc959516615c8d69a09fad086f2d747bfe84ec1cb0982`.

## Change 1: solution commits have a freshness gate

Added by `ae75c76` on 2026-07-24 at 23:33:53+03:00.

Before committing a new or changed solution version, the committing agent
must:

1. fetch and integrate the current GitHub `main` before staging the solution;
2. query the exact problem's current contest score and latest submission
   state;
3. reconcile the pulled catalog, live state, and candidate;
4. preserve distinct solution versions and their measured properties;
5. put only command- or API-traceable score facts into metadata and reports.

The integrator repeats this gate before the solution reaches `main`. The rule
is scoped to solution versions; a documentation-only audit does not require a
contest API query.

Practical effect: a locally better candidate is not sufficient evidence for a
solution commit. We first establish that it is newer/different from both Git
and the contest platform and cannot overwrite a stronger lineage.

## Change 2: two writing agents require isolated worktrees

Added by `ec8b107` on 2026-07-25 at 10:51:48+03:00.

When Codex and Claude are both active:

- each writing agent uses its own worktree, branch, and Git index;
- one task has one owner and an exclusive write set;
- Codex is the default integrator and submission controller;
- only the integrator updates `main`, shared hotspots, and contest-side
  mutations;
- Codex edits `codex/`; Claude edits `claude/`;
- each agent owns only its status file and message namespace;
- published messages are immutable and corrections use a new message;
- claims, decisions, measurements, blockers, handoffs, and mutations are not
  synchronized until recorded under `coordination/`;
- peer branch/status/messages are fetched and inspected at task start,
  before shared-path work, at handoff, and before integration.

Practical effect: path ownership alone is not enough to make a shared dirty
worktree safe. If the main checkout contains unrelated changes, Codex must not
pull, rebase, stage, or commit there. It should preserve that checkout and
work from a separate clean worktree/branch.

This audit followed that rule: the main checkout already had three unrelated
untracked files, so the note was written in the clean
`agent/codex-instruction-audit` worktree based on current `origin/main`.

## Change 3: Claude work has a 15-minute evidence lease

Added by `bcf901e` on 2026-07-25 at 10:56:38+03:00.

Claude may stop and release a task at any time. If an active Claude task
shows no new concrete evidence for 15 minutes, Codex may stop/reassign/take
over without seeking additional user approval. Concrete evidence is an
inspectable commit/diff, test or experiment result, narrowed failure, or a
previously announced traceable long-running job—not a repeated intention or
timestamp update.

Before takeover Codex must inspect Claude's status, messages, branch, and
announced jobs; publish a stop/takeover message; preserve Claude's branch;
and establish a new exclusive owner/write set. Claude must then stop,
checkpoint safe partial work, acknowledge, and release the paths.

Practical effect: the lease permits recovery from a stalled assignment, not
destructive cancellation or silent concurrent editing.

## Existing rules that remain important

The earlier parts of `AGENTS.md` were not newly added by these commits, but
remain effective:

- read current state, storage policy, and Codex bookkeeping before task work;
- search this repository first and never broadly scan the large Arcadia
  mounts;
- keep bulk/reproducible artifacts off ordinary Git and validate
  `medium_data` before every bulk write;
- keep submitter and YT worker credentials separate and never log secrets;
- report only command- or artifact-traceable measurements;
- do not edit Claude bookkeeping without explicit user direction.

## YT policy conflict resolved

The audit initially found that the authoritative root/storage policies used
roughly one hour while the user-validated architecture decision used roughly
five minutes. The user clarified on 2026-07-25 that **five minutes is a
preference**, not a hard cutoff.

`AGENTS.md` and `docs/storage-and-compute.md` now match that intent:

- below roughly five minutes, prefer local work;
- above roughly five minutes, prefer evaluating YT for independent CPU work;
- keep interactive work or jobs dominated by YT packaging/startup overhead
  local.

The architecture and operative repository policy are now aligned.

## Session-level behavior versus project policy

The current Codex runtime also restricts subagent creation unless the user or
an applicable project/skill instruction explicitly requests delegation.
That is effective for this session but has no Git provenance and should not
be treated as durable team policy. Repository rules should be changed only
through tracked policy files.
