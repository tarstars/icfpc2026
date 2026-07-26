"""14x14 double-extraction ring machine for reverse-a-list (reverse_06).

Descendant of tarstars' ``reverse_faster`` (reverse_05, 15x15, live
117,214).  Same protocol -- frame ``[k, v1..vk]`` circulating through a
relay that merges input with spatial priority, each pass extracting the
last TWO values -- but the pump room is re-laid from 8x7 interior down to
7x6, which takes the whole program from 15x15 (fp 225) to 14x14 (fp 196).

Three changes buy the row and the column:

1. **The head send moved inside the relay loop.**  The loop is
   ``> s U / ^ m d`` walked as ``> s U d m ^``: it SENDS what is already
   in A, then READS the next value.  Entered with A = k-2 (the new head)
   and BP = k-2, lap j sends value j-1 (lap 1 sends the head), reads
   value j and exits at lap k-1 holding v_{k-1}.  That is exactly
   ``head + v1..v_{k-2}`` sent and ``v1..v_{k-1}`` read, so reverse_05's
   separate head-``s`` cell and its whole approach lane disappear.

2. **BP is loaded with k-2 instead of k-1**, so the ``k == 2`` branch
   needs no BP fixup: X's straight-south arm drops directly onto the
   loop's ``U`` (X sits one row above it, in the same column) and ``d``
   falls through on BP = 0 into the shared tail.  reverse_05 spent a
   whole column on that fall lane plus a zeroing ``m``.

3. **The constant is 2, not 1**, so one ``-`` replaces ``-b-``.  It is
   reloaded on the climb home (``2`` then ``M`` on the head row).

Interior, 7 wide x 6 tall (@ is a nop the boot walk crosses on its way
to the climb column):

        c0 c1 c2 c3 c4 c5 c6
    r0   .  .  v  -  r  M  <     head row, walked WEST: B=2, A=k, A=k-2
    r1   .  .  b  .  .  .  2     BP = k-2 ; climb reloads A=2
    r2   v  .  X  r  s  @  ^     three-way branch ; k==1 spur (r, print)
    r3   >  s  U  .  .  .  s     loop top ; climb prints v_{k-1}
    r4   ^  m  d  .  .  .  W     loop bottom ; climb swaps
    r5   .  .  >  M  r  s  ^     tail: hold v_{k-1}, read+print v_k

Pipe resolution (pump floor row 9: ring-out at col 7, output at col 11):
the loop's ``s`` at (5,7) is 4 from the ring and 8 from the output; the
three printing ``s`` at (4,10), (5,12) and (7,11) are all nearer the
output.  The pump has a single incoming pipe, so every ``r``/``U`` takes
the ring and ``U`` always turns south (the ring drops through the roof).

The return pipe climbs column 4, not column 3: column 3 would run flush
past the input room's right wall, and the server counts a pipe merely
passing an INPUT room's wall as a second connection and rejects the
program (rule discovered by tarstars, see ``server_compat``).
"""

from .canvas import Canvas

PUMP_INTERIOR = [
    "  v-rM<",
    "  b   2",
    "v Xrs@^",
    ">sU   s",
    "^md   W",
    "  >Mrs^",
]

RELAY_INTERIOR = [
    "@v",
    "v<",
    "Rs",
    ">^",
]

PUMP = (1, 5)  # 9x8 room: rows 1-8, cols 5-13
RELAY = (0, 0)  # 4x6 room: rows 0-5, cols 0-3
IN_ROOM = (11, 0)
OUT_ROOM = (11, 10)

RING_IN_COL = 3  # pump column offset where the ring drops through the roof
RING_OUT_COL = 2  # pump column offset of the ring-out pipe on the floor
OUTPUT_COL = 6  # pump column offset of the output pipe on the floor


def _room(interior: list[str]) -> list[str]:
    width = len(interior[0])
    edge = "+" + "-" * width + "+"
    return [edge] + [f"|{row}|" for row in interior] + [edge]


def build_reverse6() -> str:
    canvas = Canvas()
    canvas.put(*PUMP, _room(PUMP_INTERIOR))
    canvas.put(*RELAY, _room(RELAY_INTERIOR))
    canvas.put(*IN_ROOM, ["+-+", "|I|", "+-+"])
    canvas.put(*OUT_ROOM, ["+-+", "|O|", "+-+"])

    pr, pc = PUMP
    rr, rc = RELAY

    # input: I roof -> relay floor col 1.  Its terminal (6,1) sorts before
    # the ring's (6,2) in reading order, which is what gives input priority
    # at the relay's `R` and keeps the frame in order.
    canvas.pipe([(IN_ROOM[0] - 1, IN_ROOM[1] + 1), (rr + 6, rc + 1)])

    # ring-in: relay right wall -> row 0 -> down through the pump roof.
    canvas.pipe([(rr + 1, rc + 4), (pr - 1, rc + 4), (pr - 1, pc + RING_IN_COL)])
    canvas.cells[(pr - 1, pc + RING_IN_COL)] = "v"

    # ring-out: pump floor -> bottom row -> climb col 4 (clear of the input
    # room) -> relay floor col 2.  17 cells; pass 1 of n=16 parks 15.
    canvas.pipe(
        [
            (pr + 8, pc + RING_OUT_COL),
            (13, pc + RING_OUT_COL),
            (13, 4),
            (9, 4),
            (9, 2),
            (rr + 6, rc + 2),
        ]
    )

    # output: pump floor -> O roof.
    canvas.pipe([(pr + 8, pc + OUTPUT_COL), (OUT_ROOM[0] - 1, pc + OUTPUT_COL)])
    return canvas.render()
