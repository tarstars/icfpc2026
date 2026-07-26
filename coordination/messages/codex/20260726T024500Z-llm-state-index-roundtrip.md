# LLM indexed-state round trip

Status: pushed contract gate; no contest mutation.

The indexed state now has a strict inverse reference. It rejects duplicate
room events, unknown pipe sources, malformed markers, and trailing tokens.

Evidence:

- `stateunindex_reference(stateindex_reference(state)) == state` for all
  14 public and 20 pipe-bearing fuzz states;
- the complete state-index suite is `60 passed in 0.53s`;
- Ruff passes;
- the exact live LLM submission remains `2/28`.

This confirms that globalizing the two pipe records loses no information and
can be reversed after the selected PIPEAPPLY mutation.
