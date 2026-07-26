# Eight-hour autonomous goal — secure unsolved problems first

## Activation and end

Pursue this goal autonomously for eight hours from activation. Codex is the
integrator; Claude works concurrently in its isolated worktree. Do not wait
for user input when the repository, tests, or API can answer the question.

Stop after eight hours, when the queue is empty, or when every remaining item
has failed its defined gates twice. Start no new item during the final
30 minutes; use that time to finish tests, preserve artifacts, push, and
write the handoff.

## Mission

Maximize secured contest value. Turn the three released zero-score problems
into committed, pushed, validated, and submitted baselines before beginning
speculative redesigns:

1. `little-little-little-man` (LLLM);
2. `little-little-man` (LLM);
3. `pathfinder`.

`Y` Memory, generic synthesis work, and other architecture investigations are
backlog items. They may not displace an unfinished zero-score problem.

## Parallel ownership

### Claude

1. Preserve and finish the in-flight LLLM SCAN and CLASSIFY components.
2. Assemble LLLM per `docs/architecture/claude_18_lllm_assembly_workorder.md`.
3. Run every LLLM gate and submit a passing artifact.
4. Move immediately to the LLM machine and its existing component contracts.
5. Request Codex review at component and final-machine boundaries.

Claude owns its existing `claude_*`, LLLM/LLM builder, test, and artifact
paths until it explicitly transfers them.

### Codex

1. Resume Pathfinder from the bitboard design and distance-mod-3 correction.
2. Build, adversarially validate, preflight, and submit Pathfinder.
3. Review Claude's LLLM and LLM handoffs promptly, with commands and concrete
   findings rather than general approval.
4. Integrate reviewed commits into main and serialize contest submissions.
5. During genuinely blocking long runs, prepare freshness checks and
   submission dossiers for proven optimizations without delaying zero-score
   work.

Codex owns Pathfinder, main integration, shared catalogs, `sim.py`, its own
messages/status, and submission serialization.

## Mutual review and help

- Every handoff must name the pushed commit, owned paths, exact test commands,
  case counts, dimensions/ticks when applicable, and remaining risks.
- The other agent performs an adversarial review before final integration or
  submission. Review the oracle, pipe bindings, parser constraints, boundary
  cases, and claimed metrics.
- Review is read-only unless ownership is explicitly transferred. Never edit
  another agent's in-flight paths.
- If either agent has no new inspectable progress for 15 minutes, the other
  agent checks its branch/status and offers one bounded, non-overlapping
  subtask: reproduce a failure, add an adversarial test, inspect geometry,
  or review a component.
- After two failed attempts on the same blocker, record the evidence and
  change the approach. Transfer ownership explicitly if the peer is better
  positioned to continue.
- Fetch before every handoff and before every solution commit. Communicate
  through immutable owner-written messages under `coordination/messages/`.
- Push concrete progress at least every 15 minutes. Timestamp-only updates do
  not count as progress.

## Gates and submission authority

Standing authorization covers any submission that passes all gates:

1. canonical public/oracle tests pass with zero failures;
2. required fuzz or adversarial suite passes;
3. `scripts/preflight.py <artifact> <slug>` prints `READY TO SUBMIT`;
4. current GitHub state is fetched and integrated;
5. the exact problem's live API score/submission state is queried;
6. the exact artifact and hash are preserved before submission.

Submit only through `uv run icfpc-api ... submit ... --confirm --wait`.
Preserve the full JSON response and immediately notify the peer of the contest
mutation. Never submit an artifact that failed or skipped a gate.

## Queue definitions of done

### 1. LLLM

SCAN and CLASSIFY are committed; final assembly passes 10/10 public cases,
preflight, at least 50 fuzz cases, STEP/FETCH binding and port-margin audit,
and three official-engine comparisons. Passing artifact submitted and
response preserved.

### 2. LLM

Complete machine passes 14/14 public cases, its pipe-bearing fuzz suite,
binding audit, and preflight. Passing artifact submitted and response
preserved.

### 3. Pathfinder

Machine passes 7/7 public cases, adversarial games against
`claude/pathfinder-reference.py`, freshness checks, and preflight. Passing
artifact submitted and response preserved.

### 4. Optimizations, only after 1–3 have baselines

Work in measured return order:

1. Snake geometry press;
2. freshness and submission review of validated Sudoku, Plotter, Sort, and
   Reverse successors;
3. the next optimization with a measured score model and bounded build.

Do not reopen already rejected hypotheses. A new optimization attempt must
state its parent, expected lever, time budget, acceptance gates, and stop
condition before implementation.

## Eight-hour pacing

- First 30 minutes: fetch, inventory all uncommitted work, preserve it, assign
  exclusive paths, and exchange status.
- Hours 0.5–3: LLLM completion and Pathfinder construction in parallel.
- Hours 3–5.5: LLM construction and Pathfinder validation/submission.
- Hours 5.5–7.5: finish any remaining zero-score target, then execute the
  highest-confidence optimization.
- Final 30 minutes: tests, freshness checks, commits, pushes, status, and
  concise mutual handoff.

## Required final handoff

Report:

- commits pushed and branches;
- submissions with IDs, scores, and pass counts;
- exact validation commands and results;
- uncommitted files, if any, with ownership;
- failed attempts and measured reasons;
- current API state for all three targets;
- the smallest next action for each unfinished item.

Success is accepted baselines and preserved evidence, not the amount of code
written. No valuable work may remain only in an uncommitted worktree.
