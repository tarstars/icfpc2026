# GPT Brackets 26-square candidates

Date: 2026-07-27

Status: two immutable candidates generated and extensively replayed locally;
no platform submission.

## Best result

`gpt_brackets_13.man` is a 26x26 successor to accepted `brackets_11` and to the
first branch candidate `gpt_brackets_12`.

```text
artifact:    submissions/brackets/gpt_brackets_13.man
generator:   littleman.gpt_brackets_26:build_gpt_brackets_13
SHA-256:     c4f5449b830f72f5529e82aa7034d580956aa83baffd162e4a36ebb6219e4eed
bytes:       669
rooms/pipes/men: 5 / 6 / 3
pipe lengths:    [2, 2, 2, 44, 13, 2]
```

The exact repository-public result under the locally reconstructed current
simulator is:

```text
cases:       9 / 9
ticks:       [248, 60, 108, 72, 147, 381, 137, 137, 2083]
average:     374.77777777777777
footprint:   676
local score: 253349.77777777778
```

The same replay reproduces checked-in `brackets_11` exactly at public ticks
`[250, 62, 110, 73, 154, 388, 144, 144, 2090]` and local score `276615.0`.
Therefore `gpt_brackets_13` is 8.410687% better locally.

This is a local measurement, not a live score. The repository records the
accepted server score for `brackets_11` as 484,532.65. Applying the local ratio
would be only a projection, so no projected server number is used as evidence.

## Solver-guided component frontier

The preceding exact endpoint solve proved the two short room0/room2 gap pipes
were already at the absolute two-cell minimum. The next variable had to be room
implementation. Two finite body variants were sufficient to reach 26x26.

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

### First physical result: `gpt_brackets_12`

CLOSE's freed right column creates a legal corridor at global column 25. The
OPEN-to-CLASSIFY transport pipe moved from column 26 to 25 and shortened from
49 to 47 cells. This produced the first validated 26x26 candidate:

```text
SHA-256:     8cc306772304f39e21f6b140586844419b55103cec575834228dc9350bc2c4a5
public ticks: [248, 60, 108, 72, 150, 384, 140, 140, 2086]
local score:  254476.44444444444
```

It remains immutable in the repository as lineage.

### Endpoint successor: `gpt_brackets_13`

The exact port model permits the long pipe's source at every non-corner cell on
OPEN's right wall, global rows 17 through 24, while preserving all eight OPEN
send bindings. Row 17 is the highest legal candidate. Moving the source there
and routing through the same column-25 corridor gives:

```text
(17,20) -> (17,25) -> (0,25) -> (0,4)
```

The route falls from 47 to 44 cells. Room bodies, placements, the other five
pipes, logical topology, and footprint do not change. The new source is the
highest binding-preserving cell on this wall, so this same-wall/corridor search
direction is exhausted.

Because pipe reading order changes when the source rises, raw parser pipe
indices 3 and 4 swap. Validation therefore compares operation roles by logical
`(source room, destination room)` rather than by incidental parser index. The
full role-count signature remains unchanged.

## Validation performed

The exact checked-in `gpt_brackets_13` text passed:

- all 9 repository public cases;
- all 9,331 strings over `()[]{}` of length 0 through 5;
- 425 directed cases covering empty input, maximum depth, maximum length,
  every offense position, unclosed stacks, and wrong-type closers;
- 10,000 deterministic random strings, seed `2026072703`, length 0 through 64,
  with generated open count capped at 32.

There were zero failures. Against `brackets_11`, all 10,000 random cases
completed faster:

```text
tick delta distribution:
  -7: 2570 cases
  -6:   86 cases
  -2: 1902 cases
  -1: 5442 cases
mean: -2.7752 ticks
```

Static evidence:

- parser finds five rooms, six pipes, and three men;
- parser-order pipe lengths are `[2, 2, 2, 44, 13, 2]`;
- every pipe has at least two cells;
- dimensions are exactly 26x26;
- no room wall cells are shared;
- exactly one pipe runs against the input room;
- generator output is byte-identical to the artifact;
- exact SHA-256 is pinned above;
- logical pipe-role counts equal `brackets_11`.

The branch contains a focused repository test invoking the project parser,
`alexey_pipecheck`, `server_compat.validate_layout`, exact public judge,
exhaustive short corpus, and deterministic boundary fuzz.

## Independent gate still required

GPT's runtime has GitHub connector access but not the user's native repository
checkout or contest credentials. The simulator replay was reconstructed from
current `sim.py` and checked by reproducing the exact known `brackets_11` public
score, but this is not a substitute for independent checkout replay.

Before any integration into `main` or platform action, Codex or the current
submission controller should:

1. fetch and integrate current `origin/main`;
2. query the exact live Brackets score and latest submission state;
3. run:

```bash
PYTHONPATH=src uv run pytest -q -n 0 tests/test_gpt_brackets_26.py
PYTHONPATH=src uv run python scripts/preflight.py \
  submissions/brackets/gpt_brackets_13.man brackets
```

4. inspect the branch diff and artifact hash;
5. decide independently whether the candidate merits submission.

No platform submission was made by this task.
