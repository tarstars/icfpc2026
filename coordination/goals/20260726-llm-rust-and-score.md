# Goal: finish LLM, accelerate execution, improve live scores

## Timebox

Run autonomously until `2026-07-27T09:00Z`, unless the user stops or replaces
this goal. Reserve the final 30 minutes for validation, preservation, pushes,
API reads, and handoff. Start no new implementation item in that window.

## Mission

Maximize secured contest value through three coordinated streams:

1. finish and submit a correct `little-little-man` (LLM) machine;
2. build an exact high-performance Rust executor and parallel test engine;
3. improve the accepted server scores of already-solved problems.

LLM remains the first contest priority because it is the only graded problem
without full case coverage. Tooling must accelerate LLM and later search, not
displace an unfinished LLM baseline.

## Current evidence

- LLM live state: 14/28 after submission
  `f077726c-a3b9-4ad3-b106-83091add453d`; the accepted partial passes 6/14
  public and 8/14 private cases. Remaining failures include step-cap and
  wrong-frame cases.
- LLLM: 21/21. Pathfinder: 18/18.
- The existing Python command `uv run pytest -q tests/test_llm*.py` covers
  46 modules and passed 1,622 tests in 621.31 seconds.
- Codex's complete raw-input physical LLM candidate, leaf services, state
  index, selector, pipe apply, wall scan, and frame pipeline are preserved on
  `agent/codex-llm`; the immediate task is to remove later-round frame
  repainting costs and resolve the remaining wrong-frame semantics.
- Claude has an independent incremental LLM stream on `agent/claude`.

## Parallel ownership

### Codex

1. Finish the full physical LLM action coordinator on `agent/codex-llm`.
2. Preserve exact whole-machine tests, binding audit, preflight, artifact,
   hash, and submission response.
3. After either LLM stream secures a baseline, own the Rust executor and
   parallel test-engine stream in a new isolated worktree.
4. Adversarially review Claude's LLM and score-improvement candidates.

### Claude

1. Continue the independent incremental LLM machine, landing and submitting
   gated partial improvements as individual immutable variants.
2. After LLM is secured, lead algorithmic score improvements, beginning with
   small, fast-to-iterate problems.
3. Adversarially review the Rust semantic contract, differential results,
   and Codex's final LLM machine.

The two LLM streams must not edit each other's paths. The first stream to
secure the required baseline becomes authoritative; the other transfers its
useful evidence and moves immediately to the next stream.

## Stream A: finish LLM

Required gates before a final LLM submission:

1. complete physical machine;
2. 14/14 public frame sequences;
3. pipe-bearing and multi-man fuzz coverage;
4. whole-machine port/binding audit;
5. `scripts/preflight.py <artifact> little-little-man` prints
   `READY TO SUBMIT`;
6. fetch current GitHub state and query exact live LLM state;
7. preserve immutable artifact and SHA-256;
8. submit through `icfpc-api --confirm --wait` and preserve stdout/stderr.

Submit a partial candidate only when it passes every public case it claims
and improves live pass count beyond 2/28 without regressing prior cases.

## Stream B: Rust executor and parallel tests

Architecture:

1. retain the Python parser/reference simulator as the semantic oracle;
2. define a versioned dense machine/state IR;
3. implement execution in Rust with exact signed-64 wrapping, pipe timing,
   blocking, movement, frames, collisions, and Split (`Y`) semantics;
4. expose a PyO3/maturin binding compatible with `uv`/pytest;
5. expose a standalone deterministic CLI for local batches and YT;
6. parallelize across independent programs, cases, fuzz seeds, and search
   shards; do not parallelize dependent ticks unless equivalence is proven;
7. add parse/IR caching and avoid repeated process startup in the test engine.

Acceptance:

- zero mismatches against Python for status, ticks, output, frames, men,
  registers, pipes, blocking, wrap64, collisions, and `Y`;
- the same 46-module, 1,622-test workload passes;
- wall time below 60 seconds, with 30 seconds as the stretch target;
- deterministic results at 1 worker and N workers;
- benchmark report records revisions, hardware, commands, and slowest tests.

Use local compute below roughly one hour. Evaluate YT first for independent
work expected to exceed one hour, after local parity and payload smoke tests.

## Stream C: improve accepted scores

Begin after LLM materially improves, or in genuinely non-blocking parallel
capacity. Prioritize measured return:

1. reverse-a-list, Packet Reassembly, Snake, and Sort;
2. proven unsubmitted successors after freshness and regression review;
3. algorithmic redesigns for large 1,000x-plus gaps;
4. no work on Triangle, already rank 1.

Every attempt must state its parent, lever, expected score effect, timebox,
gates, and stop condition before implementation. Success means a lower
accepted server score, not merely a smaller local artifact. Target at least
three accepted score improvements.

## Synchronization and safety

- Work in isolated branches/worktrees with explicit path ownership.
- Fetch before every handoff and solution commit.
- Push inspectable progress at least every 15 minutes.
- Exchange immutable messages under each agent's own coordination namespace.
- The peer independently reviews each final machine or submission candidate.
- Before every submission, run public/oracle tests, adversarial/fuzz tests,
  binding checks, preflight, API freshness, and exact artifact hashing.
- Standing authorization covers submissions that pass all mandatory gates.
- Preserve full API JSON and immediately notify the peer of contest mutation.
- Never commit credentials, tokens, raw bulk output, or generated caches.

## Definition of done

1. LLM has a preserved passing machine and terminal submission response.
2. Rust execution is exact and reduces the measured LLM test workload below
   60 seconds, including deterministic multicore execution.
3. At least three already-solved problems have lower accepted server scores.
4. All work is committed and pushed; no valuable result exists only locally.
5. Final handoff lists commits, branches, commands, timings, artifacts,
   hashes, submission IDs, scores, failures, and smallest remaining actions.
