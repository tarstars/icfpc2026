# 20260726-gpt-reverse-y-schedule: linear-time reverse via split workers

- Status: active
- Record owner: gpt
- Work owner: gpt
- Reviewer: alexey
- Integrator: codex
- Problem: `reverse-a-list`
- Base main commit: `237997931538b440ae1a67fd2e12ffc102b599a9`
- Branch: `agent/gpt-reverse-y`
- Progress lease: 15 minutes without concrete evidence
- Created UTC: `2026-07-26T20:51:00Z`

## Outcome

Prototype and measure a `Y`-spawned fixed farm of 16 readers whose path lengths convert sequential input reception into reverse-order output without a LIFO store.

## Core schedule

Let worker `i` be the `i`-th worker in creation order, `0 <= i < 16`. The input pipe supplies list values one per tick, so worker `i` receives at time `t+i`.

Place its send cell `d_i = 31 - 2*i` ticks after its receive. Then:

```text
send_i = t + i + d_i = t + 31 - i
```

Therefore among the first `n` workers, worker `n-1` sends first and worker `0` sends last, exactly reversing the list. The schedule is independent of `n`; workers `n..15` remain blocked.

For a reusable farm, make the post-send return length `2+i`, so the total receive-to-read-cycle length is `33-i` and every worker returns to a read cell at the common time `t+33`.

## Exclusive write set

- `coordination/tasks/20260726-gpt-reverse-y-schedule.md`
- `coordination/status/gpt.md`
- `coordination/messages/gpt/`
- `experiments/gpt-reverse-y/`
- `reports/2026-07-26-gpt-reverse-y.md`

## Shared read-only paths

- `submissions/reverse-a-list/`
- `src/littleman/split_probe.py`
- `claude/official-sim/`
- Alexey reverse sources, reports, tasks, status and messages

## Do not touch

- `main`
- existing numbered `.man` artifacts or response JSON
- Alexey's reverse implementation paths
- other agents' status or message namespaces
- shared simulator, package and API files

## Acceptance checks

- Organizer WASM engine accepts the `Y` program and exact public outputs.
- All eight public cases and deterministic lengths 1..16 pass.
- Repeated 1–3-round cases prove the worker farm resets or safely respawns.
- No wall birth, unintended collision, shared wall, one-cell pipe or output-order race.
- Record dimensions, footprint, ticks, runner-count timeline and exact artifact hash.
- Retain a whole-machine candidate only if it improves the live 84,922.5 score locally with material margin.

## Contest authority

Contest submission is forbidden. Alexey owns Reverse submissions; Codex remains submission controller.

## Handoff

Publish the exact construction, organizer-WASM results and artifact under the GPT experiment namespace. Alexey may adopt or rebuild it under a separate solution task.