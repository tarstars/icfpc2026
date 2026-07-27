# GPT Brackets 26-square candidate

Date: 2026-07-27

Status: immutable candidate generated and extensively replayed locally; no
platform submission.

## Result

`gpt_brackets_12.man` is a 26x26 successor to accepted `brackets_11`.

```text
artifact:    submissions/brackets/gpt_brackets_12.man
generator:   littleman.gpt_brackets_26:build_gpt_brackets_26
SHA-256:     8cc306772304f39e21f6b140586844419b55103cec575834228dc9350bc2c4a5
bytes:       671
rooms/pipes/men: 5 / 6 / 3
pipe lengths:    [2, 2, 2, 13, 47, 2]
```

The candidate's exact repository-public result under the reconstructed current
simulator semantics is:

```text
cases:       9 / 9
ticks:       [248, 60, 108, 72, 150, 384, 140, 140, 2086]
average:     376.44444444444446
footprint:   676
local score: 254476.44444444444
```

The same replay reproduces `brackets_11` exactly at public ticks
`[250, 62, 110, 73, 154, 388, 144, 144, 2090]` and local score `276615.0`.
Therefore the candidate is 8.003382% better locally.

This is a local measurement, not a live score. The accepted server score for
`brackets_11` is 484,532.65; applying a local ratio would only be a projection,
so no projected number is used as submission evidence.

## Solver-guided component frontier

The preceding exact endpoint solve proved the two short room0/room2 gap pipes
were already at the absolute two-cell minimum. The next variable had to be room
implementation. Two small, finite body variants were sufficient.

### CLOSE width 25 -> 24

The former final output arm ended on one row:

```text
... r M 1 + s H
```

The `s` and `H` occupied relative columns 22 and 23. The variant keeps the
arithmetic prefix, turns down at relative `(2,22)`, sends at `(3,22)`, and halts
at `(4,22)`. Both destination cells were blank and outside every other control
path. The send still resolves to the output pipe. This removes the 23rd
interior column.

### OPEN height 11 -> 10

The old one-time startup prefix read `n`, descended to a dedicated bottom row,
turned west, then climbed into the loop:

```text
row 8: @ r v
row 9: ^   <
```

The variant changes row 8 to `@ r ^`, rises into a new `<` at row 7 column 3,
then joins the existing westbound return row and its column-1 climb. The new
arrow is harmless when the ordinary return path later crosses it while already
moving west. The dedicated ninth interior row is deleted.

### Physical consequence

CLOSE's freed right column creates a legal corridor at global column 25. The
OPEN-to-CLASSIFY transport pipe moves from column 26 to 25 and shortens from 49
to 47 cells. The room placements otherwise retain the accepted topology.

The final scored box is 26x26. No pipe-role count changes: every `s`, `r`, and
`q` role count by room and parser pipe index equals the `brackets_11`
signature. The one moved `s` still selects the output pipe.

## Validation performed

The exact checked-in candidate passed:

- all 9 repository public cases;
- all 9,331 strings over `()[]{}` of length 0 through 5;
- 425 directed cases covering empty input, maximum depth, maximum length,
  every offense position, unclosed stacks, and wrong-type closers;
- 10,000 deterministic random strings, seed `2026072702`, length 0 through 64,
  with the generated open-count capped at 32.

There were zero failures. Against `brackets_11`, all 10,000 random cases
completed one to four ticks earlier; mean delta was `-1.9823` ticks.

Static evidence:

- parser finds five rooms, six pipes, and three men;
- parser-order pipe lengths are `[2, 2, 2, 13, 47, 2]`;
- every pipe has at least two cells;
- dimensions are exactly 26x26;
- generator output is byte-identical to the artifact;
- exact SHA-256 is pinned above.

The branch also contains a focused repository test that invokes the project
parser, `alexey_pipecheck`, `server_compat.validate_layout`, exact public judge,
short exhaustive corpus, and deterministic boundary fuzz.

## Independent gate still required

GPT's runtime has GitHub connector access but not the user's native repository
checkout. The local replay engine was reconstructed directly from current
`sim.py` semantics and validated by reproducing the exact known
`brackets_11` public score, but this is not a substitute for an independent
checkout run.

Before any platform action, Codex or the current submission controller should
run:

```bash
PYTHONPATH=src uv run pytest -q -n 0 tests/test_gpt_brackets_26.py
PYTHONPATH=src uv run python scripts/preflight.py \
  submissions/brackets/gpt_brackets_12.man brackets
```

They should also refresh the exact live Brackets submission and standings state.
No platform submission was made by this task.
