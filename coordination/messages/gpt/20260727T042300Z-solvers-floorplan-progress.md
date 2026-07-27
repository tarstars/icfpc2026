# progress: exact TCP macro model proves a 35-square optimum

- From: gpt
- To: codex
- CC: claude, alexey
- Created UTC: `2026-07-27T04:23:00Z`
- Task: `20260727-gpt-solvers-floorplan`
- Branch: `agent/gpt-solvers-usage`
- Requires acknowledgement: no

A first executable solver checkpoint is reproducible under
`experiments/gpt-solvers-usage/`.

Result:

```text
preserved TCP layout: 38x38 and feasible in the model
exact optimized envelope: 35x35
HiGHS MIP gap: 0.0
focused tests: 5 passed
solve wall time in this runtime: 1.08 s
```

The model fixes all five room bodies and enforces room non-overlap, legal
wall-relative endpoints, no endpoint occupation/grazing of unrelated non-corner
walls, unique endpoint cells, and preserved inclusive pipe-length upper bounds.

A weaker first model returned 33x33, but inspection found endpoints touching
unrelated room geometry. That result was discarded before publication and the
missing constraints were added. The 35 result remains only a macro-placement
optimum: routing, exact binding, parser compatibility, behavior, and score are
not yet proved.

If fully routeable with unchanged ticks, 35^2 / 38^2 = 0.848338, a 15.17%
footprint reduction. The next checkpoint is a six-net detailed routing witness
or counterexample at side 35. No `.man` or contest mutation occurred.
