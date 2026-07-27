# GPT Brackets 25-square candidates

Date: 2026-07-27

Status: two immutable candidates generated and extensively replayed locally;
no platform submission.

## Best result

`gpt_brackets_15.man` is a 25x25 successor to accepted `brackets_11`, the
26-square GPT lineage, and `gpt_brackets_14`.

```text
artifact:    submissions/brackets/gpt_brackets_15.man
generator:   littleman.gpt_brackets_25:build_gpt_brackets_15
SHA-256:     826553c4a58fd1ef83f81e8b05e9c3d54b575f2030d89c566cd5d9a99c09e605
bytes:       630
rooms/pipes/men: 5 / 6 / 3
pipe lengths:    [2, 2, 2, 10, 42, 2]
```

Local exact public replay:

```text
cases:       9 / 9
ticks:       [246, 58, 106, 70, 146, 380, 136, 136, 2082]
average:     373.3333333333333
footprint:   625
local score: 233333.3333333333
```

The same simulator reconstruction reproduces `brackets_11` exactly at local
score `276615.0`. The best candidate is therefore 15.646898% better locally.

These are local measurements. The repository records `brackets_11` live at
484,532.65, but applying a local ratio would be a projection rather than a
server result, so no projected server score is reported as evidence.

## Component-frontier step to 25x25

The 26-square machine was pinned horizontally by CLOSE's 24-column outer box
plus the long transport corridor, and vertically by OPEN's ten-row outer box.
Two finite body choices remove one dimension each.

### CLOSE outer width 24 -> 23

The empty-stack output path turns down at relative column 21, executes `+` at
row 3, sends at row 4, and continues into the already-existing terminal `H` at
row 5 column 21. The halt is shared by two terminal paths. No operation to the
right remains, so the CLOSE outer box falls from 24 to 23 columns.

### OPEN outer height 10 -> 9

Startup moves into otherwise unused cells in row 5 as `@ r v`, descends through
a blank row-6 cell, and enters the existing `<` at row 7 column 3. It then uses
the ordinary westbound return and column-1 climb. The dedicated last startup
row disappears.

### Long transport corridor

With CLOSE ending at global column 23, the OPEN-to-CLASSIFY pipe uses column 24:

```text
(17,20) -> (17,24) -> (0,24) -> (0,4)
```

The pipe falls from 44 to 42 cells. The occupied box becomes rows 0..24 and
columns 0..24. This first result is preserved as immutable
`gpt_brackets_14.man`, SHA-256
`9aa12829131b7bd9c4771b4bbfd49eec9fe83374a01fee91227d58ca142b0875`.

## Endpoint successor: state transport 13 -> 10

The remaining nonminimal external route in `gpt_brackets_14` was the
OPEN-to-CLOSE state pipe. Exact same-wall enumeration shows OPEN's state sends
continue to select that pipe for every left-wall source from global rows 17
through 22. Row 17 is the highest legal endpoint and gives:

```text
(17,3) -> (17,0) -> (11,0)
```

The endpoint Manhattan distance plus one is ten, exactly the routed cell count.
Thus the selected route reaches its geometric lower bound. It replaces the
13-cell route without changing any room body, placement, other pipe, logical
pipe topology, or footprint.

All remaining five external routes are either two-cell server-minimum pipes or
the fixed-obstacle shortest long corridor in this placement. Endpoint-only
optimization of the 25-square layout is therefore exhausted; further gains
require another room/body or placement choice.

## Validation performed

The exact checked-in `gpt_brackets_15` text passed:

- all 9 repository public cases;
- all 9,331 strings over `()[]{}` of length 0 through 5;
- 425 directed cases covering empty input, maximum depth, maximum length,
  every offense position, unclosed stacks, and wrong-type closers;
- 10,000 deterministic random strings, seed `2026072705`, length 0 through 64,
  with generated open count capped at 32.

There were zero failures. Against `brackets_11`, every random case completed
three to eight ticks faster:

```text
 -8: 2670 cases
 -7:   52 cases
 -4: 1879 cases
 -3: 5399 cases
mean: -4.5437 ticks
```

Static evidence:

- parser finds five rooms, six pipes, and three men;
- parser-order pipe lengths are `[2, 2, 2, 10, 42, 2]`;
- every pipe has at least two cells;
- dimensions are exactly 25x25;
- no room wall cells are shared;
- exactly one pipe runs against the input room;
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
  submissions/brackets/gpt_brackets_15.man brackets
```

4. inspect the branch diff and verify the pinned artifact hash;
5. decide independently whether the candidate merits platform submission.

No platform mutation was made by this task.
