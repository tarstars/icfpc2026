# GPT Brackets 24-square search

Date: 2026-07-27

Status: first 24-wide concrete candidate preserved; one row remains before the
square objective changes.

## Current checkpoint: `gpt_brackets_16`

The artifact is:

```text
experiments/gpt-solvers-usage/gpt_brackets_16.man
sha256 081cd30e57d63e7776280755ea75498870fcfff2575fe3b5ee2b3995ae80c79f
```

It is a 24x25 successor to `gpt_brackets_15`. It parses as five rooms, three
men, and six pipes with parser-order lengths:

```text
[2, 2, 2, 9, 41, 2]
```

The change is a component-frontier move rather than a blind squeeze:

1. CLOSE's outer width drops from 23 to 22. The empty-stack arm shares its
   eastmost send with the terminal path and then takes a final wall step.
2. OPEN and INPUT shift one column left into the released space.
3. OPEN -> CLOSE becomes a nine-cell shortest route.
4. OPEN -> CLASSIFY moves one corridor column left and becomes 41 cells.

The final wall step is intentional. The server has already accepted this exact
semantic pattern on live programs; repository validation must use
`littleman.server_compat`, whose `alexey_walljudge` lets already-sent output
drain after the man reaches the wall.

## Measured evidence

The local exact engine was first anchored by reproducing the checked-in
`gpt_brackets_15` public ticks:

```text
[246, 58, 106, 70, 146, 380, 136, 136, 2082]
```

`gpt_brackets_16` then produced:

```text
[245, 57, 105, 69, 145, 379, 135, 135, 2081]
```

Summary:

```text
                         gpt_brackets_15   gpt_brackets_16
box                      25x25             24x25
footprint                 625               625
public average ticks      373.333333        372.333333
public local score        233333.333        232708.333
relative improvement                         0.267857%
```

The candidate also passed:

- all 9,331 strings over `()[]{}` of lengths 0 through 5;
- 2,000 seeded legal strings of lengths 0 through 64;
- the Python bracket oracle on every workload;
- output equivalence with `gpt_brackets_15` on every randomized workload.

The randomized tick delta was exactly `-1` for all 2,000 cases.

These are local measurements. GPT did not query live state, invoke the contest
API, or submit.

## Why this matters even before 24x24

The score still pays 25 squared, so the current candidate buys only its tick
reduction. Its main value is removing the width barrier cleanly: a single row
fold now turns the 625 footprint into 576, an 7.84% footprint reduction before
any tick effect.

The remaining search is therefore sharply defined. It is not another global
placement problem. One of these component-level changes must succeed:

- remove one OPEN row while preserving the command and state bindings;
- move CLASSIFY to the top boundary and replace its long incoming landing pad;
- reflow/rotate OPEN and CLASSIFY as a finite implementation pair inside the
  24-square envelope;
- use a second server-safe terminal-wall share in a component whose final send
  currently requires a dedicated row.

Each implementation candidate must carry its binding map and be placed jointly
with its port options. A geometrically smaller room without those constraints
is not a valid solver result.

## Repository replay requested

```bash
PYTHONPATH=src uv run python \
  experiments/gpt-solvers-usage/build_gpt_brackets_16.py \
  > /tmp/gpt_brackets_16.man
cmp /tmp/gpt_brackets_16.man \
  experiments/gpt-solvers-usage/gpt_brackets_16.man
PYTHONPATH=src uv run python \
  experiments/gpt-solvers-usage/test_gpt_brackets_16.py
uv run python scripts/preflight.py \
  experiments/gpt-solvers-usage/gpt_brackets_16.man brackets
```

Claude, as the current coordinating/submission agent, should replay these gates,
refresh the exact live Brackets baseline, and decide whether to number, promote,
or submit. GPT retains no platform authority.
