# Claude: the contest-first plan (awaiting user validation)

Status: Proposed 2026-07-25T13:50Z under the user's decision
**contest-first — the platform must pay by Sunday 12:00Z**. Supersedes the
tier table in `claude_00` with concrete timeboxes. ~46h remain; final
freeze Sun 10:00Z, submissions close 12:00Z.

## The one structural change from the review

Instead of *full-Rust toolchain + factory-centric platform*:
**verification-first, composer-centric, check-don't-simulate, Rust only on
measured need.** Rationale: geometry-only moves on `patient` machines
cannot change results — only route lengths change ticks — so candidate
layouts are validated by *checks* (DRC, capacity, resolution map) and
priced by *arithmetic* (traversal-weighted route lengths), with the exact
judge run only on the surviving Pareto set. That removes the
millions-of-simulations premise that motivated Rust; the executor gets
built only if profiling a real annealing loop shows evaluation is still
the bottleneck (timeboxed to 4h if triggered).

## Phase P0 — Semester 4 to submission (now -> Sat morning; the score is
pass+rank points from zero on four problems)

| Item | Owner | State | Gate before submission |
|---|---|---|---|
| LLLM machine | Claude subagent (resumed) | reference 10/10; machine in build | preflight + adversarial fuzz vs reference oracle |
| Snake machine | Claude subagent | reference status due; **takeover at 14:15Z if no checkpoint** | same |
| LLM machine | Claude, extending the LLLM template | reference 14/14 done; machine unstarted | same |
| Pathfinder | Codex | released with reference + mod-3 handoff | Codex's gates |

Support work (Claude, now): adversarial case generators for LLLM/LLM and
Snake — random well-formed programs/games, my references as oracles, the
same method that de-risked memory (430 cases, 0 failures). All-or-nothing
pass scoring makes this the highest-value hour in P0.

Submission authority: the user's standing goal "submit solutions for new
problems" is treated as authorization for Semester 4 candidates that pass
every gate. Anything failing a gate is not submitted, full stop.

## Phase P1 — Composer v0 (Sat; parity gate before any real target)

1. IR->text renderer (the one missing piece; `ir_export.py` + 94 tests
   already landed).
2. Floorplan/route annealer in Python, moves = {translate room, reroute
   net, swap}, feasibility = the engine-true resolution map + DRC +
   capacity, cost = lexicographic (max(W,H), traversal-weighted route
   length).
3. **Parity gate:** re-lay `memory_04` at <= 37x37 with all checks green.
   Any invalid emission = a missing check, fixed before targets.
4. Targets in slack order (big unbalanced boxes, squared payoff):
   gradebook 386x423, plotter 113x326, sudoku 184x248 (Codex's sudoku_02
   is 184x248 live), matmul 183x180, then tcp/sort/brackets only if the
   predictor shows slack. Exact judge on finalists; preflight; submit
   improvements (only-best-counts makes this risk-free score-wise).

## Standing rules through both phases

- Preflight (`scripts/preflight.py`) is mandatory before any submission.
- Freshness check (live score + submission state) before each submit.
- 15-minute pushed-progress cadence; catalogs/variants stay Codex-owned.
- Projections quoted as +/-15%; only submissions measure.

## Explicit drop list (not before Sunday noon)

LM-Spec syntax; free-form room superoptimization; GPU anything; Rust
parser; soft-core; full contract schema (only what the composer consumes).
Stretch backlog if P0+P1 land early, in order: history dictionary machine
(projected 81x81 = 6,561 vs live 7,921, encoding verified byte-exact,
~3-6h hand build); reverse ring-capacity rebalance; tcp_02 slice.

## YT under contest-first

Optional, not on the critical path: the composer's annealing fits
overnight on the local box (1e3-1e5 evals/problem at ~0.1-0.5s each).
YT becomes worth wiring only for massive-restart placement search or the
fuzz farm — user's call, zero contest dependency.

## Timeline (UTC)

| When | Must be true |
|---|---|
| Fri 14:30 | fuzz generators exist; LLLM machine validated or blocker named; Snake checkpoint or takeover |
| Fri 18:00 | LLLM + Snake submitted (or their smallest blockers published) |
| Sat 09:00 | LLM machine judged locally; submitted |
| Sat 12:00 | composer parity gate green |
| Sat 18:00 | composer improvements on >= 2 live problems submitted |
| Sun 09:00 | last planned submissions; no new risk after 11:30 |

## What the user is asked to validate

1. The re-weighting above (composer over factory, Rust conditional).
2. P0 submission authority as stated (gated Semester 4 candidates).
3. **P1 submission authority:** standing authorization for existing-problem
   improvements that pass preflight + exact judge, or per-candidate asks?
4. YT: wire now or leave optional.
