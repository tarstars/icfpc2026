# Grade Book

Date: 2026-07-24

## Result

`build_gradebook()` and the preserved
`submissions/gradebook/gradebook_00.man` pass all seven archived public cases
and all 20 live cases.

Final local metrics:

- dimensions: 494×462
- footprint: 244,036
- program size: 224,886 bytes
- SHA-256 of generated text:
  `16a9fe2c71ae917470c16f5021594f4573efc57266e43c399ab1215a96ada522`
- public ticks:
  `[40753, 125295, 131664, 103892, 148646, 68874, 444421]`
- public average ticks: 151,935
- public footprint-tick score: 37,077,609,660
- worst public case: 444,421 ticks, below the 5,000,000 cap

Live result:

- submission: `97526857-55b8-4e83-9ad5-2864afb3a02e`
- status: `done`, 20/20 passed
- server dimensions and footprint: 494×462, 244,036
- server average ticks: 508,628.7
- server score: 124,123,713,433.2
- load/runtime error: none

## Architecture

The parser normalizes every operation to four values `(op, id, subject,
value)` and broadcasts the stream to four subject workers. Roster records are
similarly padded to `(id, g1, g2, g3, g4)`.

Each worker owns a pipe ring containing:

```text
-N, id1, grade1, id2, grade2, ..., idN, gradeN
```

Only the matching subject worker executes an operation. The others drain the
normalized command and wait. GET and SET scan for an ID, AVG accumulates the
selected ring, and TOP maximizes:

```text
(grade + 1) * 10000 - id
```

This key selects the highest grade and then the smallest ID. TOP uses the
native multiply instruction and a short state-pipe schedule to retain the
candidate ID and previous best key.

Acknowledgements form a chain `worker 1 -> 2 -> 3 -> 4 -> parser`. This proves
all four workers have completed while giving the parser only one ack pipe,
kept spatially distinct from contest input. A separate collector merges the
four result pipes into the sole output pipe.

## Generated geometry

The implementation includes a small finite-state-room compiler. Its relevant
compactions are:

- variable-height bands: two rows for goto, three for backpack branch, and
  four for sign branch;
- interval-colored vertical edge tracks;
- shared tracks for edges converging on the same target from the same
  direction;
- local target entries rather than returning every edge to the room's far
  left;
- compact pipe-selection zones and tightly packed worker allocations.

The initial spacious reference layout was 2,744 on its dominant dimension,
for footprint 7,529,536. The final generator reduces the footprint by about
96.8%.

## Validation

- `Machine.parse(build_gradebook())` finds 16 rooms and 30 pipes.
- `gradebook_00.man` exactly matches `build_gradebook()`.
- The full archived judge passes 7/7 public cases.
- The live judge passes 20/20 private and public cases.
- `uv run pytest -q` passes all 78 repository tests.
- `git diff --check` passes.

The simulator's pipe shifting was changed from scanning every pipe cell on
every tick to tracking occupied cells. Existing pipe, display, literal,
memory, and integration tests cover the preserved semantics.
