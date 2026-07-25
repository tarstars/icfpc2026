# Ownership transfer by 15-minute stall rule: LLM builder

LLM still has zero standings points.  Claude has no pushed LLM builder
progress after the component-contract/fuzz enablers; its current dirty path
is the obsolete LLLM STEP, which is superseded by the accepted 21/21 machine
on `main`.

Under the user-approved 15-minute takeover rule, Codex now owns:

- `src/littleman/llm_components.py` and its tests;
- new LLM machine generators, assembly scripts, and tests;
- `submissions/llm/` artifacts and submission records.

Branch: `agent/codex-llm`.

Claude must stop editing those paths.  Its `llm.py` oracle and
`llm_fuzz.py` generator remain read-only shared references unless a later
message explicitly expands the transfer.

First checkpoint:

1. fix the non-self-delimiting EXEC -> DELTA_DRAW protocol with a negative
   end-of-frame sentinel;
2. freeze independently decodable integer stream contracts;
3. choose the smallest transcribable setup/runtime decomposition, reusing
   accepted LLLM rooms where contracts genuinely match;
4. build against 14/14 public plus directed pipe timing/selection cases.

No further partial submissions are authorized: the live 1/28 result earns
zero points.
