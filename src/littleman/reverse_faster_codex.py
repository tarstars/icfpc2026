"""Fourteen-square geometry for the double-extraction Reverse machine.

A three-by-three relay loop replaces the two-by-four predecessor, making the
outer relay five rows high.  The relay can then sit directly below the
nine-row pump while a folded 15-cell ring retains first-pass capacity.

The compact route enters the pump through its left wall instead of its roof,
so ``U`` turns east rather than south.  The pump's lower half is rerouted
without changing the protocol: positive BP values descend to the relay-send
loop, while BP zero takes a two-row output tail and reloads ``B=1`` on the
home climb.
"""

from .canvas import Canvas

PUMP_INTERIOR = [
    "@1M    v",
    "  v-b-r<",
    "vsXrs  ^",
    " v< >1M^",
    ">UmdMr v",
    " ^s<^  s",
    "    ^sW<",
]

RELAY_INTERIOR = [
    "@ v",
    ">sv",
    "^R<",
]

PUMP = (0, 4)
RELAY = (9, 0)
IN_ROOM = (0, 0)
OUT_ROOM = (11, 11)


def _room(interior: list[str]) -> list[str]:
    width = len(interior[0])
    assert all(len(row) == width for row in interior)
    edge = "+" + "-" * width + "+"
    return [edge, *(f"|{row}|" for row in interior), edge]


def build_reverse_faster_codex() -> str:
    canvas = Canvas()
    canvas.put(*PUMP, _room(PUMP_INTERIOR))
    canvas.put(*RELAY, _room(RELAY_INTERIOR))
    canvas.put(*IN_ROOM, ["+-+", "|I|", "+-+"])
    canvas.put(*OUT_ROOM, ["+-+", "|O|", "+-+"])

    # External input has reading-order priority at the relay's R.
    canvas.pipe([(3, 1), (8, 1)])

    # Relay -> pump.  The second cell turns east into the pump's left wall.
    canvas.pipe([(8, 3), (7, 3)])
    canvas.cells[(7, 3)] = ">"

    # Pump -> relay: exactly 15 cells, preserving first-pass capacity.
    canvas.pipe(
        [
            (9, 5),
            (10, 5),
            (10, 9),
            (12, 9),
            (12, 8),
            (11, 8),
            (11, 6),
            (13, 6),
            (13, 5),
        ]
    )

    # Pump -> output: the two-cell minimum.
    canvas.pipe([(9, 12), (10, 12)])
    return canvas.render()
