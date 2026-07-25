"""Selection-sort ring with an in-band remaining-count token.

The accepted ``sort_03`` asks ``q`` for the number of parked values before
every selection pass. Because ``q`` cannot see values still in flight, the
walker traverses a three-row settling corridor before asking again.

This variant removes that timing protocol. The round's count circulates in
the FIFO behind the values being scanned:

* load ``n`` values into the ring while retaining ``n`` in B;
* enter the common pass handler with A = n;
* send ``n - 1`` behind the current values and scan exactly n values;
* requeue every value except the selected minimum;
* after the scan, the count token is at the FIFO head, ready for the next
  pass; zero returns to the input reader.

Blocking receive supplies all required synchronization. No ``q`` or settling
corridor remains. This is the same in-band-control principle recovered from
the winning Packet Reassembly design.
"""

from .canvas import Canvas


PUMP_INTERIOR = [
    ">@rMbm>rsv  ",  # load n into B/BP, then stream values to the ring
    "      ^ md  ",  # load-loop return; BP=0 exits downward at d
    "      vbW<  ",  # initial pass: restore n from B and set BP=n
    "      >v    ",  # join the common pass handler
    "^   a  < br<",  # count read; zero returns home, positive turns down
    "    >M1W-sv ",  # send count-1 behind the values
    "va   Mrm< < ",  # take first value as minimum; BP=count-1
    "    >+Wsv   ",  # smaller value: requeue old minimum
    " >r-Xv      ",  # compare next value with current minimum
    "    >>+sv   ",  # larger/equal value: restore and requeue it
    "vd   m  <   ",  # scan exactly BP remaining values
    ">Ws        ^",  # emit minimum, then climb to the count handler
]


RELAY = [
    "+----+",
    "|>s@v|",
    "|^r <|",
    "+----+",
]


def _room(interior: list[str]) -> list[str]:
    width = len(interior[0])
    assert all(len(row) == width for row in interior)
    edge = "+" + "-" * width + "+"
    return [edge] + ["|" + row + "|" for row in interior] + [edge]


def build_sort_count_token() -> str:
    canvas = Canvas()
    canvas.put(0, 0, ["+-+", "|I|", "+-+"])
    canvas.put(0, 4, _room(PUMP_INTERIOR))
    canvas.put(14, 0, ["+-+", "|O|", "+-+"])
    canvas.put(14, 12, RELAY)

    # The one-cell I -> pump pipe is legal: its arrow's backward cell is the
    # I wall and its forward cell is the pump wall.
    canvas.cells[(1, 3)] = ">"

    # The output and ring-out pipes leave separate bottom-wall ports.
    canvas.pipe([(14, 7), (15, 7), (15, 3)])
    canvas.pipe([(14, 10), (15, 10), (15, 11)])
    canvas.cells[(15, 11)] = ">"

    # Fold the return FIFO into the otherwise empty shelf under the pump.
    # Its bottom-wall attachment keeps every ring `r` closer to this pipe
    # than to the input pipe; nearest-pipe selection is part of the language.
    # The fold also keeps the complete machine inside an 18x18 square.
    canvas.pipe(
        [(16, 11), (16, 10), (17, 10), (17, 4), (16, 4), (16, 9), (14, 9)]
    )
    return canvas.render()
