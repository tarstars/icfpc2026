# OVERNIGHT HANDOFF — state, queue, and operating rules

Written 2026-07-25T19:2xZ for an autonomous session that runs until
**2026-07-26T06:00Z (09:00 Moscow)**, when the user rejoins — about TEN
HOURS. The contest itself ends 2026-07-27T12:00Z (freeze 10:00Z), so a
full working day remains after the handback. **Do no new design.**

Realistic scope for ten hours, given today's measured build times
(a component room took 1-3h with a subagent): items 1-2 are the MUST,
item 3 is likely, items 4-6 are stretch. Getting LLLM submitted is worth
more than partial progress on three other things — a problem at zero
scores nothing, and only the best submission counts.

## Live scores (only these count)

| problem | live | note |
|---|---|---|
| snake | 8,838,759,329 (17/17) | first attempt; geometry uncompacted |
| memory | 23,344,360 | Codex pressed my 27.75M packed rebuild |
| others | see `submissions/*/‌*-submit.json` | 12 older problems |
| **lllm / llm / pathfinder** | **ZERO — not submitted** | biggest available gains |

## Running when this was written

Two subagents: SCAN (`claude_17` order A) and CLASSIFY (order B). Both
write only their own files. Verify their output against their work
orders before using it.

## THE QUEUE — do these in order, top first

1. **Land SCAN + CLASSIFY.** When each agent reports: run its tests,
   confirm its acceptance list, commit. If an agent stalls, apply
   `claude_14` triage (`scripts/agent_watch.py`), respawn once, and if it
   fails twice move to queue item 2 with the monolithic LOADER instead
   (Codex's room works — it is merely 723x8134, which still SCORES;
   correctness beats footprint when the alternative is zero).
2. **LLLM assembly + submit** per `claude_18`. DoD: 10/10 public,
   preflight READY, >=50 fuzz cases clean, submitted, response preserved.
   This is the single highest-value item on the board.
3. **Snake geometry press.** Live at 107x223; the builder judged ~150x150
   plausible. Every 10% off the max dimension is ~19% off the score.
   Rooms are proven — move them, re-route, re-run gates. DoD: a smaller
   artifact passing 5/5 + preflight, submitted.
4. **LLM machine** via `src/littleman/llm_components.py` (263 tests, the
   seven-component contracts already validated). DRAW transfers nearly
   verbatim from LLLM; FETCH/STEP patterns transfer. DoD: 14/14 public,
   preflight, submit.
5. **Pathfinder.** Reference at `claude/pathfinder-reference.py` validates
   7/7; Codex's bitboard design plus the distance-mod-3 fix is in
   `coordination/messages/codex/20260725T123756Z-*`. DoD: 7/7, preflight,
   submit.
6. **Y fan-out redesign** — ONLY if items 1-5 are done and `Y` is in a
   simulator. `split_probe.YMachine` is a tested single-room reference;
   `sim.py` still lacks `Y` (Codex's decision was never made). Biggest
   theoretical lever: subset-sum is 3646x3029.

## Operating rules (non-negotiable)

- **Never submit without `scripts/preflight.py` READY** plus the
  problem's oracle/fuzz check. Submissions cannot lower a score, so a
  gated submission is always safe; an ungated one wastes the slot.
- **Never modify a shipped artifact or its generator.** New attempt =
  new `<slug>_NN.man`.
- Push a checkpoint at least every 15 minutes (`agent/claude`).
- Subagent supervision: `claude_14` + `scripts/agent_watch.py`. Two
  failures on one task -> change the task, not the prompt.
- Record every result in this file under RESULTS, with the command and
  the number. Claims without a command are not results.
- Codex owns `main`, `docs/`, catalogs, `sim.py`. Message it; do not edit
  its paths.

## Traps that have already cost time today

- A bare `Machine.run()` burns the whole tick cap on server-style
  machines — always judge through the round controller.
- `preflight` catches the two-cell pipe rule and shared walls; both have
  killed submissions before.
- Local:server tick ratios are NOT constant across machines (memory was
  off by 12.5%). Projections rank; only submissions measure.
- Subagent failures are usually the 64k output ceiling, not confusion.

## RESULTS (append below; newest last)
