"""Generator for the Memory problem's pipeline machine.

Architecture (one man per room, every room a racetrack loop):

  I -> P2 (parse; k=(addr-h)%100) -> cmd chain -> P3W -> P3R
       P2 -> P4 (addr) -> newh=(addr+1)%100 -> back to P2 (h loop)
  RING: RELAY(init 100 zeros) -> serpentine -> P3W -> P3R -> RELAY

Command encoding on the chain: count k >= 0 means "act here",
-(k+1) means "just relay k+1 ring values through". The involution
f(x) = -(x+1) (bitwise NOT) maps one encoding to the other, so P3W's
entry row `M 1 + N s` forwards the correct command to P3R for both
READ and WRITE without branching.

The loop idiom `> r s v / ^ _ m d` relays exactly BP+1 values and
exits (below d) with the last relayed value still in A.

Per op with head pointer h, k = (addr - h) % 100:
  READ:  P2 -> P3W: -(k+1)  (P3W relays k+1, forwards k)
         P3R active: BP=k, relay k+1, exit A=mem[addr], s to output.
  WRITE: P2 -> P3W: k, value (P3W: BP=k-1 relays k, then r W s
         replaces the target; k=0 uses an inline stub; forwards -(k+1))
         P3R passive: N b m -> BP=k, relay k+1.
"""

from .canvas import Canvas

# interior cols 1-36; attachments: input LEFT row3, H-in RIGHT row3,
# to-P4 RIGHT row1, cmd BOTTOM col10.
P2 = [
    "+------------------------------------+",
    "|>@rXrM                srv           |",
    "|^   sN+1M%W`001`MN-     <           |",
    "|   >rM                     srv      |",
    "|^               srs%W`001`MN-<      |",
    "+------------------------------------+",
]

# interior rows 1-9, cols 1-20; attachments: cmd-in LEFT row3,
# ring-in BOTTOM col18, cmd-fwd BOTTOM col2, ring-out BOTTOM col16.
P3W = [
    "+--------------------+",
    "|     >     >rsv     |",
    "|     ^mbN< ^ md     |",
    "|>@rM1+NsWXrMrW s   v|",
    "|    vMrmb<          |",
    "|    >          v    |",
    "|               >rsv |",
    "|               ^ md |",
    "|^              sWr< |",
    "|^             <    <|",
    "+--------------------+",
]

# interior rows 1-6, cols 1-11; attachments: cmd-in TOP col2,
# ring-in TOP col9, ring-out BOTTOM col10, output LEFT row5.
P3R = [
    "+-----------+",
    "|   >Nbm>rsv|",
    "|>@rXv  ^ md|",
    "|   >>b>rsv |",
    "|      ^ md |",
    "|^ s      < |",
    "|^         <|",
    "+-----------+",
]

# interior rows 1-3, cols 1-17; in LEFT row2, out BOTTOM col14.
P4 = [
    "+-----------------+",
    "| @0s          v  |",
    "|>rM1+M`100`W%sv  |",
    "|^             <  |",
    "+-----------------+",
]

# interior rows 1-4, cols 1-10; in LEFT row4, out RIGHT row3.
RELAY = [
    "+----------+",
    "|@`99`b0>sv|",
    "|       ^md|",
    "|       >sv|",
    "|       ^r<|",
    "+----------+",
]


def build_newh_room() -> list:
    return P4


def build_relay_init_room() -> list:
    return RELAY


def build_memory() -> str:
    cv = Canvas()
    cv.put(2, 0, ["+-+", "|I|", "+-+"])          # I: rows 2-4, cols 0-2
    cv.put(0, 6, P2)                              # rows 0-5, cols 6-43
    cv.put(0, 48, P4)                             # rows 0-4, cols 48-66
    cv.put(8, 6, P3W)                             # rows 8-18, cols 6-27
    cv.put(22, 6, P3R)                            # rows 22-29, cols 6-18
    cv.put(26, 0, ["+-+", "|O|", "+-+"])          # O: rows 26-28
    cv.put(32, 6, RELAY)                          # rows 32-37, cols 6-17

    cv.pipe([(3, 3), (3, 5)])                     # I -> P2 left row3
    cv.pipe([(1, 44), (1, 46), (2, 46), (2, 47)])  # P2 right row1 -> P4 left row2
    cv.pipe([(5, 62), (6, 62), (6, 45), (3, 45), (3, 44)])  # P4 newh -> P2 right row3
    cv.pipe([(6, 16), (7, 16), (7, 3), (11, 3), (11, 5)])   # P2 cmd -> P3W left row3
    cv.pipe([(19, 8), (21, 8)])                   # P3W cmd-fwd -> P3R top col8
    cv.pipe([(19, 22), (20, 22), (20, 15), (21, 15)])  # P3W ring-out -> P3R top col15
    cv.pipe([(27, 5), (27, 3)])                   # P3R output -> O
    cv.pipe([(30, 16), (31, 16), (31, 3), (36, 3), (36, 5)])  # P3R ring -> RELAY left row4
    # RELAY -> serpentine (ring storage, >100 cells) -> P3W bottom col24
    cv.pipe(
        [
            (35, 18), (35, 30), (21, 30), (21, 32), (35, 32), (35, 34),
            (21, 34), (21, 36), (35, 36), (35, 38), (21, 38), (20, 38),
            (20, 24), (19, 24),
        ]
    )
    return cv.render()


def build_memory_compact() -> str:
    """memory_01: geometry-only compaction. Identical logic; P4 relocated
    from the top-right (cols 48-66, the sole cause of width 67) to the
    bottom, its two P2<->P4 pipes wrapped up the empty right side. Brings
    the bounding box from 67x38 (footprint 4489) toward ~47x47."""
    cv = Canvas()
    cv.put(2, 0, ["+-+", "|I|", "+-+"])
    cv.put(0, 6, P2)
    cv.put(8, 6, P3W)
    cv.put(22, 6, P3R)
    cv.put(26, 0, ["+-+", "|O|", "+-+"])
    cv.put(32, 6, RELAY)
    cv.put(39, 6, P4)                              # MOVED: rows 39-43, cols 6-24

    cv.pipe([(3, 3), (3, 5)])
    cv.pipe([(6, 16), (7, 16), (7, 3), (11, 3), (11, 5)])
    cv.pipe([(19, 8), (21, 8)])
    cv.pipe([(19, 22), (20, 22), (20, 15), (21, 15)])
    cv.pipe([(27, 5), (27, 3)])
    cv.pipe([(30, 16), (31, 16), (31, 3), (36, 3), (36, 5)])
    cv.pipe(
        [
            (35, 18), (35, 30), (21, 30), (21, 32), (35, 32), (35, 34),
            (21, 34), (21, 36), (35, 36), (35, 38), (21, 38), (20, 38),
            (20, 24), (19, 24),
        ]
    )
    # P2 right row1 -> wrap down col45, under, up to P4 left row2.
    # Row 46 is deliberately below the return pipe's row 45 corridor.
    cv.pipe([(1, 44), (1, 45), (46, 45), (46, 5), (41, 5)])
    cv.cells[(41, 5)] = ">"                        # terminal bend into P4 left
    # P4 out bottom col14 -> approach P2 right row3 from below on col44.
    # This stays disjoint from the other wrap pipe's col45 corridor.
    cv.pipe([(44, 20), (45, 20), (45, 44), (3, 44)])
    cv.cells[(3, 44)] = "<"                        # terminal bend into P2
    return cv.render()
