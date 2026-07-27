"""Repack the counted Plotter while preserving every room program.

The counted ``plotter_06`` has ETEST and EUPD stacked to the right of the
display/controller block, with three empty columns between the blocks.
Moving that pair two columns west keeps one separating column and reduces the
occupied width from 155 to 152.  Their internal links and hot 193-cell state
ring move rigidly; only two feed-forward pipes are redrawn.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from .canvas import Canvas
from .sim import Machine

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "submissions" / "plotter" / "plotter_06.man"
SOURCE_SHA256 = "ec817fc2c16f1f2d8c46d97e2216025e6d4f541fc88a82747f732db99e8e76f7"

# Source room indices are frozen by SOURCE_SHA256.  Rooms 0 and 10 are ETEST
# and EUPD.  Their two direct pipes and the EUPD->ETEST ring move with them.
MOVED_ROOMS = (0, 10)
DX = -2

# SETUP->ETEST, then EUPD->ADDRESS.  The latter uses the gap below ETEST to
# turn west without accidentally creating a second ETEST output.
EXTERNAL_ROUTES = (
    ((62, 102), (63, 102), (63, 134), (0, 134), (0, 145), (1, 145)),
    (
        (143, 145),
        (144, 145),
        (144, 134),
        (74, 134),
        (74, 88),
        (3, 88),
        (3, 38),
        (4, 38),
    ),
)


def _room_indices(machine: Machine) -> dict[int, int]:
    return {id(room): index for index, room in enumerate(machine.rooms)}


def build_plotter_route() -> str:
    """Return the deterministic 152-square-footprint Plotter candidate."""

    source = SOURCE.read_text()
    digest = hashlib.sha256(source.encode()).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError(f"unexpected plotter_06 source hash {digest}")

    machine = Machine.parse(source)
    indices = _room_indices(machine)
    move_cells: set[tuple[int, int]] = set()
    external_cells: set[tuple[int, int]] = set()

    for room_index in MOVED_ROOMS:
        room = machine.rooms[room_index]
        move_cells.update(
            (row, col)
            for row in range(room.top, room.bottom + 1)
            for col in range(room.left, room.right + 1)
        )

    for pipe in machine.pipes:
        role = (indices[id(pipe.source)], indices[id(pipe.dest)])
        if role in {(0, 10), (10, 0)}:
            move_cells.update(pipe.cells)
        elif role in {(7, 0), (10, 2)}:
            external_cells.update(pipe.cells)

    canvas = Canvas()
    for row, line in enumerate(source.rstrip("\n").split("\n")):
        for col, glyph in enumerate(line):
            if glyph == " " or (row, col) in external_cells:
                continue
            target = (row, col + DX) if (row, col) in move_cells else (row, col)
            if target in canvas.cells:
                raise ValueError(f"translated cell collision at {target}")
            canvas.cells[target] = glyph

    for route in EXTERNAL_ROUTES:
        canvas.pipe(list(route))
    return canvas.render()
