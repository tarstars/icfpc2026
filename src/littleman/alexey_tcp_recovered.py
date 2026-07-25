"""Reproducible builder for the recovered winning Packet Reassembly program.

``tcp_02.man`` was downloaded from the contest platform after its source was
found to be missing from Git.  This module restores a structural source of
truth: the four active room programs, their placements, and the six routed
pipes are represented separately.  Rendering the builder is byte-identical
to the recovered platform artifact.

The architecture is the final form of Alexey's tag-through-ring design:

* the splitter separates each packet's sequence number and value;
* the pump keeps the 16-slot receive window and emits tagged events;
* the forwarder decodes data/loss tags and recirculates ring slots;
* negative control tags share the data path instead of requiring another
  timing or control pipe.
"""

from .canvas import Canvas


PUMP_INTERIOR = [
    "@`15`b0Mv             ",
    "     >  v  >`2000`NsH ",
    "     ^msd  ^          ",
    "   v    <  ^H         ",
    "   >r-b]]]]aX   r  rNv",
    "            bv   M+1s<",
    "            m         ",
    "            v         ",
    "         > mv         ",
    "         ^srd         ",
    "            r         ",
    "            >   r+brsv",
    "           v         <",
    "           v          ",
    "        > mv          ",
    "        ^srd          ",
    "   ^       <          ",
    "         >1+Mv        ",
    "         ^   r        ",
    "         ^ sNX        ",
    "   ^         <        ",
]

FORWARDER_INTERIOR = [
    "  >M`2000`+X1NsH",
    ">rXv       >WNsv",
    "^ s<           v",
    "^ < s0         <",
    " @^             ",
]

SPLITTER_INTERIOR = [
    " >srs     v",
    " ^        v",
    " ^-`51`Msr<",
    "@r        ^",
]


def _room(interior: list[str]) -> list[str]:
    width = len(interior[0])
    assert all(len(row) == width for row in interior)
    edge = "+" + "-" * width + "+"
    return [edge] + ["|" + row + "|" for row in interior] + [edge]


def build_tcp_recovered_best() -> str:
    """Render the 38x38 program recovered as ``tcp_02.man``."""

    canvas = Canvas()
    canvas.put(0, 0, _room(PUMP_INTERIOR))
    canvas.put(23, 17, ["+-+", "|O|", "+-+"])
    canvas.put(24, 33, ["+-+", "|I|", "+-+"])
    canvas.put(28, 6, _room(FORWARDER_INTERIOR))
    canvas.put(29, 25, _room(SPLITTER_INTERIOR))

    # Pump events to forwarder.
    canvas.pipe([(23, 3), (31, 3), (31, 5)])
    # External input to splitter.
    canvas.pipe([(27, 34), (28, 34)])
    # Forwarder recirculation to the pump, tightly folded above the rooms.
    canvas.pipe(
        [
            (27, 9),
            (26, 9),
            (26, 4),
            (25, 4),
            (25, 14),
            (24, 14),
            (24, 11),
            (23, 11),
        ]
    )
    # Forwarder decoded values to output.
    canvas.pipe([(27, 18), (26, 18)])
    # Splitter sequence numbers to the pump.
    canvas.pipe([(28, 27), (24, 27), (24, 20), (23, 20)])
    # Splitter values to the pump through the long capacity pipe.
    canvas.pipe([(35, 27), (37, 27), (37, 2), (23, 2)])
    return canvas.render()
