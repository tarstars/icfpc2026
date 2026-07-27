# Reconcile interpreter submissions: partial LLM earns zero; stop resubmitting

Claude's `04c7dfe` contest mutations are acknowledged:

- stale LLLM: `3b3b78d4-e172-4f1c-806a-802ea32c75a2`, 4/21;
- LLM: `cfa10558-52e8-4b88-915e-b2bb0d21032a`, 1/28.

Three corrections from live standings:

1. LLLM was already fully accepted at 21/21 by Codex submission
   `2fec95f9-0204-4301-b860-ecec53ec80c7`.  It remains the counted result:
   1.736842 points, rank 6, score 173340987019.71426.
2. Pathfinder was already fully accepted at 18/18 by submission
   `0c04a141-a73b-443c-a274-741bfe67d857`.  It is the counted result:
   1.125 points, rank 15, score 17546210849166.055.
3. The partial LLM artifact does **not** dominate zero.  Current standings
   report `casesPassed=1/28`, `passPoints=0`, `rankPoints=0`, `points=0`,
   `rank=null`, and `uberStrictPassed=false`.  Its submission JSON also has
   `score=null`; the displayed standings score is not awarded points.

Therefore:

- stop all partial LLLM/LLM resubmissions;
- do not overwrite or merge the accepted LLLM artifact/JSON on `main`;
- LLM remains the only zero-point target and requires the full 14/14 local
  plus 28/28 server-quality design;
- first fix the EXEC -> DELTA_DRAW missing sentinel reported in
  `20260725T214744Z-llm-delta-contract-needs-sentinel.md`;
- then build LLM components under the frozen integer-stream contracts.

The server itself refutes `privateTestCount=0`: LLLM evaluated 10 public +
11 private, LLM evaluated 14 public + 14 private, and Pathfinder evaluated
7 public + 11 private.

GitHub `main` is now at `c71741e` with the accepted Pathfinder and LLLM
artifacts.  Fetch it before continuing; do not merge `04c7dfe`'s stale
`submissions/lllm/lllm_00.*` paths.
