# 20260726-gpt-tcp-relay-component: compact TCP relay experiment

- Status: active
- Record owner: gpt
- Work owner: gpt
- Reviewer: codex
- Integrator: codex
- Problem: `tcp`
- Base main commit: `36f4778deef6635314705b3d018568ee4969c24d`
- Branch: `agent/gpt`
- Progress lease: 15 minutes without concrete evidence
- Created UTC: `2026-07-26T17:37:48Z`
- Last updated UTC: `2026-07-26T17:37:48Z`

## Outcome

Determine whether the `U`-based send/read relay idiom can materially improve
current bit-packed TCP (`tcp_08`) without changing its three-word window
protocol. Retain an exact component or whole-machine experiment only when its
trace and score measurements beat the current relay.

## Exclusive write set

- `coordination/tasks/20260726-gpt-tcp-relay-component.md`
- `coordination/status/gpt.md`
- `coordination/messages/gpt/`
- `experiments/gpt-tcp-relay/`
- `reports/2026-07-26-gpt-tcp-relay-component.md`

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

## Deliverables

- Exact baseline trace and cycle cost for `tcp_fast.build_r()`.
- Exhaustive bounded search or constructive alternatives using `U` where
  applicable.
- Component harness proving FIFO order, blocking behavior, and steady-state
  throughput.
- If a component wins, a generated whole-machine experiment under
  `experiments/gpt-tcp-relay/`, with public and deterministic boundary results.
- Focused report and immutable handoff or negative-result message.

## Acceptance checks

- Baseline and candidate emit exactly the input sequence for empty, singleton,
  burst, and backpressured streams.
- Every pipe has at least two cells and required capacity is preserved.
- All `r`/`s`/`U` bindings are explicit and unchanged where the surrounding
  machine is retained.
- A whole-machine candidate must pass all public TCP cases and the repository's
  deterministic boundary suite before it is retained.
- Measurements distinguish component cycle time, footprint, local ticks, and
  projected/live facts.

## Contest authority

Read-only contest API access: not needed for the component experiment.

Contest submission: forbidden. This task does not create a numbered solution
artifact; any later solution task must perform the normal freshness gate.

## Handoff

Push exact experiment code, generated artifacts, measurements, and an immutable
message to Codex, Claude, and Alexey. Codex decides integration or assignment of
a separate solution-version task.
