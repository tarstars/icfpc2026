# Four-Hour Goal: Claude Packed Memory Candidate

## Activation

Pursue this goal autonomously for four hours beginning when the user activates
this file. Work only from `/home/tarstars/prj/icfpc2026-claude` on branch
`agent/claude`.

Do not stop merely because the first design fails. Continue through bounded
alternatives while useful work remains, subject to the 15-minute
concrete-progress policy.

## Mission

Build, measure, and hand off a competitive packed `memory_02` candidate based
on `reports/2026-07-25-memory-packing-feasibility.md`.

The result must be a real Little Man machine with measured behavior, not only
an analytical packing model.

## Role and authority

Claude is the solution owner for the packed Memory task.

Claude may:

- edit Memory-specific source, tests, new artifacts, and reports within the
  declared task write set;
- edit `claude/`, `coordination/status/claude.md`, and
  `coordination/messages/claude/`;
- run local tests and read-only contest API queries;
- commit and push reproducible checkpoints to `origin/agent/claude`.

Claude may not:

- edit `main`, `codex/`, Codex's Sudoku paths, or Codex's status/messages;
- edit shared policy, package/lock, generic simulator, or API files unless
  Codex explicitly transfers the path;
- overwrite `memory_01` or any preserved submission response;
- create a contest submission;
- promote an estimated score as measured.

## Startup

1. Fetch `origin` and rebase `agent/claude` onto current `origin/main`.
2. Read the required project state, protocol, this goal, and the Codex
   liveness-policy message.
3. Acknowledge the liveness policy from Claude's message namespace.
4. Publish or acknowledge the Memory task record with an explicit exclusive
   write set.
5. Record the starting commit and current live Memory score/submission state.

## Primary task: packed `memory_02`

Preserve `memory_01` unchanged. Prefer a new generator/module, new focused
tests, a new numbered `.man` artifact, and a focused report.

Investigate the proven base-`2**21` packing design and bounded alternatives as
needed. Measure encoding/decoding overhead and geometry together. Do not retain
a design whose wider stations or additional ticks erase the packing benefit.

A retained candidate must:

1. Correctly encode and decode all permitted values without violating signed
   64-bit wrapping semantics.
2. Cover directed boundary values and deterministic randomized packing tests.
3. Reproduce its exact `.man` artifact byte-for-byte from the generator.
4. Parse and pass `littleman.server_compat`.
5. Pass all public Memory cases.
6. Pass deterministic randomized operation sequences and worst-shape capacity
   cases against a Python oracle.
7. Record SHA-256, byte size, dimensions, footprint, pipe capacities,
   per-case ticks, average ticks, local score, and comparison with
   `memory_01`.
8. Demonstrate a measured score improvement over `memory_01`.

Do not submit the candidate.

## Bounded fallback ladder

If the three-value packing design fails or is slower:

1. Localize whether the blocker is arithmetic correctness, station width,
   pipe capacity, synchronization, or decode ticks.
2. Try bounded geometry changes that preserve the protocol.
3. Compare a two-value packing variant if it offers a better total
   footprint-tick tradeoff.
4. Preserve a concise negative report if no packed variant beats
   `memory_01`.
5. Use remaining time for independent adversarial testing and a clear next
   design recommendation; do not switch into Codex's Sudoku task.

## Progress and synchronization

An active task has a 15-minute concrete-progress lease. Renew it with
inspectable evidence such as a diff/commit, test result, benchmark, narrowed
failure, or an announced long-running command with traceable output. A
timestamp-only update does not count.

Publish status and immutable messages at claim, first reproducible behavior,
material design decisions, blockers, pushed checkpoints, and handoff.

Claude may stop voluntarily. Before stopping, preserve safe partial work,
publish a blocker or release message, and release the write set.

If Codex issues a `stop` or `takeover` message:

1. Cease the affected implementation promptly.
2. Preserve and push safe partial work when possible.
3. Acknowledge the message and release the write set.
4. Do not resume unless reassigned.

Before every commit containing a new solution version, rebase or reconcile
with current `origin/main`, query the exact Memory live score and latest known
submission state, and preserve traceable freshness evidence.

## Handoff

A valid handoff must identify:

- the full payload commit and branch;
- exact diff scope;
- generator and artifact paths;
- exact validation commands and observed results;
- hashes, dimensions, ticks, capacities, and score comparison;
- failed alternatives and remaining assumptions;
- integration order and any expected conflicts;
- confirmation that no contest mutation occurred.

Push the handoff to `origin/agent/claude` and notify Codex through Claude's
message namespace.

## End condition

Work until four hours have elapsed from activation, Codex takes over, or every
bounded path above is exhausted.

Before ending:

1. Finish or safely terminate running commands.
2. Push every recoverable checkpoint.
3. Leave the branch and worktree in a documented state.
4. Report commits, measurements, retained/rejected candidates, failures,
   blockers, and exact integration instructions.

No contest submission is authorized by this goal.
