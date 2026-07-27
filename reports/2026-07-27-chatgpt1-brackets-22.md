# chatgpt_1 Brackets 22-square checkpoint

Date: 2026-07-27

Status: macro-placement frontier saved; no 22x22 `.man` claimed.

## Synchronization

The chatgpt_1 branch was synchronized with `main` through
`03a8f74ad1c0d8db9db34d08da3718ec3db08629`. Upstream coordination, the final
two-hour plan, `subdb.py`, and the live Reverse submission record were retained
without modifying peer-owned namespaces.

The previous chatgpt_1 Reverse artifact is now live:

```text
artifact   chatgpt1_reverse_09.man
geometry   17x17
result     20/20
score      62,568.5
improvement 84,423.95 -> 62,568.5, factor 1.349x
```

Claude submitted it; chatgpt_1 made no contest API call.

## Saved Brackets artifacts

```text
experiments/chatgpt1-brackets-22/README.md
experiments/chatgpt1-brackets-22/macro_frontier.py
experiments/chatgpt1-brackets-22/macro_frontier.json
```

The standard-library enumerator fixes the existing room bodies and explores
the sharp 22-square macro family:

- CLOSE, width 22, lies on the top or bottom boundary;
- OPEN and CLASSIFY occupy the remaining 15 rows with one routing row;
- the two 3x3 I/O rooms occupy side pockets;
- endpoint cells must satisfy a conservative no-phantom-attachment test.

Measured checkpoint:

```text
room area                         412 / 484
free cells after rooms             72
parent pipe cells                   53
raw residual slack                  19
stack-family packings           25,764
safe-port necessary survivors     1,700
best independent route lower bound   21 cells
```

Best lower-bound seed:

```text
CLOSE      (15, 0)
OPEN       ( 0, 3)
CLASSIFY   ( 9, 0)
INPUT      ( 0, 0)
OUTPUT     (10,17)

lower bounds [3, 3, 2, 7, 3, 3]
```

## Interpretation

This proves that the 22-square component rectangles are not blocked by area or
by a trivial lack of legal wall-adjacent endpoint cells. It does **not** prove
simultaneous endpoint assignment or routing.

The remaining discriminating step is a parser-in-the-loop multi-commodity
router with exact named binding constraints. Each rendered survivor must have:

```text
5 rooms / 6 pipes / 3 men
the six intended named room pairs
the accepted `s`/`r`/`q` binding signature
no shared wall, phantom pipe, one-cell pipe, or extra input adjacency
```

Only after that gate does behavioral judging begin. The final release commands
remain:

```bash
uv run python scripts/wasm_judge.py <candidate.man> brackets
uv run python scripts/subdb.py compare <candidate.man> brackets
```

No Brackets candidate and no contest submission is claimed in this checkpoint.
