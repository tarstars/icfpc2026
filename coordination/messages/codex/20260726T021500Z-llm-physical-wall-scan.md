# LLM physical wall-scan stage

Status: pushed component checkpoint; no contest mutation.

`llm_wallscan.py` lifts WALLHIT from a leaf predicate to a stream stage. It
consumes one complete normalized state, calls WALLHIT for every room, skips
all variable-length pipe/FIFO records, and emits one per-room flag followed
by `WALLSCAN_END`.

Evidence:

- 18 physical/reference snapshots across 0/1/2 pipes, 1/2/3 rooms, and
  0/1/3 interpreted ticks;
- deterministic generation, server layout, pipe audit, and Ruff pass;
- `19 passed in 0.29s`.

The recirculation gate can now make the freeze decision from a copied state
stream without embedding any geometry arithmetic.
