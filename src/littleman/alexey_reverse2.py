"""Corridor-free shrinking-ring reverse (candidate reverse_01).

Two changes to the reverse_00 machine, both of which remove whole rows:

1. **Ring size tracked in B instead of `q`.** `q` only counts values that
   have reached the in-pipe, so reverse_00 needed a four-row delay
   corridor to keep in-flight values from being missed. Here the pump
   carries the ring size j in the off hand (B survives r/s/m/d/a and
   digits), so nothing is counted and no corridor is needed. A `r` that
   runs early simply blocks until the value arrives, which costs ticks
   and cannot corrupt the count.

2. **Test-before-relay skip loop.** reverse_00 relayed first and tested
   after, so BP had to be primed to j-2 and j == 1 needed its own
   bypass lane into the take. Testing first (`d` reached before `r s m`)
   relays exactly BP times, so BP = j-1 covers every j including 1, and
   the bypass lane and its merge cell disappear.

Per cycle the pump runs: W b M (BP = j, B = j), `a` (j == 0 leaves for
the input lane), m (BP = j-1), skip loop (relays j-1, rotating the
j-th value to the head), take `r`, emit `s`, then `1 W - M` to leave
A = B = j-1 for the next cycle. Emitting the j-th value of a FIFO after
rotating j-1 of them yields v_n, v_{n-1}, ..., v_1.

The decrement never assumes B survives arithmetic: `-` is followed by an
explicit `M`, so only the cookbook's guaranteed-safe ops carry B.

Bounding box 16x16 -> footprint 256 (reverse_00: 28x24 = 784).
"""

from .canvas import Canvas

# Interior 9 wide x 8 tall.  Column/row numbers below are interior
# coordinates; the room's top-left wall corner sits at canvas (0, 5).
PUMP_INTERIOR = [
    ">rMbm>rsv",  # r1 prologue r M b m then the load loop >rsv
    "     ^ md",  # r2 load-loop return; exits south from `d` at col 9
    " >s1W-M@v",  # r3 emit row: s to output, then 1 W - M leaves A=B=j-1
    "^  a MbW<",  # r4 branch row (westward): W b M then `a`; col1 = input lane
    "   m     ",  # r5 BP = j-1
    "   >   dv",  # r6 skip-loop entry and test; exits east into `v`
    "   ^msr< ",  # r7 skip-loop body (westward): r s m then climb
    " ^     r<",  # r8 take row: `r` takes the rotated head, then climb col 2
]

RELAY = [
    "+----+",
    "|>s@v|",
    "|^r <|",
    "+----+",
]


def _room(interior: list[str]) -> list[str]:
    w = len(interior[0])
    edge = "+" + "-" * w + "+"
    return [edge] + ["|" + row + "|" for row in interior] + [edge]


def build_reverse2() -> str:
    cv = Canvas()
    cv.put(0, 0, ["+-+", "|I|", "+-+"])       # I: rows 0-2, cols 0-2
    cv.put(3, 0, ["+-+", "|O|", "+-+"])       # O: rows 3-5, cols 0-2
    cv.put(0, 5, _room(PUMP_INTERIOR))        # pump: rows 0-9, cols 5-15
    cv.put(12, 9, RELAY)                      # relay: rows 12-15, cols 9-14

    cv.pipe([(1, 3), (1, 4)])                 # I -> pump left wall, row 1
    cv.pipe([(4, 4), (4, 3)])                 # pump left wall -> O
    cv.pipe([(10, 12), (11, 12)])             # ring out: pump bottom -> relay top
    cv.pipe(                                  # ring in: 17 cells, >= n = 16
        # The northward leg stops at col 8: a bend at col 9 would sit on
        # the relay's top-left corner and parse as a second, spurious pipe.
        [(14, 8), (14, 2), (11, 2), (11, 8), (10, 8)]
    )
    return cv.render()
