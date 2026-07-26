# finding: `Y` removes the LIFO requirement for Reverse

- From: gpt
- To: alexey
- CC: codex, claude
- Created UTC: `2026-07-26T20:51:00Z`
- Task: `20260726-gpt-reverse-y-schedule`
- Branch: `agent/gpt-reverse-y`
- Requires acknowledgement: no; idea requested by Alexey's breakthrough call

## Construction

A fixed farm of 16 little men can receive the values directly from the single input FIFO in creation order. No worker stores more than its own `A`, and no LIFO exists.

If worker `i` receives at tick `t+i`, put its `s` cell `31-2*i` ticks after its `r` cell. Its send tick is

```text
t + i + (31 - 2*i) = t + 31 - i.
```

Thus, for any `n`, the first `n` workers send in order `n-1, n-2, ..., 0`. Workers `n..15` stay blocked and do not interfere. This is linear-time reversal by spatial scheduling rather than storage.

For reuse across rounds, put `2+i` ticks after `s` before the worker reaches a read position again. Total cycle from receive to read is `33-i`, hence all workers return together at `t+33`:

```text
receive_i = t+i
send_i    = t+31-i
return_i  = t+33
```

A controller must consume the length token before all workers and stay away from the input pipe until the values are consumed. Creation order makes that deterministic.

## Why this matches the leaderboard

A 20x20–24x24 machine completing a round in roughly 35–45 ticks scores around 14k–26k. The current leader's 15.3k no longer implies a hidden LIFO: a split-worker delay network explains linear time at the observed footprint.

## Work now underway

I am prototyping the farm against the vendored organizer WASM engine, including repeated rounds and cleanup/reset. I will not touch Alexey's Reverse paths or submit. Exact task record: `coordination/tasks/20260726-gpt-reverse-y-schedule.md`.