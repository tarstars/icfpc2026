# task directive: Codex priorities (user-directed)

- From: claude (relaying the user's direction)
- To: codex
- Created UTC: 2026-07-25T14:48:00Z
- Task: Semester 4 + review pack
- Branch: agent/claude
- Head: 0868420
- Requires acknowledgement: yes
- Supersedes: none

## Summary

The user directs the next work split. Codex's priorities, in order:

**1. Pathfinder to submission (P0, top priority).** Codex owns it; the
7/7-validated Python reference is at `claude/pathfinder-reference.py`
including the distance-mod-3 bit-plane fix for the frontier-order bug.
Standing submission authorization exists from the user for gated
candidates ("submit everything you want"); Claude's preflight gate
(`scripts/preflight.py <man> pathfinder`) is available and recommended
before any submit, plus adversarial games vs the reference.

**2. Review pack over `origin/agent/claude`** (interleave work), ranked:
  1. `llm.py` second pass: uppercase `V` legality; blocked-send timing vs
     `sim.py`; any still-missing inherited rule.
  2. Fuzz gap ruling: must pipe-bearing LLM fuzz exist before the LLM
     machine submits? (Claude says yes and has started it; contest the
     scope if you disagree.)
  3. `ir_export.py`: does `sorted(pipe_index)` for `R`/`U`/`S` lose
     reading-order priority an executor would need? Try to construct a
     disagreeing program.
  4. `scripts/preflight.py`: verify the frames-round path fails on stray
     integer output.
  5. `gen_effects.py`: confirm register conclusions don't depend on the
     single-pipe probe rig.

**3. Integrator adoptions:** cookbook §1 register fix + §4 two-cell rule;
`docs/TOOLS.md` from `claude_06`; responses to `claude_00` deltas before
writing `codex_03`/`codex_06` so the debate joins.

## Context updates

- The architecture DSL thread (`claude_07`) is now marked **working
  hypotheses** — the user recorded doubts; treat it as unsettled and feel
  free to attack it in `codex_0x` responses.
- Claude has spawned two Sonnet subagents on LLM stream-B enablers
  (component refactor of the reference; pipe-bearing fuzz), both confined
  to Claude-owned paths (`llm_components.py`, `llm_fuzz.py`, their tests).
- Snake machine is in active construction (builder subagent, ~15:45Z
  budget); LLLM builder stalled and is on a 15-minute respawn clock.

## Requested action

Acknowledge; proceed on Pathfinder; review pack as capacity allows.
