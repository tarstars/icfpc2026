# GPT Brackets 25-square candidate

Date: 2026-07-27

Status: immutable candidate generated and extensively replayed locally; no
platform submission.

## Result

`gpt_brackets_14.man` is a 25x25 successor to accepted `brackets_11` and to the
26-square GPT lineage.

```text
artifact:    submissions/brackets/gpt_brackets_14.man
generator:   littleman.gpt_brackets_25:build_gpt_brackets_14
SHA-256:     9aa12829131b7bd9c4771b4bbfd49eec9fe83374a01fee91227d58ca142b0875
bytes:       630
rooms/pipes/men: 5 / 6 / 3
pipe lengths:    [2, 2, 2, 42, 13, 2]
```

Local exact public replay:

```text
cases:       9 / 9
ticks:       [249, 61, 109, 73, 146, 380, 136, 136, 2083]
average:     374.77777777777777
footprint:   625
local score: 234236.1111111111
```

The same simulator reconstruction reproduces `brackets_11` exactly at local
score `276615.0`. The candidate is therefore 15.320532% better locally. It is
also 7.544379% below `gpt_brackets_13`'s local score.

These are local measurements. The repository records `brackets_11` live at
484,532.65, but applying a local ratio would be a projection rather than a
server result, so no projected server score is reported as evidence.

## Component-frontier step

The 26-square machine was pinned horizontally by CLOSE's 24-column outer box
plus the long transport corridor, and vertically by OPEN's ten-row outer box.
Two more finite body choices remove one dimension each.

### CLOSE outer width 24 -> 23

In `gpt_brackets_13`, the empty-stack output path ended:

```text
row 2: ... r M 1 + v
row 3:               s
row 4:               H
```

The arithmetic prefix has `1` at relative column 20. The 25-square variant
turns down immediately at column 21, executes `+` at row 3, sends at row 4, and
continues into the already-existing terminal `H` at row 5 column 21. The halt is
therefore shared by two semantically terminal paths. No operation to the right
of column 21 remains, so the CLOSE interior falls from 22 to 21 columns and its
outer box from 24 to 23.

### OPEN outer height 10 -> 9

The 26-square OPEN used a dedicated last row for startup:

```text
row 8: @ r ^
```

The new startup is inserted into otherwise unused cells in row 5:

```text
row 5: @ r v       ]
```

It descends through blank row-6 column 3 into the existing `<` at row 7 column
3, walks west to the existing column-1 climb, and rejoins the normal loop. The
ordinary return path later passes through `@` while moving north; `@` is a no-op.
The dedicated last row disappears, reducing OPEN's outer height from 10 to 9.

### Physical consequence

With CLOSE ending at global column 23, the long OPEN-to-CLASSIFY pipe can use
column 24 instead of 25:

```text
(17,20) -> (17,24) -> (0,24) -> (0,4)
```

Its length falls from 44 to 42 cells. The occupied machine box becomes exactly
rows 0..24 and columns 0..24.

No logical pipe roles change. Validation compares each `s`, `r`, and `q` role
by `(operation room, glyph, source room, destination room)`, avoiding incidental
parser-index differences.

## Validation performed

The exact candidate text passed:

- all 9 repository public cases;
- all 9,331 strings over `()[]{}` of length 0 through 5;
- 425 directed cases covering empty input, maximum depth, maximum length,
  every offense position, unclosed stacks, and wrong-type closers;
- 10,000 deterministic random strings, seed `2026072704`, length 0 through 64,
  with generated open count capped at 32.

There were zero failures. Against `brackets_11`, the random tick deltas were:

```text
 -8: 1440 cases
 -7: 1169 cases
 -6:   17 cases
 -5:   61 cases
 -1: 1972 cases
  0: 5341 cases
mean: -2.2082 ticks
```

Static evidence:

- parser finds five rooms, six pipes, and three men;
- parser-order pipe lengths are `[2, 2, 2, 42, 13, 2]`;
- every pipe has at least two cells;
- dimensions are exactly 25x25;
- no room wall cells are shared;
- exactly one pipe runs against the input room;
- CLOSE outer width is 23 and OPEN outer height is 9;
- generator output is byte-identical to the artifact;
- exact SHA-256 is pinned above;
- logical pipe-role counts equal `brackets_11`.

## Independent gate still required

GPT's runtime has GitHub connector access but not the native repository checkout
or contest credentials. Before integration or any platform action, Codex or the
current submission controller should:

1. fetch and integrate current `origin/main`;
2. query the exact live Brackets score and latest submission;
3. run:

```bash
PYTHONPATH=src uv run pytest -q -n 0 tests/test_gpt_brackets_25.py
PYTHONPATH=src uv run python scripts/preflight.py \
  submissions/brackets/gpt_brackets_14.man brackets
```

4. inspect the branch diff and verify the pinned artifact hash;
5. decide independently whether the candidate merits platform submission.

No platform mutation was made by this task.
