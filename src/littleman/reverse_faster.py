"""Double-extraction marker-ring machine for reverse-a-list.

Same ring protocol as reverse_fast (frame ``[k, v1..vk]``, input merged
into the ring by a relay with spatial priority), but each pass extracts
the last TWO values: send head k-2, relay k-2 values, fall out of the
relay loop holding v_{k-1} in B (via M), read v_k, print it, W, print
v_{k-1}.  Passes per round halve (n^2/2 -> n^2/4 relays).

Pass branch on A = k-2 at X (heading south): >0 cw=W main path;
==0 straight S: k=2 rides the fall column through a BP-zeroing ``m``,
reusing U, d and the tail (no head sent, ring left empty); <0 ccw=E:
k=1 spur reads v1 and prints (head 1 was left by the last odd pass).
Head 0 is never sent, so the idle ``r`` is the only between-rounds
parking spot.  B=1 is reloaded on the climb home (``1``/``M``).
"""

from .canvas import Canvas

PUMP_INTERIOR = [
    "@1M    v",
    "  v-b-r<",
    "vsXrs  ^",
    "  m    M",
    ">mU    1",
    "^sd    s",
    "  >MrsW^",
]

RELAY_INTERIOR = [
    "@v",
    "v<",
    "Rs",
    ">^",
]


def _room(interior: list[str]) -> list[str]:
    width = len(interior[0])
    top = "+" + "-" * width + "+"
    return [top] + [f"|{row}|" for row in interior] + [top]


# ------------------------------------------------------------------ layout
PUMP = (1, 5)  # top-left corner of the 10x9 pump room
RELAY = (0, 0)  # top-left corner of the 4x6 relay room
IN_ROOM = (12, 0)
OUT_ROOM = (12, 10)
RING_OUT_COL = 2  # pump interior column of the ring-out pipe (floor)
OUTPUT_COL = 6  # pump interior column of the output pipe (floor)
RING_IN_COL = 3  # pump interior column where ring-in drops through the roof


def build_reverse_faster() -> str:
    canvas = Canvas()
    canvas.put(*PUMP, _room(PUMP_INTERIOR))
    canvas.put(*RELAY, _room(RELAY_INTERIOR))
    canvas.put(*IN_ROOM, ["+-+", "|I|", "+-+"])
    canvas.put(*OUT_ROOM, ["+-+", "|O|", "+-+"])

    pr, pc = PUMP
    rr, rc = RELAY

    # input: I room (SW corner) top wall -> relay floor col 1 (sorts before
    # ring-out's col 3 terminal: that gives input spatial priority at `R`).
    canvas.pipe([(IN_ROOM[0] - 1, IN_ROOM[1] + 1), (rr + 6, rc + 1)])

    # ring-in: relay right wall -> along row 0 -> down through pump roof.
    canvas.pipe([(rr + 1, rc + 4), (pr - 1, rc + 4), (pr - 1, pc + RING_IN_COL)])
    canvas.cells[(pr - 1, pc + RING_IN_COL)] = "v"

    # ring-out: pump floor -> swing east of the I room -> climb col 3
    # (clear of both the relay above and the I room in the SW corner) ->
    # relay floor col 3.  Capacity 15 >= head + 14 relays of pass 1.
    canvas.pipe(
        [
            (pr + 9, pc + RING_OUT_COL),
            (13, pc + RING_OUT_COL),
            (13, 5),
            (11, 5),
            (11, 3),
            (rr + 6, rc + 3),
        ]
    )

    # output: pump floor -> O room top wall
    canvas.pipe(
        [
            (pr + 9, pc + OUTPUT_COL),
            (OUT_ROOM[0] - 1, pc + OUTPUT_COL),
        ]
    )
    return canvas.render()
