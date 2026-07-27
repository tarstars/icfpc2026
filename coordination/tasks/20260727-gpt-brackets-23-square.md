# 20260727-gpt-brackets-23-square: joint component, port, and route synthesis

- Status: active
- Record owner: gpt
- Work owner: gpt
- Reviewer / integrator / submission controller: claude
- Problem: `brackets`
- Base: current `agent/gpt-solvers-usage` after immutable `gpt_brackets_17`
- Branch: `agent/gpt-solvers-usage`
- Created UTC: `2026-07-27T07:30:00Z`
- Progress lease: 15 minutes without concrete pushed evidence

## Outcome

Find a server-compatible Brackets machine with
`max(width,height) <= 23`, or preserve a finite infeasibility/counterexample
certificate for the current component family and switch immediately.

## Write set

- `src/littleman/gpt_brackets_23.py`
- `tests/test_gpt_brackets_23.py`
- `submissions/brackets/gpt_brackets_18.man`
- `experiments/gpt-solvers-usage/brackets23_*.py`
- `experiments/gpt-solvers-usage/gpt_brackets_18.man`
- `experiments/gpt-solvers-usage/gpt_brackets_18-evidence.json`
- `reports/2026-07-27-gpt-brackets-23-square.md`
- this task, GPT status, and GPT messages

All prior `.man` artifacts are immutable and read-only.

## Search model

Jointly choose:

1. component variants for CLASSIFY, CLOSE, OPEN, input, and output;
2. rectangle origins inside a 23x23 envelope;
3. same-wall source/destination port cells;
4. six vertex-disjoint pipe routes;
5. logical nearest-pipe bindings at every `s`, `r`, and `q` cell.

The search must include room-cell obstacles, first/last pipe-direction legality,
input-room adjacency, no shared walls, and the server-confirmed final-wall drain
semantics.

## Hard score gate

The objective is always:

```text
max(width,height)^2 * average ticks
```

At the current 370.222 public average, a 23-square scores about 195,848 and
beats `gpt_brackets_17` by about 8.2%. A candidate is retained only if its exact
judged score is lower than 213,248.

## Acceptance

- exact generator/artifact equality and SHA;
- parser/server layout/minimum-pipe/input-adjacency gates;
- unchanged logical pipe-role map or an explicitly verified replacement;
- 9/9 public cases under server-compatible semantics;
- exhaustive strings through length five;
- at least 10,000 deterministic random strings through length 64;
- no contest API call by GPT.

## Coordination

Claude owns the generic `layout_ir` / `layout_solve` / `layout_route` work and
all submissions. This task uses isolated experiment code and does not edit
those shared solver files.
