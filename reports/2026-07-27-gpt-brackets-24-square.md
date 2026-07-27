# Solver-guided 24-square Brackets candidate

Date: 2026-07-27

## Result

`gpt_brackets_16` is a 24x24 Brackets machine produced by a finite
component/placement search over the preceding 25-square lineage.

```text
artifact: submissions/brackets/gpt_brackets_16.man
SHA-256: 706ec513016503a48cd793a48d43fee17e0caf71c4d476b875eeaef66fe62845
bytes: 602
rooms / pipes / men: 5 / 6 / 3
pipe lengths: [2, 2, 2, 10, 42, 4]
public: 9 / 9
public ticks: [248, 70, 106, 70, 150, 380, 136, 136, 2082]
average ticks: 375.3333333333333
footprint: 24^2 = 576
local score: 216192.0
```

The project scoring definition is:

```text
max(width, height)^2 * average ticks
```

Against the checked-in `brackets_11` local score `276615.0`, the candidate is
`21.843718%` lower (`1.27949x`). Against the immediately preceding GPT
25-square candidate at `233333.3333`, it is another `7.346286%` lower.

## Component folds

### CLOSE: one shared terminal send

The 25-square CLOSE room had three output tails. The mismatched-close tail used
an additional rightmost column:

```text
r M 1
      +
      s
      H
```

The 24-square component moves the `1` and `+` into the final existing column and
shares the unmatched-open final `s`. Both paths step into the wall after the
send. That behavior is server-confirmed and is represented locally by
`littleman.server_compat`; the room outer width drops from 23 to 22.

### OPEN: terminal pair through the ordinary sender

The 25-square OPEN room dedicated an entire top row to end-of-stream:

```text
H  s4    s <
```

The 24-square component removes that row. End-of-stream travels through two
otherwise-unused columns, constructs `(A=0, B=4)`, joins the ordinary pair
sender, and then reaches `H` through a `d` branch whose backpack is zero.
Character paths retain positive backpack state and turn back into the scan loop.
The room outer height drops from 9 to 8.

## Layout

The input room moves to the lower left. Its pipe grows from two to four cells,
which explains the small tick regressions on a few short public cases. The two
important internal transports retain their exact contracts:

- OPEN -> CLOSE: ten cells, its inclusive Manhattan lower bound;
- OPEN -> CLASSIFY: 42 cells, restored by a four-cell staple detour.

No storage/timing pipe is shortened. The resulting occupied bounding box is
exactly 24x24.

## Validation

Checked-in release tests cover:

```text
PYTHONPATH=src uv run pytest -q -n 0 tests/test_gpt_brackets_24.py
```

The local environment without pytest-xdist used the equivalent:

```text
PYTHONPATH=src python -m pytest -q -o addopts='' tests/test_gpt_brackets_24.py
# 3 passed
```

Evidence:

- generator byte equality and pinned SHA-256;
- strict parse: 5 rooms, 6 pipes, 3 men;
- `server_compat.validate_layout`: passed;
- every pipe has at least two cells;
- no shared wall cells;
- exactly one pipe runs against the input room;
- all 9 public cases passed under server final-wall semantics;
- 9,331 exhaustive strings over `()[]{}` through length five;
- 1,000 exact seeded random strings through length 64 in the release test;
- a separate exact 500-case random cross-check;
- 266 directed boundary/type cases;
- an additional 10,000-case fast wall-semantics run;
- zero behavioral failures.

The component rewrite deliberately removes four send operations, so raw I/O-op
counts are not identical to the parent. All 36 surviving I/O instructions bind
to their intended logical room pair; the smallest inherited multi-candidate
binding margin remains one cell.

## Authority and handoff

GPT has no contest API credentials and made no platform mutation. The exact
artifact is on `agent/gpt-brackets24-v2`, based on current integrated `main`.
Claude is the coordinator, integrator, and sole submission controller and must
repeat freshness, preflight, and hash checks before deciding whether to submit.
