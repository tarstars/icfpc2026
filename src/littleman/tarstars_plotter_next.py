"""A 125-square successor to the fused Plotter racetrack.

The live ``plotter_08`` worker is 125 rows high.  Its basic blocks are
semantically named and linked, so moving ``start`` to the end is geometry
only and exposes one additional legal staircase merge.  The resulting worker
is 123 rows high with the same protocol.

One row remains above the worker, while its two outgoing ports move to
opposite side walls.  The retained rooms from ``plotter_08`` are packed into
the west band, with DISPLAY lifted one row so its bottom input stays inside
the 125-square bounding box.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from .alexey_squeeze import squeeze
from .alexey_stairfold import fold_room
from .canvas import Canvas
from .gradebook import compile_fsm
from .matmul import RELAY
from .plotter_racetrack import FUSED_COMPACT_PORTS, FUSED_ZONES
from .plotter_racetrack import build_fused_plotter_fsm
from .sim import Machine

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "submissions" / "plotter" / "plotter_08.man"
SOURCE_SHA256 = "1614d73921d512f321cb1a1a10660e75258c1ae0346f2b77bd51207be3e5c3dd"
ARTIFACT = REPO / "submissions" / "plotter" / "tarstars_plotter_09.man"


def _reordered_fsm():
    fsm = build_fused_plotter_fsm()

    start = fsm.blocks.pop(0)
    fsm.blocks.append(start)
    return fsm


def build_reordered_fused_harness() -> str:
    """Return a judgeable harness for the reordered fused worker."""

    worker = compile_fsm(_reordered_fsm(), FUSED_ZONES, right_padding=0)
    canvas = Canvas()
    top, left = 5, 10
    canvas.put(top, left, worker.rows)
    setup_x = left + worker.zones["setup"]
    ring_in_x = left + worker.zones["ring_in"]
    output_x = left + worker.zones["output"]
    ring_out_x = left + worker.zones["ring_out"]
    bottom = top + len(worker.rows) - 1

    canvas.put(0, setup_x - 1, ["+-+", "|I|", "+-+"])
    canvas.pipe([(3, setup_x), (top - 1, setup_x)])
    output_top = bottom + 3
    canvas.put(output_top, output_x - 1, ["+-+", "|O|", "+-+"])
    canvas.pipe([(bottom + 1, output_x), (output_top - 1, output_x)])

    relay_top = bottom + 9
    relay_left = left + worker.width + 8
    canvas.put(relay_top, relay_left, RELAY)
    canvas.pipe(
        [
            (bottom + 1, ring_out_x),
            (relay_top + 3, ring_out_x),
            (relay_top + 3, relay_left - 1),
        ]
    )
    canvas.pipe(
        [
            (relay_top + 2, relay_left - 1),
            (relay_top + 2, left + worker.width + 3),
            (top - 3, left + worker.width + 3),
            (top - 3, ring_in_x),
            (top - 1, ring_in_x),
        ]
    )
    return canvas.render()


def build_reordered_fused_room() -> list[str]:
    """Return the folded and squeezed 26x123 worker rectangle."""

    folded, rows_freed = fold_room(build_reordered_fused_harness(), 1)
    if rows_freed != 78:
        raise ValueError(f"expected 78 folded worker rows, got {rows_freed}")
    compact, rows_dropped, columns_dropped = squeeze(
        folded,
        rows=True,
        cols=True,
    )
    if (rows_dropped, columns_dropped) != (85, 33):
        raise ValueError(
            f"unexpected reordered-worker squeeze "
            f"{(rows_dropped, columns_dropped)}"
        )

    machine = Machine.parse(compact)
    room = machine.rooms[1]
    rows = [
        "".join(machine.grid[row][room.left : room.right + 1])
        for row in range(room.top, room.bottom + 1)
    ]
    if (len(rows), len(rows[0])) != (123, 26):
        raise ValueError(f"unexpected reordered worker size {(len(rows), len(rows[0]))}")

    indices = {id(candidate): index for index, candidate in enumerate(machine.rooms)}
    observed = {}
    for pipe in machine.pipes:
        role = (indices[id(pipe.source)], indices[id(pipe.dest)])
        if role == (0, 1):
            observed["setup"] = pipe.cells[-1][1] - room.left
        elif role == (1, 2):
            observed["output"] = pipe.cells[0][1] - room.left
        elif role == (1, 3):
            observed["ring_out"] = pipe.cells[0][1] - room.left
        elif role == (3, 1):
            observed["ring_in"] = pipe.cells[-1][1] - room.left
    if observed != FUSED_COMPACT_PORTS:
        raise ValueError(f"unexpected reordered worker ports {observed}")
    return rows


def _room_rows(machine: Machine, room_index: int) -> list[str]:
    room = machine.rooms[room_index]
    return [
        "".join(machine.grid[row][room.left : room.right + 1])
        for row in range(room.top, room.bottom + 1)
    ]


RIGHT_RELAY = [
    "+---+",
    "|vr<|",
    "|>s^|",
    "| @^|",
    "+---+",
]


def build_tarstars_plotter_next() -> str:
    """Build the 125x125 candidate from frozen ``plotter_08`` rooms."""

    source = SOURCE.read_text()
    digest = hashlib.sha256(source.encode()).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError(f"unexpected plotter_08 source hash {digest}")
    machine = Machine.parse(source)
    if (len(machine.rooms), len(machine.pipes), len(machine.men)) != (12, 14, 10):
        raise ValueError("unexpected plotter_08 topology")

    canvas = Canvas()

    worker_top, worker_left = 1, 43
    worker_rows = build_reordered_fused_room()
    canvas.put(worker_top, worker_left, worker_rows)
    worker_bottom = worker_top + len(worker_rows) - 1

    # The input/setup stack occupies the west band above the router.
    canvas.put(3, 1, _room_rows(machine, 1))
    for room_index in range(2, 7):
        room = machine.rooms[room_index]
        canvas.put(room.top, 0, _room_rows(machine, room_index))

    # The retained router, PLOT, SWAP, and DISPLAY rooms fit west of the
    # worker.  DISPLAY is lifted one row so its bottom input is row 124.
    canvas.put(72, 0, _room_rows(machine, 7))
    canvas.put(86, 10, _room_rows(machine, 9))
    canvas.put(86, 24, _room_rows(machine, 10))
    canvas.put(98, 6, _room_rows(machine, 11))

    relay_top, relay_left = 85, 72
    canvas.put(relay_top, relay_left, RIGHT_RELAY)

    # Retained input -> setup chain.
    canvas.pipe([(6, 2), (7, 2)])
    canvas.pipe([(12, 2), (14, 2)])
    canvas.pipe([(19, 2), (21, 2)])
    canvas.pipe([(34, 2), (36, 2)])
    canvas.pipe([(47, 2), (49, 2)])

    # S5 -> worker SETUP approaches the left top port from the west.
    setup_x = worker_left + FUSED_COMPACT_PORTS["setup"]
    canvas.pipe(
        [
            (62, 2),
            (63, 2),
            (63, 39),
            (0, 39),
            (0, setup_x),
        ]
    )
    canvas.cells[(0, setup_x)] = "v"

    # OUTPUT and RING_OUT leave opposite side walls at the same row.  With
    # equal vertical terms, every output-zone send (column 9) is strictly
    # nearer the west pipe and every ring-zone send (column 13) is strictly
    # nearer the east pipe.
    side_row = worker_top + 60
    canvas.pipe(
        [
            (side_row, worker_left - 1),
            (side_row, 40),
            (71, 40),
            (71, 2),
        ]
    )
    canvas.cells[(71, 2)] = "v"

    # The 180-degree relay exposes both ports on its east wall.  RING_OUT uses
    # column 78; the return uses the outer column 79, so the paths stay planar.
    canvas.pipe(
        [
            (side_row, worker_left + len(worker_rows[0])),
            (side_row, 78),
            (relay_top + 1, 78),
            (relay_top + 1, relay_left + 5),
        ]
    )
    ring_in_x = worker_left + FUSED_COMPACT_PORTS["ring_in"]
    canvas.pipe(
        [
            (relay_top + 2, relay_left + 5),
            (relay_top + 2, 79),
            (0, 79),
            (0, ring_in_x),
        ]
    )
    canvas.cells[(0, ring_in_x)] = "v"

    # ROUTER -> PLOT and ROUTER -> SWAP.
    canvas.pipe([(82, 13), (85, 13)])
    canvas.pipe(
        [
            (82, 16),
            (83, 16),
            (83, 32),
            (84, 32),
            (84, 14),
            (85, 14),
            (85, 26),
        ]
    )
    canvas.cells[(85, 26)] = "v"

    # PLOT's two display channels follow DISPLAY one row north.
    canvas.pipe([(90, 19), (92, 19), (92, 9), (97, 9), (97, 16)])
    canvas.cells[(97, 16)] = "v"
    canvas.pipe([(90, 15), (91, 15), (91, 5), (108, 5)])
    canvas.cells[(108, 5)] = ">"

    # SWAP -> DISPLAY approaches the lifted room from row 124.
    canvas.pipe([(92, 30), (96, 30), (96, 40), (124, 40), (124, 26)])
    canvas.cells[(124, 26)] = "^"
    return canvas.render()


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    target = Path(args[0]) if args else ARTIFACT
    target.write_text(build_tarstars_plotter_next())


if __name__ == "__main__":
    main()
