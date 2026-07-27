# Solver-guided 24-square Brackets lineage

Date: 2026-07-27

## Best result

`gpt_brackets_17` is the best current candidate.

```text
artifact: submissions/brackets/gpt_brackets_17.man
SHA-256: 51a6219ee527d5607720a99a1401cba9d94de9579021d32f1a1ed79adbc72325
bytes: 594
rooms / pipes / men: 5 / 6 / 3
pipe lengths: [2, 2, 2, 5, 39, 3]
public: 9 / 9
public ticks: [242, 64, 100, 64, 144, 376, 132, 132, 2078]
average ticks: 370.22222222222223
footprint: 24^2 = 576
local score: 213248.0
```

The project score is:

```text
max(width, height)^2 * average ticks
```

Against `brackets_11` at local score `276615.0`, candidate 17 is
`22.908013%` lower (`1.29715x`). The repository live score for `brackets_11`
is `484532.65`; applying the parent server/local ratio gives a non-authoritative
projection near `373536`.

## Component folds

### CLOSE: one shared terminal send

The preceding room used a separate rightmost column for the mismatched-close
result. The new room moves `1,+` into the final existing column and shares the
unmatched-open `s`. Both paths step into the wall after the send. This behavior
is server-confirmed and judged locally through `littleman.server_compat`.
CLOSE outer width falls from 23 to 22.

### OPEN: terminal pair through the ordinary sender

The preceding room dedicated an entire row to end-of-stream. The new room routes
terminal state through two spare columns, constructs `(A=0,B=4)`, joins the
ordinary pair sender, and halts through a `d` branch whose backpack is zero.
Character paths retain positive backpack state and turn back into the scan loop.
OPEN outer height falls from 9 to 8.

## Port/placement optimization

Candidate 16 established the 24x24 box at score `216192.0`. Candidate 17 keeps
the same components and footprint, then applies a finite endpoint search:

- OPEN moves left and INPUT moves to the lower right;
- the CLASSIFY-return ports move to columns 9 and 7;
- the OPEN -> CLASSIFY endpoint moves one column right while preserving the
  intended nearest-pipe split;
- OPEN -> CLOSE shortens `10 -> 5` cells;
- OPEN -> CLASSIFY shortens `42 -> 39`;
- INPUT -> OPEN shortens `4 -> 3`.

Only transport pipes are shortened. Candidate 17 improves candidate 16 by
`1.361753%` without changing the 24-square footprint.

## Validation

```text
PYTHONPATH=src uv run pytest -q -n 0 tests/test_gpt_brackets_24.py
```

The available local environment used:

```text
PYTHONPATH=src python -m pytest -q -o addopts='' tests/test_gpt_brackets_24.py
# 3 passed
```

Evidence:

- deterministic generator byte equality for candidates 16 and 17;
- pinned hashes;
- strict parse: 5 rooms, 6 pipes, 3 men;
- `server_compat.validate_layout`: passed;
- no shared walls and exactly one input-adjacent pipe;
- every pipe has at least two cells;
- public 9/9 under server final-wall semantics;
- 9,331 exhaustive strings over `()[]{}` through length five;
- 266 directed boundary/type cases;
- 10,000 seeded random strings through length 64;
- zero behavioral failures.

The component rewrite deliberately removes four sends relative to `brackets_11`,
so raw I/O-op counts differ. Every surviving I/O instruction resolves to its
intended logical room pair. The smallest multi-candidate binding margin is one
cell and is covered by the exact layout tests.

## Authority

GPT has no contest credentials and made no platform mutation. The branch is
based on current integrated `main`. Claude is coordinator, integrator, and sole
submission controller and must repeat freshness, preflight, and hash checks
before deciding whether to submit.
