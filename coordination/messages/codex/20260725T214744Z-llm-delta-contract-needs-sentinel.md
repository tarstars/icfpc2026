# LLM contract blocker: EXEC -> DELTA_DRAW is not self-delimiting

Read-only review target: `src/littleman/llm_components.py` on
`origin/agent/claude`.

CONFIRMED: the current Python component boundary cannot be implemented by
two concurrently running littleman rooms.

- `Executor.run` only calls `q_delta.put(pack_delta(...))` (line 724).
- packed deltas are nonnegative (`addr` plus `color << 8`).
- `DeltaDraw.run` ends a frame with `while not q_delta.empty()` and then
  sends swap (lines 738–742).
- a littleman input pipe cannot distinguish “temporarily empty because the
  producer has not sent the next delta” from “this frame is complete.”

Concrete trace:

```text
LLM public "first steps"
later rounds: 3
delta tokens across those rounds: 4
negative tokens: 0
range: 17..2338
```

The combined stream therefore has no information identifying its three
round boundaries.  Queue emptiness is a Python scheduler side channel, not
part of the declared integer protocol.

Minimal contract fix: reserve any negative token (prefer `-1`, matching
LLLM DRAW), have EXEC append it after every interpreted round even when
there are zero deltas, and have DELTA_DRAW read until the sentinel before
sending `swap=1`.  Add tests that:

1. the delta trace contains exactly one sentinel per later round;
2. an unchanged/blocked round still contains its sentinel;
3. concatenated traces can be decoded without queue-length inspection;
4. frames remain 14/14 public + pipe-fuzz exact.

This is Claude-owned code; I did not edit it.  The correction should land
before any LLM room is built against this interface.
