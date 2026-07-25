# Four-Hour Goal: Codex Integration and Sudoku Improvement

## Activation

Create and pursue this as an active goal for four hours beginning when the
user activates this file. Do not mark the goal complete merely because the
first candidate or handoff is finished; continue through the priority ladder
while safe, useful work remains.

## Mission

Produce and integrate as many evidence-backed ICFPC 2026 score improvements as
safely possible. The primary technical target is a real two-row Sudoku
candidate. In parallel, act as the integration and API counterpart for
Claude's packed Memory work.

## Role and authority

Codex is the integrator and submission controller.

Codex may:

- create task records and synchronization messages;
- edit the Codex-owned and task-owned paths defined below;
- run local tests, benchmarks, and read-only contest API queries;
- review commits from `origin/agent/claude`;
- commit validated work and push `main`;
- reclaim Claude's task under the 15-minute concrete-progress policy.

Codex may not:

- create a contest submission without separate explicit user authorization
  for the exact candidate;
- edit `claude/` or Claude's active exclusive write paths;
- overwrite preserved solution versions or live-result JSON;
- discard unrelated worktree changes;
- report projections as measurements.

## Startup

1. Read the required project state and the two-agent protocol.
2. Fetch `origin` and confirm `main` is current.
3. Inspect Claude's status, messages, branch, and active write set.
4. Publish task records for the Sudoku and Memory work split if they do not
   already exist.
5. Claim only the Sudoku and integration paths.

## Primary technical task: Sudoku two-row candidate

Turn the measured two-row packing bound into an actual, fully validated
candidate while preserving `sudoku_00`.

Codex owns:

- Sudoku-specific implementation and generator files;
- Sudoku-specific tests;
- a new numbered artifact under `submissions/sudoku-validity/`;
- a focused Sudoku optimization report;
- final Sudoku catalog and shared-state updates during integration.

A retained candidate must:

1. Reproduce byte-for-byte from its generator.
2. Parse and pass `littleman.server_compat`.
3. Pass every public Sudoku case.
4. Pass deterministic valid-grid, valid-prefix, and directed row, column, and
   box duplicate tests.
5. Record exact SHA-256, byte size, width, height, footprint, per-case ticks,
   average ticks, local score, parent version, and comparison.
6. Improve measured local score over `sudoku_00`.
7. Preserve failed layouts and negative conclusions concisely when they teach
   a reusable constraint.

Do not submit the candidate.

## Claude integration duty

Claude's primary task is packed `memory_02`.

At each meaningful checkpoint, and whenever 15 minutes pass without concrete
Claude progress:

1. Fetch `origin/agent/claude`.
2. Inspect Claude's status, new messages, commits, and announced running work.
3. Answer actionable questions through Codex's message namespace.
4. Apply the liveness policy when appropriate.
5. Review any handoff for scope, exact reproduction, correctness, signed-64
   safety, server compatibility, measurements, and comparison with
   `memory_01`.
6. Integrate only evidence-backed work. Before a solution reaches `main`,
   repeat the Git/API freshness gate required by `AGENTS.md`.

## Priority ladder after Sudoku

If Sudoku succeeds, is rigorously rejected, or is blocked by a recorded
constraint, continue in this order:

1. Review and integrate a valid Claude `memory_02` handoff.
2. Refresh live API state and prepare submission-ready dossiers for
   `sort_05`, `reverse_02`, and `plotter_01`; do not submit them.
3. Attempt a bounded repair of the known Subset Sum relocation pipe collision.
4. If the collision is not repaired promptly, document the smallest
   reproducible blocker and propose the next route change.

Do not begin a lower-priority item while a higher-priority item has an
immediately actionable validation or integration step.

## Evidence and synchronization

- Keep local, projected, and live measurements explicitly separate.
- Record exact commands and compact outcomes.
- Preserve hashes for every candidate artifact.
- Publish progress, blocker, takeover, handoff, and integration messages under
  `coordination/messages/codex/`.
- Do not edit Claude's status or message namespace.
- Before every new solution commit, fetch/integrate `origin/main` and query
  the exact problem's current score and latest known submission state.

## End condition

Work until four hours have elapsed from activation or every priority above is
either completed or blocked by a concrete recorded condition.

Before ending:

1. Finish or safely terminate running commands.
2. Push every safe completed commit to `main`.
3. Leave incomplete experiments recoverable and clearly marked.
4. Publish a final report containing:
   - main and handoff commit hashes;
   - candidates retained or rejected;
   - exact local and live measurements;
   - tests and API checks performed;
   - failures and blockers;
   - unsubmitted submission-ready candidates;
   - the next three recommended actions.

No contest submission is authorized by this goal.
