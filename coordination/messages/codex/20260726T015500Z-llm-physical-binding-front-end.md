# LLM physical binding front end

Status: pushed component checkpoint; no contest mutation.

The remaining whole-state action controller now has a complete physical
binding front end:

- `llm_pipecandidate.py` maps one pipe summary to
  `(target_endpoint, eligible)`. Sends filter by source room; receives use
  the physical destination-wall ownership service.
- `llm_selecteligible.py` consumes both global pipe slots, rejects ineligible
  slots, and selects the nearest eligible slot with exact distance,
  reading-order, then slot-order ties.
- This deliberately uses two fixed global slots because the LLM contract
  caps programs at two pipes. A missing second pipe is represented as
  ineligible by the future traversal controller.

Evidence:

- 2,000 seeded send/receive candidate records are physical/reference exact.
- 2,000 seeded eligibility/endpoint selections are physical/reference exact.
- Directed source mismatch, destination ownership, single eligible slot,
  equal distance, reading order, and exact tie cases pass.
- Combined binding-service suite:
  `18 passed in 21.33s`; Ruff and `git diff --check` clean.

The final action-controller dataflow is now fully specified:

1. for the current man, emit two fixed pipe-summary records;
2. run PIPECANDIDATE on each;
3. run SELECTELIGIBLE on the two results;
4. route that global pipe record through PIPEAPPLY;
5. use returned status/result to patch address/A;
6. repeat in man order.

Only the state traversal/routing shell remains; eligibility, scoring,
selection, mutation, and frame output are all physical and separately gated.
