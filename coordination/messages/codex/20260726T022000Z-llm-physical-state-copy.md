# LLM physical state fan-out

Status: pushed component checkpoint; no contest mutation.

`llm_statecopy.py` consumes one normalized state and emits:

`state, COPY_SPLIT, state, COPY_END`.

It is delimiter-safe despite negative record markers and uses a deliberately
long private return pipe sized for the maximum normalized state, so the first
copy can stream while the second is retained for STATEFRAME or WALLSCAN.

One geometry defect was caught and fixed: the first return route turned
immediately downward at the relay wall, so it did not form a legal outgoing
pipe. The route now travels one cell left before bending; the parser sees all
four intended pipes.

Evidence:

- all 14 public plus 10 pipe-bearing fuzz states are physical/reference byte
  exact;
- deterministic generation, server layout, pipe audit, and Ruff pass;
- `25 passed in 1.07s`.

This supplies the recirculation shell's required fan-out without relying on
queue emptiness or a fixed state length.
