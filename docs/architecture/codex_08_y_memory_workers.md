# Codex: Y-spawned Memory workers

Date: 2026-07-25  
Status: design hypothesis; no candidate has been built.

## Conclusion

Memory can in principle use `Y` to create one persistent worker per logical
cell. A balanced binary split tree with 99 `Y` cells has exactly 100 leaves,
well below the 65,536-man cap. Each leaf can park at a request loop and keep
its cell value in B, initially zero because all split copies inherit the
parent's registers.

This removes the packed ring's variable-distance search. It does **not**
remove the harder communication problem: a command must still reach exactly
one persistent worker. The 100-worker machine is therefore plausible, not
yet known to improve score.

## Evidence and baseline

- `Y` birth geometry, register/BP inheritance, creation order, wall errors,
  and collision death are specified in `claude/split-instruction-20260725.md`.
- The navigation and collision probes passed 24/24 on the server. Thus the
  needed `Y` semantics are confirmed rather than inferred.
- Submission `27976256-dce5-4ef8-bff4-746027434a7b` confirms the current
  `memory_06` baseline: 34x32, average 20,194.083 ticks, score
  23,344,360.333, 24/24.
- The public problem allows addresses 0..99, values -1,000,000..1,000,000,
  and 2..1,000 input tokens.
- Full `sim.py` does not yet implement `Y`. `split_probe.YMachine` models the
  new movement semantics but treats `r` as a permanent park and `s` as a nop,
  so it cannot validate the proposed machine end to end.

## Direct-address architecture

```text
                    request pipe 0  -> worker 0  (B = cell 0)
                  / request pipe 1  -> worker 1  (B = cell 1)
I -> DISPATCHER --             ...
                  \ request pipe 99 -> worker 99 (B = cell 99)
                                      |
                         shared response pipe
                                      v
                              DISPATCHER -> O
```

The dispatcher reads `op`, `addr`, and, for a write, `value`. It stores `op`
in BP, walks an address decision tree, and reaches an `s` instruction bound
to the selected worker's request pipe. It waits for one response before
accepting the next operation, which preserves write dependencies and read
output order without sequence numbers.

Every worker has one short local loop and stores only its cell value:

- READ request (`A=0`): `X` takes the read arm; `W s W` returns B while
  restoring it unchanged.
- WRITE request (`A=1`): the write arm receives the following value with
  `r`, executes `M`, and sends an acknowledgement such as zero.
- The worker then returns to its dedicated blocking `r`.

The worker does not need an address register: its physical request pipe is
its identity. Arithmetic in the dispatcher may freely destroy A and B
because the operation kind survives in BP and the reached leaf identifies
the address.

## Exact fan-out

`Y` need not produce a power of two. Recursively split a requested leaf count
`n` into `floor(n/2)` and `ceil(n/2)` disjoint subrectangles; stop splitting
at `n=1`. The resulting full binary tree contains 99 split cells and 100
leaves. Each leaf route ends at one worker loop. The layout must equalize or
otherwise separate simultaneous paths so no copies meet, swap through, or
spawn onto an occupied cell.

No explicit readiness barrier is required for correctness if a request token
may wait in its pipe: the dispatcher already waits for the worker's response.
A readiness measurement is still useful for timing and deadlock diagnosis.

## The real cost: ports and pipes

The straightforward design needs 100 independently selectable dispatcher
outputs entering one worker room, plus a shared response. `Y` removes 99 room
walls and 99 initial men; it does not copy pipe values or create private
channels.

The source permits multiple pipes per room and `s` selects the nearest
outgoing pipe, but a 100-pipe, same-room-pair topology is not yet
server-confirmed. Port claim regions, tie-breaking, minimum two-cell pipe
length, route crossings, and room perimeter are acceptance conditions. Use
`littleman.room_ports` to calculate bindings and margins rather than relying
on visual proximity.

An `S`-broadcast alternative sends each command to all workers, which then
compare the address in parallel. It replaces the dispatcher tree with 100
hard-wired comparators and still needs many destination channels. This is a
useful comparison point, but not the first build.

## Score thresholds

To beat the confirmed score 23,344,360.333, a candidate with maximum
dimension D must satisfy:

| D | maximum average ticks |
|---:|---:|
| 40 | 14,590 |
| 50 | 9,338 |
| 55 | 7,717 |
| 60 | 6,485 |
| 70 | 4,764 |

Thus a roughly 60-square 100-port layout needs more than a 3.1x tick
improvement. Direct access can remove the ring scan, but pipe flight and
address-tree travel can consume that advantage.

## Alternative: 34 packed-word workers

Thirty-four workers could retain `memory_04`'s proven three-values-per-word
encoding and require far fewer ports. However, a worker holding its word in B
cannot also hold the masks, shift, and incoming value needed for an update.
It therefore needs a shared ALU/scratch protocol and at least a word
round-trip. This is geometrically attractive but more register- and
protocol-heavy than 100 raw-value workers.

## Experiment sequence

1. Add `Y` and collision removal to the full pipe-capable simulator.
2. Build a parameterized 4-worker direct-address machine.
3. Prove spawn completion, B persistence, read/write acknowledgements,
   nearest-pipe bindings, and response serialization.
4. Scale through 10, 25, 50, and 100 workers; keep every measured geometry.
5. Test all public cases, all 100 addresses, boundary values, repeated
   overwrites, and deterministic streams near the 1,000-token limit.
6. Compare direct addressing, `S` broadcast, and 34 packed workers by actual
   `max(width,height)^2 * average_ticks`.

The target is 100 workers, but the best competitive point may be 25 or 50.
The implementation should therefore be generated from a worker-count
parameter rather than hard-coded directly at 100.
