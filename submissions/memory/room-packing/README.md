# Room packing experiments (Alexey line)

Working intermediates, **not submissions**. Each is validated 7/7 on memory's
public cases unless noted. The submitted results live one level up, next to this folder.

The theme: how tightly can rooms be packed without touching any machine logic.
Two server rules set the naive floor — rooms may not share a wall cell, and a
pipe may not be shorter than two cells — which together seem to force a 2-row
gap between stacked rooms. **They do not.**

## The two techniques

**Magnetising (trim + slide).** Trim a room to its content, then slide the
pipes that were attached into the columns the trim freed. They come out
shorter than they started and pull the bounding box in with them. If the trim
flips a read, do not give up: find the one cell whose resolution changed,
write the room's reads as distance inequalities, and solve for a port
position — moving the *port*, never the source room, because an endpoint is
pinned to the wall it enters.

**Herringbone (offset stacking).** Offset the lower room sideways. Its top
wall and the upper room's bottom wall then sit on adjacent rows and share no
cell, which is legal, and the pipe leaves through the resulting overhang into
the lower room's SIDE wall. **Zero gap rows, two-cell pipe.** Alternate the
offset direction down the stack so each room overhangs the other on opposite
sides — that is the herringbone, and it is what keeps a column clear for the
next joint below.

## Files, in order

| file | what it is |
|---|---|
| `alexey-memory-trimmed-top.man` | top room trimmed of six empty columns; needed the `I` port moved to the bottom wall (feasible window: columns 12-24) |
| `alexey-memory-narrow40.man` | right-edge pipes slid into the freed columns: width 46 -> 40, pipes 91->87 and 67->63, i.e. shorter than before the trim |
| `alexey-memory-h33.man` | first herringbone joints on the packed-storage machine: 37x37 -> 36x33 |
| `alexey-memory-zig.man` | herringbone flipped — block 2 left, block 3 right — so column 7 stays clear under block 3 and block 4 can be reached at its own top port. 36x33, 7/7, ticks 4,143.6 |

Note the first two belong to the *older* pipeline-ring memory line, which was
later superseded threefold by the packed-storage machine (`memory_04`). The
techniques carried over; the numbers did not.

## The trap, twice paid for

Moving a room means redrawing **every** pipe attached to it. The tell when you
miss one is that the parsed pipe count silently drops, and the machine then
fails instantly rather than deadlocking. Block 4 has four pipes; that is why
raising it is still open.

## `alexey-memory-zig4.man` — blocks 3 and 4 joined, rows 17-18 gone

The last gap in the chain. Block 4 rises two rows (18-32 -> 16-30, columns
unchanged) and is entered at **its own top port, column 7** — that port cannot
move, because block 4 has two pipes each way. The flipped herringbone is what
makes it reachable: block 3 sits at columns 8-33, so column 7 is clear
underneath it, and block 3's outgoing pipe leaves through its LEFT wall,
drops down column 6 and turns back east into column 7:

    (14,7) < -> (14,6) v -> (15,6) > -> (15,7) v   into block4's top wall at (16,7)

Four cells. Moving that port was safe because all five of block 3's `s` cells
resolve to the same outgoing pipe — checked, not assumed.

**All four of block 4's pipes were redrawn at once**, with a collision assert
on every cell, which is what finally made this work after two failed attempts
at redrawing them piecemeal.

One real catch: the 4->5 pipe came out at 12 cells against its original 26,
and the machine deadlocked. Length is capacity. Padding it back to 28 with a
serpentine in the free columns 29-35 fixed it — 7/7, ticks 4,145.6.

Footprint stays 1,296: the layout is 36x33 and **width binds**. The two rows
this freed are in the middle; the `O` room still holds the bottom at rows
30-32, so it has to follow before the height can actually drop.

## `alexey-memory-zig5.man` — `O` magnetised to block 4

`O` rises two rows (30-32 -> 28-30) and sits against block 4's left wall.
Block 4's exit stays exactly where it was — its left wall, row 29, which it
must, since block 4 has two pipes each way — and the pipe collapses from four
cells to **two**:

    (29,4) < -> (29,3) <   into O's right wall at (29,2)

7/7, ticks 4,143.6. Layout **36 x 32**.

Footprint is still 1,296: width 36 binds against height 32, so every row won
here is banked rather than cashed. What now holds the last row is the 5->4
pipe, whose horizontal run sits on row 31 — block 5's outgoing port is on its
BOTTOM wall, so the pipe is forced one row below the rooms. Block 5 has one
pipe each way, so that port is free to move; but its natural alternative (the
left wall) points straight at block 4's right wall, which would terminate the
pipe at the wrong port. That is the next thing to solve.

### State of the chain

    block1 rows  0-4   cols  5-33
    block2 rows  5-8   cols  3-31    herringbone left
    block3 rows  9-15  cols  8-33    herringbone right
    block4 rows 16-30  cols  5-28    joined, entered at its own top port
    block5 rows 26-29  cols 30-35
    I      rows  1-3   cols  0-2
    O      rows 28-30  cols  0-2     magnetised

    37x37 (memory_04) -> 36x36 (memory_05, submitted) -> 36x33 -> 36x32

## `alexey-memory-zig6.man` — `O` pressed flat against block 4

`O` moves up two more rows and right two columns (30-32/0-2 -> 26-28/2-4), so
its right wall at column 4 now abuts block 4's left wall at column 5 — no cell
shared, which is legal, and no corridor between them at all. Block 4's exit
stays put at its left wall, row 29, and the pipe reaches `O` through the
overhang below it:

    (29,4) < -> (29,3) ^   into O's BOTTOM wall at (28,3)

Two cells. 7/7, ticks 4,143.6, layout 36x32.

This is the herringbone applied sideways: two rooms can touch along a wall as
long as the pipe leaves through a face that overhangs, and `O` could take a
port anywhere because it has one incoming pipe and nothing else.

Columns 0-1 are now free at rows 26-28; only the `I` room (rows 1-3) still
holds them, so the left edge is one repack away from moving in.
