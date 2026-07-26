# LLM frame-to-DRAW adapter

Status: component checkpoint; no contest mutation.

`llm_pairpack.py` consumes the exact `(color, address)` stream emitted by
STATEFRAME and produces DRAW-compatible deltas:

`address * 16 + color`.

The physical room uses one scratch ring and multiplication by a literal 16.
It relays the negative frame delimiter and halts without assuming any
particular frame length.

Evidence:

- 2,000 randomized physical/reference streams are byte-exact;
- directed minimum `(0, 0)` and maximum `(15, 4095)` cases pass;
- deterministic generation, server layout, pipe audit, and Ruff pass;
- `3 passed in 1.07s`.

Freshness before commit:

- `origin/main` is `f35eb11`;
- exact live LLM submission `e57fd7d2-352d-4929-a474-2009a6af4fd0`
  remains `2/28` (13/14 public and 13/14 private wrong-frames).
