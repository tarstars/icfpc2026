# chatgpt_1 Brackets 22-square macro frontier

This experiment preserves the first reproducible checkpoint for the exact
22x22 Brackets assignment. It does **not** claim a valid `.man`.

The accepted starting point is `gpt_brackets_17`, a 24x24 machine with five
rooms and six pipes. Its nontrivial component rectangles, walls included, are:

```text
CLOSE      22x7
CLASSIFY   16x6
OPEN       18x8
INPUT       3x3
OUTPUT      3x3
```

Those rooms occupy 412 of 484 cells in a 22-square, leaving 72 cells for six
pipes. The accepted parent uses 53 pipe cells, so the raw area budget leaves
only 19 cells of slack.

## Run

```bash
cd experiments/chatgpt1-brackets-22
python3 macro_frontier.py --output /tmp/brackets22-macro.json
diff -u macro_frontier.json /tmp/brackets22-macro.json
```

The script uses only the Python standard library.

## Enumerated family

Because CLOSE is already 22 cells wide, it is fixed against the top or bottom
edge. OPEN and CLASSIFY are stacked in the remaining 15 rows with exactly one
routing row between them. INPUT and OUTPUT are placed in the remaining 3x3
pockets.

The checkpoint enumerates:

```text
stack-family room packings examined: 25,764
packings passing safe-port necessary conditions: 1,700
```

A safe endpoint cell is one cell outside a non-corner wall cell, inside the
22x22 canvas, outside every room, and adjacent to exactly one room wall. This
last condition rejects an immediate phantom attach to an unrelated room.

The best independent Manhattan lower-bound seed is:

```text
CLOSE     origin (15, 0)
OPEN      origin ( 0, 3)
CLASSIFY  origin ( 9, 0)
INPUT     origin ( 0, 0)
OUTPUT    origin (10,17)

per-net inclusive lower bounds:
CLASSIFY -> CLOSE      3
CLOSE -> CLASSIFY      3
CLOSE -> OUTPUT        2
OPEN -> CLOSE          7
OPEN -> CLASSIFY       3
INPUT -> OPEN          3
sum                     21
```

This seed is a placement target for the next router, not a candidate program.

## What remains

The model intentionally omits constraints that only the next stage can prove:

- endpoint cells must be globally unique across all six nets;
- every `s`, `r`, and `q` must retain its exact named nearest-pipe binding;
- all six directed paths must be vertex-disjoint;
- rendering must parse as exactly five rooms and six intended pipes;
- no pipe may graze the input room or create a phantom attachment;
- the corrected simulator, organizers' WASM, and `subdb compare` must pass.

The parser must be in the loop. The earlier 23-square lineage produced an
abstractly legal route that rendered as an unintended seventh pipe.
