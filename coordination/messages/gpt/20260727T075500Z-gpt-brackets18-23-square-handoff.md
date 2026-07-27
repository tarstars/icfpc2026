# handoff: `gpt_brackets_18` is a parser-gated 23x23 Brackets candidate

- From: gpt
- To: claude
- CC: alexey, codex
- Created UTC: `2026-07-27T07:55:00Z`
- Task: `20260727-gpt-brackets-23-square`
- Branch: `agent/gpt-solvers-usage`
- Requires acknowledgement: YES

## Exact candidate

```text
submissions/brackets/gpt_brackets_18.man
SHA-256 50e85872d47e81c90f1205f0ae4c0341b62626630b1a1efb66552d357425320c
535 bytes
23x23, footprint 529
5 rooms / 6 pipes / 3 men
pipe lengths [4, 14, 2, 8, 4, 2]
```

Public result under server-compatible final-wall semantics:

```text
9/9
case ticks [256, 78, 114, 78, 158, 382, 140, 140, 2088]
average 381.55555555555554
score max(23,23)^2 * average = 201842.88888888888
```

Comparison:

```text
brackets_11 local 276615.0      -> -27.031112%
gpt_brackets_17  213248.0      ->  -5.348285%
```

## Solver result

A binary multi-commodity model jointly selected:

- vertical room order and exact origins;
- paired same-wall ports satisfying all nearest-pipe roles;
- six directed vertex-disjoint routes;
- legal first arrows away from each source room.

The first abstract solution was rejected after rendering because one I-to-OPEN
terminal also touched OUTPUT and the parser created a seventh one-cell phantom
pipe. The final search therefore included parser pipe count/topology and exact
named `s/r/q` binding checks as hard gates. The preserved candidate has exactly
the six intended room pairs and the accepted lineage's binding signature.

## Validation

```text
9,331 / 9,331 exhaustive strings over ()[]{}, lengths 0..5
71 / 71 directed boundary workloads
10,000 / 10,000 deterministic random strings, lengths 0..64
maximum additional runtime 2,120 ticks
```

Exact generation, SHA, parser structure, topology, binding map, server layout,
no shared walls, one input pipe, and minimum two-cell pipes pass.

Reproduce:

```bash
PYTHONPATH=src uv run pytest -q -n 0 tests/test_gpt_brackets_23.py
PYTHONPATH=src uv run python scripts/preflight.py \
  submissions/brackets/gpt_brackets_18.man brackets
```

Please fetch this branch, repeat repository-native validation and exact live
Brackets freshness, then submit the pinned SHA if it still improves the counted
result. GPT made no contest API call.

The 23-square write set is released. A 22-square successor requires a new CLOSE
component implementation or CLOSE/CLASSIFY fusion; port movement alone cannot
create routing clearance because CLOSE already spans all 22 columns.
