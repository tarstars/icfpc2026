# Semester 4 attack plans (delegation wave of 2026-07-25T14:45Z)

Per the validated contest plan and the user's directive: ideas written as
plans, implementation delegated to subagents on simpler models where the
task is well-specified enough to survive one. Machine-building stays on
strong builders; pure-Python, spec-driven tasks go to Sonnet.

## Board

| Problem | Owner | State at 14:45Z | Next gate |
|---|---|---|---|
| LLLM | builder subagent (resumed) | STALLED 75 min, hard checkpoint sent, respawn at ~15:00Z if silent | preflight + fuzz, then submit |
| Snake | builder subagent | actively writing (28.6KB machine + tests at 14:43Z, 2h budget to ~15:45Z) | preflight + fuzz vs its 5/5 reference, then submit |
| LLM | Claude + two Sonnet agents (below) | reference 24/24; netlist hypothesis in claude_07 | contracts frozen -> component builds |
| Pathfinder | Codex | bitboard design + my 7/7 reference handed off | Codex's gates |

## Sonnet task A — LLM component refactor (stream A contracts, executable)

Goal: `src/littleman/llm_components.py`, the seven-component pipeline of
claude_07 (LOADER, GEOM, PIPETRACE, BIND, INIT_FRAME, EXEC, DELTA_DRAW)
communicating ONLY through explicit FIFO queues of integers, plus
`tests/test_llm_components.py`.

Acceptance:
- frame-for-frame equality with the untouched monolith (`llm.py`) on all
  14 LLM public cases, all 10 LLLM cases, and `corpus(20260725, 200)`;
- integers-only asserted on every queue (the .man-implementability
  constraint at boundaries);
- a trace-recording mode (per-queue token streams per case) — the future
  acceptance tests of the littleman components;
- monolith `llm.py` not modified at all.

Why Sonnet-safe: pure Python, exact oracle to diff against, no geometry.

## Sonnet task B — pipe-bearing LLM fuzz (closing the known gap)

Goal: extend `src/littleman/llm_fuzz.py` + `tests/test_llm_fuzz.py` with
`random_llm_program(rng)`: 2-3 rooms, 1-2 pipes, <= 20 pipe cells, legal
per `Machine.parse`, `s`/`r` only in rooms having a pipe in the required
direction, canvas <= 16x16. Cases at tick_cap=100 (LLM's bound), frames
from the validated `llm.py` oracle.

Coverage the generator must demonstrably hit (asserted in tests): values
in flight rendered as 14; blocked `r` and blocked `s` situations; a
wall-freeze with values still in the pipe; multi-man cases where one man
halts while others run.

Why Sonnet-safe: generation + validation loop against two existing exact
tools (parser, oracle); the hard part (semantics) is already pinned.

## Held by Claude (not delegated)

- Validation + submission of every machine (preflight, fuzz, freshness,
  submit, Codex notification) — the authority the user granted rides with
  the gates, and the gates stay in one pair of hands.
- GEOM/PIPETRACE restricted-subset models — start after task A freezes
  the contracts; these are the two novel components and the current
  hypothesis test.
- P1 composer (Saturday per plan).

## Respawn plan for LLLM (if the hard checkpoint fails)

Fresh builder (strong model), fresh prompt with: the working LLLM plan
compressed to steps (setup ring -> INIT frame -> judge case 1 -> stepper
-> patch-per-frame -> full judge), the perimeter-wall and draw-once
notes, preflight as the gate, plus the two process rules that killed the
predecessors: no huge outputs, file writes every 15 minutes.
