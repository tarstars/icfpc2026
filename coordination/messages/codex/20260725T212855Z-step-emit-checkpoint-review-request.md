# STEP emit checkpoint — review requested

Branch: `agent/codex-lllm-step`  
Commit: `7299096e9e238d499370a0e0223272d575830abe`

The physical STEP room now completes later-round space ticks end to end:

- `k=1`: output equals `run_case(rows, [1]).deltas`; canonical scratch is
  `[CTRL=1, ADDR=18, BI=0, AI=0, OLD=17, K=0]`.
- `k=2`: output equals `run_case(rows, [2]).deltas`; canonical scratch is
  `[CTRL=2, ADDR=34, BI=0, AI=0, OLD=17, K=0]`.
- both return to the blocked ROUND-IN `r` at local `(30, 8)`;
- `[1, 2, 1]` is consumed across three consecutive rounds and matches the
  reference stream exactly.

Evidence:

```text
uv run pytest tests/test_lllm_step.py -q
86 passed in 7.43s
```

Freshness gate before commit:

```text
git fetch origin
LLLM standings snapshot 2026-07-25T21:26:44.981Z
wheezards rows: []
```

Please perform a read-only adversarial review of the emit choreography,
especially host-B lifetime, FETCH request/response reconstruction, DRAW
port resolution, and the return highway. Do not edit the transferred STEP
paths while I continue with the class-7 conditional branch.
