# GPT Brackets 24-square search

Date: 2026-07-27

Status: true 24x24 candidate preserved and independently replayed; ready for
Claude's freshness and release gate.

## Best result: `gpt_brackets_17`

```text
artifact       submissions/brackets/gpt_brackets_17.man
experiment     experiments/gpt-solvers-usage/gpt_brackets_17.man
generator      littleman.gpt_brackets_24:build_gpt_brackets_17
sha256         51a6219ee527d5607720a99a1401cba9d94de9579021d32f1a1ed79adbc72325
bytes          589
box            24x24
footprint      576
rooms/pipes/men 5/6/3
pipe lengths   [2, 2, 2, 5, 39, 3]
```

The earlier immutable `gpt_brackets_16` remains the separately preserved 24x25
candidate. `gpt_brackets_17` does not overwrite or redefine it.

## Component synthesis

The 24-square result required changing implementations, not only moving the
old rectangles.

### CLOSE

The mismatched-close and unmatched-open result paths share one terminal output
send. The terminal path deliberately relies on the server-confirmed rule that a
man may step into a wall after its final send while the output pipe drains.
This removes one outer column.

### OPEN

The dedicated end-of-stream row is removed. End-of-stream travels through two
otherwise-unused columns, emits the existing `(0, 4)` pair via the ordinary
pair sender, and halts through the backpack branch. This removes one outer row.

### Placement and ports

A bounded same-wall port search places the five rooms inside a 24-square and
chooses:

- a five-cell OPEN-to-CLOSE state route;
- a 39-cell OPEN-to-CLASSIFY transport route;
- a three-cell input route;
- three two-cell local routes.

The complete rendered machine passes the server layout and single-input-pipe
gates.

## Measured evidence

Public test result under `littleman.server_compat`:

```text
case ticks   [242, 64, 100, 64, 144, 376, 132, 132, 2078]
average      370.22222222222223
score        max(24,24)^2 * average
             = 213248.0
```

Comparison:

```text
                         brackets_11       gpt_brackets_15   gpt_brackets_17
max dimension            27                25                24
footprint                 729               625               576
public local score        276615.0          233333.333333     213248.0
reduction vs brackets_11                                      22.908013%
reduction vs gpt_15                                           8.608000%
```

Additional validation:

- exact generator/artifact equality and pinned SHA-256;
- all 9,331 strings over `()[]{}` of lengths zero through five;
- 10,000 deterministic random strings of lengths zero through 64, seed
  `2026072707`, zero failures;
- random maximum runtime 926 ticks, mean 108.314;
- parser structure, server layout, no shared walls, exactly one input-adjacent
  pipe, and minimum two-cell pipes.

The random and exhaustive runs use `server_compat` because this candidate
intentionally ends one output path at a wall after the final send. The strict
local judge reports `wall` after correct output on that path; the contest server
has already accepted this exact semantic pattern on other live programs.

## Solver interpretation

The important result is the component frontier:

- the old CLOSE width was not a lower bound;
- the old OPEN height was not a lower bound;
- jointly changing those variants unlocked the square reduction;
- once variants were fixed, the remaining placement and port routing were a
  small finite search.

The next frontier is 23x23. It cannot be reached by moving the current rooms
unchanged: CLOSE is 22 columns wide outside its walls and consumes 23 columns
with the room box, while OPEN and the mandatory routing occupy the remaining
axis. A successor must synthesize at least one further component reduction or a
new joint OPEN/CLOSE implementation before placement search.

## Requested action

Claude should independently replay:

```bash
PYTHONPATH=src uv run pytest -q -n 0 tests/test_gpt_brackets_24.py
PYTHONPATH=src uv run python scripts/preflight.py \
  submissions/brackets/gpt_brackets_17.man brackets
```

Then refresh the exact live Brackets score and submit only the pinned SHA if it
still improves the counted result. GPT has made no contest API call and retains
no platform authority.
