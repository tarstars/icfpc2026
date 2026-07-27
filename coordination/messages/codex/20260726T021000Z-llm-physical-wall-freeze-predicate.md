# LLM physical wall-freeze predicate

Status: pushed component checkpoint; no contest mutation.

`llm_wallhit.py` consumes normalized room bounds plus the man's current
address and returns exact wall contact, distinguishing the interior from all
four walls. This closes the last leaf-level semantic gap needed after the
action/man map: if any live man returns 1, the program freezes before another
interpreted tick.

Evidence:

- 2,000 seeded rectangles/addresses are physical/reference exact;
- directed top, bottom, left, right, and interior cases pass;
- determinism, server layout, pipe audit, and Ruff gates pass;
- `3 passed in 4.78s`.

The final traversal shell therefore has no remaining arithmetic predicates
to invent. Its service set is PIPEMASK, FETCH, PIPECANDIDATE,
SELECTELIGIBLE, PIPEAPPLY, MANSTEP, WALLHIT, and STATEFRAME.
