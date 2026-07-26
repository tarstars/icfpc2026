# 20260726-gpt-tcp-relay-component: compact TCP relay experiment

- Status: paused by direct user reprioritization; write set released
- Record owner: gpt
- Work owner: none while paused
- Reviewer: codex
- Integrator: codex
- Problem: `tcp`
- Base main commit: `36f4778deef6635314705b3d018568ee4969c24d`
- Branch: `agent/gpt`
- Progress lease: inactive while paused
- Created UTC: `2026-07-26T17:37:48Z`
- Last updated UTC: `2026-07-26T17:41:57Z`

## Outcome

Determine whether the `U`-based send/read relay idiom can materially improve
current bit-packed TCP (`tcp_08`) without changing its three-word window
protocol. Retain an exact component or whole-machine experiment only when its
trace and score measurements beat the current relay.

## Pause disposition

The user explicitly reprioritized GPT to preserve two already validated `.man`
candidates in Git. No TCP implementation artifact had been created. The claim
and inspected source remain useful context, but all TCP write paths are
released until a new user or integrator assignment resumes the task.

## Former exclusive write set — released

- `coordination/tasks/20260726-gpt-tcp-relay-component.md`
- `experiments/gpt-tcp-relay/`
- `reports/2026-07-26-gpt-tcp-relay-component.md`

GPT continues to own only its status and message namespace generally.

## Shared read-only paths

- `src/littleman/tcp_fast.py`
- `tests/test_tcp_fast.py`
- `submissions/tcp/`
- `docs/alexey-tcp-handoff.md`
- `coordination/messages/alexey/20260726T152000Z-20260726-subset-sum-ack-and-tcp-loop.md`

## Do not touch

- `main`
- existing numbered `.man` artifacts, response JSON, or variant catalogues
- `codex/`, `claude/`, `coordination/status/{codex,claude,alexey}.md`
- other agents' message namespaces
- generic simulator, parser, canvas, package, or API infrastructure

## Work completed before pause

- Inspected `tcp_fast.build_r()`: the current three-word ring relay is already a
  six-cell cycle and the controller uses unrolled insert/relay blocks.
- Inspected Alexey's `> s U d m ^` idiom and recorded that its main advantage is
  combining an already-loaded head send with the next receive; applicability to
  the bit-packed controller remains unmeasured.
- Published the claim before editing, as required by the coordination protocol.

## Contest authority

No contest mutation occurred. No numbered solution artifact was created.

## Resume condition

Create a new task assignment or explicitly reactivate this record with a fresh
write set after the candidate-preservation task is handed off.
