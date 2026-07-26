# LLM physical state index

Status: component checkpoint; no contest mutation.

`llm_stateindex.py` transforms the interleaved normalized state into:

1. compact room headers;
2. `SETUP_END, INDEX_SPLIT`;
3. a global pipe table whose records begin `(start, source_event)`;
4. `INDEX_END`.

The room's negative event token is unique and remains in B while every
variable-length pipe record is scanned. This removes the need for a separate
room counter or register pipe. The counted values loop sets BP directly from
A, so B retains the source identity.

Evidence:

- all 14 public plus 10 pipe-bearing fuzz states are physical/reference
  byte-exact;
- deterministic generation, server layout, pipe audit, and Ruff pass;
- `26 passed in 0.52s`;
- rig is 274 x 113 with 1,136 occupied cells;
- public cases take 3,375 through 24,143 ticks.

The physical tests exposed and fixed two binding defects: late main-stream
reads initially preferred the scratch return pipe, and the late scratch
sentinel initially preferred display output. Centered external and scratch
endpoints make every intended binding strict.

Freshness before commit:

- `origin/main` is `f35eb11`;
- exact live LLM submission `e57fd7d2-352d-4929-a474-2009a6af4fd0`
  remains `2/28`.

Next composition step: run PIPECANDIDATE over each tagged table record for
one compact room header, SELECTELIGIBLE once, and use the selected source tag
plus slot to route one record through PIPEAPPLY.
