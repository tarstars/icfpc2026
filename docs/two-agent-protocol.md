# Two-Agent Work Protocol

Updated: 2026-07-25

This is the normative synchronization protocol for two agents working on the
ICFPC 2026 repository at the same time. Its goals are to prevent duplicate
experiments, lost work, stale solution commits, conflicting Git operations,
and duplicate contest submissions while keeping contest work fast.

The operational entry point and templates live under `coordination/`.

## 1. Topology and roles

Two writing agents must never use the same Git worktree. A shared worktree has
one working tree, branch, and index; path ownership alone cannot make
simultaneous pulls, rebases, staging, and commits safe.

Use:

- one worktree and `agent/<id>` branch per worker;
- one designated **integrator**, who alone updates `main`;
- one designated **submission controller**, normally the integrator, who alone
  performs contest-side mutations.

The default project roles are:

| Role | Default owner | Responsibilities |
| --- | --- | --- |
| Integrator/API reviewer | Codex | Task split, shared hotspots, live-score and submission reconciliation, review, integration, `main`, submit/poll |
| Solver/researcher | Claude | Algorithms, generators, candidate artifacts, focused tests, measurements, and report drafts on an agent branch |

These are defaults, not capability limits. Either agent may lead a technical
task. A task record must say who owns that particular outcome.

If the user starts both agents in one worktree, only one may write or run Git.
The other must remain read-only until it is moved to an isolated worktree.

## 2. Units of work

Split work by independently verifiable outcome, not by vague activity.
Examples include:

- build and locally validate one `memory_02` prototype;
- audit a Sudoku two-row placement without changing the accepted generator;
- reproduce and benchmark one recovered submission;
- query and reconcile the live state of one exact problem;
- review one handoff commit against a named acceptance checklist.

Each task has one owner and records:

- task ID and problem;
- owner, reviewer, and integrator;
- base `main` commit and agent branch;
- exclusive write paths;
- shared paths that are read-only for the owner;
- paths that must not be touched;
- concrete deliverables and acceptance checks;
- permitted contest-side mutations;
- expected handoff form.

Use `coordination/templates/task.md`. Task IDs use
`YYYYMMDD-<problem-or-area>-<short-outcome>`.

Do not start implementation until ownership and the write set are explicit.
If two proposed tasks need the same file, either split the file ownership,
serialize the tasks, or give both changes to one owner.

## 3. Path ownership

During an active task, only its owner edits its exclusive write set.

The integrator owns these shared hotspots unless a task explicitly transfers
one of them:

- `AGENTS.md`;
- `docs/current-state.md`;
- shared policy and protocol files;
- package and lock files;
- generic simulator, parser, canvas, and API infrastructure;
- shared catalog entries for a problem under concurrent work;
- final live-result metadata;
- the `main` branch.

Agent-private bookkeeping remains private:

- Codex edits `codex/`;
- Claude edits `claude/`;
- neither agent rewrites the other's area.

Saved solution versions and live submission responses are immutable. Create a
new numbered version rather than overwriting an earlier artifact.

### Merge name collisions

Before integration, hash any same-path artifacts added independently on both
branches. Different bytes under one filename are two immutable versions, not
a file-level conflict to resolve by choosing one.

- Keep the target branch's existing filename unchanged.
- Rename the incoming Tarstars/Codex artifact with a `tarstars_` prefix:
  `<name>` becomes `tarstars_<name>`.
- Prefix companion catalogs or submission responses too when their paths
  conflict, and update source, tests, reports, and current metadata.
- Never rewrite a pushed immutable message merely to change its old path.
  Publish a correction message that names both the old and new paths.
- Verify that the rename preserves the artifact hash, then rerun its focused
  reproduction test before merging.

## 4. Synchronization artifacts

The repository contains four kinds of coordination artifact.

### Task records

`coordination/tasks/<task-id>.md` defines the work package. Its declared record
owner is the only agent who edits it. Other agents communicate changes through
messages.

Normally the integrator creates and owns task records on `main`; the work owner
acknowledges the assignment from its agent branch. This keeps assignment state
discoverable without making the task file jointly writable.

### Agent status

`coordination/status/<agent-id>.md` is a replaceable snapshot owned only by
that agent. It states the current task, phase, branch, head commit, write set,
last verified result, next checkpoint, and blockers.

Update status:

- when accepting or releasing a task;
- before a long-running job;
- after the first reproducible result;
- when the write set or plan changes;
- when blocked;
- when a handoff is ready;
- after integration.

Status is a convenience snapshot. Messages and Git commits are the durable
history.

### Immutable messages

Each sender owns `coordination/messages/<sender>/`. Message names use:

```text
YYYYMMDDTHHMMSSZ-<task-id>-<kind>.md
```

Kinds are `claim`, `progress`, `question`, `blocker`, `policy`, `stop`,
`takeover`, `handoff`, `ack`, `release`, and `integrated`.

Messages are immutable after they are pushed. A correction is a new message
that names the superseded file. Assignment, question, blocker, policy, stop,
takeover, and handoff messages require an `ack` from the recipient. Progress
messages do not.

The integrator publishes assignments and integration messages on `main`.
Workers publish status and messages on their agent branches. After
`git fetch origin`, inspect the peer's remote ref; a message absent from the
current checkout may still exist on the peer branch.

### Handoffs

A handoff is a message using `coordination/templates/handoff.md`. It contains
the exact commit, diff scope, commands run, measured facts, unverified
assumptions, known failures, integration order, and whether any external
mutation occurred.

A statement such as “done” without an inspectable commit and validation
evidence is not a handoff.

## 5. Notification cadence

Agents notify at meaningful state changes, not on a timer:

1. **Claim** — before implementation.
2. **Progress** — at the first reproducible result or a material design
   decision.
3. **Blocker/question** — immediately when work would otherwise diverge or
   stall.
4. **Handoff** — after focused validation and a pushed commit.
5. **Acknowledgement** — before the receiver begins review or integration.
6. **Integrated/release** — after the commit reaches `main`, or when a claim
   is abandoned.

An agent may stop voluntarily at any point. Before stopping, it should preserve
safe work in progress, publish a blocker or release message, and release its
write set. It must not resume a released task unless it is assigned again.

An active Claude task has a 15-minute progress lease. Concrete progress is new
inspectable evidence: a commit or diff, a test or experiment result, a narrowed
failure, or a previously announced long-running command with traceable output.
Repeating an intention or updating a timestamp without new evidence does not
renew the lease.

If Claude produces no concrete progress for 15 minutes, Codex may instruct
Claude to stop and may reassign or take over the task without waiting for
additional user approval. Before writing:

1. Inspect Claude's status, messages, branch, and any announced running job.
2. Publish a `stop` or `takeover` message naming the last observed evidence.
3. Preserve Claude's branch and commits; never clean or rewrite its worktree.
4. Record the new owner and exclusive write set.
5. Continue from a separate branch or new solution version so late Claude work
   cannot silently overwrite the takeover.

After a stop or takeover message, Claude must cease task work promptly,
checkpoint safe partial work if possible, acknowledge, and release the write
set. It may still report useful findings, but must not resume implementation
without reassignment.

Direct user chat may duplicate an urgent notification, but the repository
message is authoritative.

## 6. Git synchronization

At the start of a task:

1. Confirm the agent is in its own worktree and branch.
2. Require a clean worktree; do not autostash unrelated changes.
3. Run `git fetch origin`.
4. Rebase the agent branch onto `origin/main`.
5. Read active task records, both agent status files, and new peer messages.
6. Publish the claim/status checkpoint before editing implementation files.

During work:

- keep commits scoped to one task;
- never stage another agent's files;
- push reproducible checkpoints to `origin/agent/<id>`;
- fetch before expanding the write set or touching a shared path;
- do not force-push a branch after its commit has been handed off.

At handoff:

1. Rebase onto current `origin/main` unless doing so would rewrite an already
   published handoff; in that case create a new reconciliation commit.
2. Run the task's focused acceptance checks.
3. Commit and push the exact handoff state.
4. Publish a handoff message naming the full commit hash.

At integration:

1. The integrator fetches both `origin/main` and the worker branch.
2. The integrator acknowledges the handoff.
3. Inspect the diff and rerun risk-proportionate checks.
4. Reconcile any newer `main` work; never discard a newer solution or metric.
5. Apply the solution freshness gate below.
6. Integrate, push `main`, and publish an `integrated` message with the final
   commit.

If a push is rejected, fetch and inspect before retrying. Never resolve a
coordination race by force-pushing.

## 7. Contest API and submission serialization

Read-only API work may be delegated. Contest mutations are serialized through
the submission controller.

No agent may submit merely because a candidate is ready. Submission requires:

- explicit user authorization for that candidate;
- the exact graded problem ID;
- the exact locally validated file and SHA-256;
- server-compatibility validation where applicable;
- a fresh check that at most one agent is acting as submission controller;
- preservation of the returned submission ID and terminal response.

Never automatically retry an ambiguous submission POST. Notify the other
agent as soon as a submission starts and again when it terminates.

Before any commit containing a new or changed solution version, the committing
agent follows the repository freshness policy:

1. fetch and integrate current `origin/main`;
2. query the exact problem's live score and latest known submission state;
3. reconcile the live result and pulled catalog with the candidate;
4. record only traceable facts.

The integrator repeats this gate before the solution reaches `main`, even when
the worker performed it before the handoff commit.

Credentials remain in the designated ignored `.env`. Agents may reference
that file through the API tool's `--env-file` option from another worktree,
but must never copy, print, commit, or include its contents in a message.

## 8. Conflict and failure rules

- **Overlapping claims:** the integrator chooses one owner; the other agent
  releases the claim and preserves useful independent notes in a separate
  report or message.
- **Unexpected peer edits in the write set:** stop editing those paths,
  publish a blocker, and let the integrator reconcile ownership.
- **Dirty shared worktree:** do not pull, rebase, stage, or commit. Identify
  the owner and move one agent to a separate worktree.
- **Stale Claude progress:** after 15 minutes without concrete evidence, Codex
  may issue a stop/takeover and reassign the task under the liveness procedure
  above. A stale timestamp alone is not proof of abandonment before that
  threshold.
- **Failed experiment:** preserve concise evidence and release the task; do
  not hide negative results or promote projections as measurements.
- **API ambiguity:** stop all new submissions for that problem until the
  submission controller reconciles server state.
- **Secret exposure:** stop, notify the user, and avoid copying the exposed
  value into any further artifact or log.

## 9. Definition of done

A task is complete only when:

- deliverables exist at the recorded paths;
- acceptance checks and exact commands are recorded;
- measurements distinguish local, projected, and live results;
- relevant source/artifact hashes are preserved;
- the handoff commit is pushed and acknowledged;
- integration is either completed or explicitly deferred;
- claims and status are released;
- any contest mutation has a recorded terminal result.

The user remains the authority for priorities, role changes, and submission
authorization.
