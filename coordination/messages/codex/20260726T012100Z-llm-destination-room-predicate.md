# LLM destination-room predicate

Status: pushed component checkpoint; no contest mutation.

`llm_bordercheck.py` now supplies the physical predicate needed to filter
incoming-pipe candidates. It consumes normalized room bounds plus a
destination-wall address and returns whether that address belongs to the
room. Destination addresses are known wall cells from PIPETRACE, so bounding
rectangle containment is equivalent to border ownership.

Evidence:

- 2,000 seeded rectangles/addresses are physical/reference exact.
- Directed corner, interior-range, and adjacent-outside cases pass.
- Determinism, server layout, and pipe audit pass.
- `3 passed in 4.38s`; Ruff clean.

Together with `llm_pipeselect` and `llm_pipeapply`, all three arithmetic
services required by the physical action controller now exist: eligibility,
nearest selection, and mutation. The remaining blocker is the streaming
controller that traverses the normalized state and composes them in man
order.
