# LLM pipe runtime primitives checkpoint

Status: pushed implementation checkpoint; no contest mutation.

## What is now exact

- `llm_pipeaction.py` parses the fetched normalized state, binds `s` and `r`
  against the nearest eligible endpoint using `(distance, row, column,
  pipe_index)`, and applies actions sequentially in room/man execution order.
- It preserves the normalized pipe grammar including destination wall address,
  occupancy mask, and counted FIFO values.
- `full_statecycle_reference()` now composes the exact reference stages:
  mask-map, fetch-join, pipe action, man-map, and record-strip.
- `llm_pipeapply.py` is a physical one-selected-pipe primitive. Given
  `[operation, value, pipe_record...]`, it emits the updated record plus
  blocked/sent/received status and a receive result.

## Evidence

- `tests/test_llm_pipeaction.py`: 98 cases, including all 14 public programs,
  50 one-tick fuzz programs, 20 repeated 50-tick fuzz programs, and explicit
  mask/FIFO invariants, compared with `RingExecutor`.
- `tests/test_llm_pipeapply.py`: directed physical send/receive cases,
  including zero, negative values, blocked head, empty tail, and in-flight
  blocking; layout, pipe audit, and determinism gates.
- Focused integrated command over 11 runtime test modules:
  `349 passed in 19.00s`.
- Ruff and `git diff --check`: clean.
- Physical primitive dimensions: room `242 x 88`, 1,353 non-space cells;
  test rig `242 x 115`, 1,466 non-space cells.

## Remaining LLM path

The semantic state cycle is complete, but the physical machine still needs:

1. endpoint selector/binding around `llm_pipeapply`;
2. whole-state physical pipe-action traversal and recirculation;
3. wall freeze and per-frame emitter;
4. final assembly plus public/adversarial gates.

The existing live LLM result remains 2/28; this checkpoint is not a
submission candidate.
