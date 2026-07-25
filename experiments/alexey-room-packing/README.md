# Room packing experiments (Alexey line)

Working intermediates, **not submissions**. Each is validated 7/7 on memory's
public cases unless noted. The submitted results live in `submissions/`.

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
