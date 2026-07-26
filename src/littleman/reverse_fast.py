"""Marker-ring machine for reverse-a-list.

Two rooms form one ring.  The RELAY room merges the input pipe and the
pump's ring-out pipe into a single ring-in pipe, always preferring input
(its destination cell sorts first in reading order), so a whole round's
tokens enter the ring ahead of anything the pump re-sends.

The ring therefore always carries ``[k, v1 .. vk]`` -- a self-describing
frame whose head is the count of values still to print.  One pass of the
pump reads the head k, re-sends k-1 as the next head, relays k-1 values
back into the ring and prints the k-th.  No delay corridor, no ``q``, no
separate load phase: pass 1 consumes the round's own input straight out
of the ring, and the frame [0] left behind ends the round.

Pump registers: B = 1 (constant, for the head decrement), BP = the pass
counter, A = the token in hand.

Pump interior map (rel rows 1..6, cols 1..6)::

    va-br<     r b - : read head k, BP = k, A = k-1
     s         a     : BP>0 -> head south to the marker send
     >mU       s     : send the new head k-1 into the ring
     ^sd M     >mU   : m = BP-1, U reads a value (ring-in is on the
       s 1             top wall, so U always faces the man south)
    > @> ^     d     : BP>0 -> relay west; BP==0 -> fall to the printer
                s    : relay the value back into the ring
                s    : (row 5) print the value into the output pipe
                1 M  : reload B = 1 on every lap back to the head

``s`` picks the nearest outgoing pipe, so the ring-out and output pipes
leave the bottom wall under interior columns 2 and 5: that puts ring-out
strictly nearer to both ring sends and output strictly nearer to the
printer.
"""

from .canvas import Canvas

PUMP_INTERIOR = [
    "va-br<",
    " s    ",
    " >mU  ",
    " ^sd M",
    "   s 1",
    "> @> ^",
]

RELAY_INTERIOR = [
    "@v",
    "v<",
    "Rs",
    ">^",
]

RING_OUT_COL = 2  # interior column of the ring-out pipe on the pump's floor
OUTPUT_COL = 5  # interior column of the output pipe on the pump's floor


def _room(interior: list[str]) -> list[str]:
    width = len(interior[0])
    top = "+" + "-" * width + "+"
    return [top] + [f"|{row}|" for row in interior] + [top]


# ------------------------------------------------------------------ layout
PUMP = (1, 6)  # top-left corner of the 8x8 pump room
RELAY = (0, 0)  # top-left corner of the 6x4 relay room
IN_ROOM = (8, 0)
OUT_ROOM = (11, 10)


def build_reverse_fast() -> str:
    canvas = Canvas()
    canvas.put(*PUMP, _room(PUMP_INTERIOR))
    canvas.put(*RELAY, _room(RELAY_INTERIOR))
    canvas.put(*IN_ROOM, ["+-+", "|I|", "+-+"])
    canvas.put(*OUT_ROOM, ["+-+", "|O|", "+-+"])

    pr, pc = PUMP
    rr, rc = RELAY

    # input: I room top wall -> relay floor, interior column 1.  Its
    # destination cell sorts first, which is what gives input priority in
    # the relay's `R`.
    canvas.pipe([(IN_ROOM[0] - 1, IN_ROOM[1] + 1), (rr + 6, rc + 1)])

    # ring-in: relay left wall -> pump top wall.  Entering from the top is
    # what makes `U` face the pump man south.
    canvas.pipe([(rr + 1, rc + 4), (pr - 1, rc + 4), (pr - 1, pc + 2)])
    canvas.cells[(pr - 1, pc + 2)] = "v"  # terminal bend into the pump roof

    # ring-out: pump floor -> relay floor.  The long way round: it must
    # hold a whole 16-value round while the relay is still busy draining
    # input.
    #
    # It climbs column rc+4 and enters the relay's bottom-right corner.
    # The obvious shorter climb up column rc+3 runs flush along the input
    # room's right wall, and the server counts a pipe merely passing
    # alongside an I/O room as connected to it -- that rejected
    # reverse_03.man outright.  Column rc+4 keeps a full cell of clearance
    # from the input room, and the last two cells cut across at row 7,
    # above the input room's roof.
    canvas.pipe(
        [
            (pr + 8, pc + RING_OUT_COL),
            (13, pc + RING_OUT_COL),
            (13, rc + 4),
            (7, rc + 4),
            (7, rc + 3),
            (rr + 6, rc + 3),
        ]
    )

    # output: pump right wall -> O room top wall
    canvas.pipe(
        [
            (pr + 8, pc + OUTPUT_COL),
            (OUT_ROOM[0] - 1, pc + OUTPUT_COL),
        ]
    )
    return canvas.render()
