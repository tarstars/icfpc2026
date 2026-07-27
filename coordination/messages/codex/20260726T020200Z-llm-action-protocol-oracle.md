# LLM action-controller protocol oracle

Status: pushed contract checkpoint; no contest mutation.

`llm_actionprotocol.py` is the executable contract for the remaining physical
state traversal. For each man in room order it:

1. emits the exact 9-token PIPECANDIDATE requests for both global slots;
2. passes `(man, eligible0, eligible1, target0, target1)` through
   SELECTELIGIBLE;
3. passes `(op, A, normalized_pipe_record)` through PIPEAPPLY;
4. patches pipe mask/FIFO and, on success, the man address/A;
5. records `(room, op, selected_pipe, status, result)`.

It does not reimplement the leaf arithmetic. It calls the same reference
grammars used to gate the physical rooms, so a future traversal controller can
be checked token-for-token at every boundary.

Evidence:

- exact equality with the monolithic pipe-action oracle on all 14 public plus
  50 pipe-bearing fuzz states;
- repeated 30-cycle comparisons on 20 fuzz states, stopping at the LLM
  wall-freeze/halt boundary;
- combined action/protocol/physical-leaf suite:
  `199 passed in 7.18s`;
- Ruff and `git diff --check` clean.

The smallest remaining implementation is now unambiguous: a recirculating
state-shell that emits these frozen requests and applies their frozen
responses. No arithmetic or selection semantics should be added to that
shell.
