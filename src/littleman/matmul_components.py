"""Component-level transformations for the compact Matrix Multiply machine."""

from __future__ import annotations

from .alexey_piperoute import Router
from .alexey_squeeze import squeeze
from .alexey_stairfold import fold_room, ports_are_single_walled
from .sim import Machine

CONTROLLER_ROOM_INDEX = 0
A_RING_CAPACITY = 256


def _input_clearance_cells(machine: Machine) -> set[tuple[int, int]]:
    input_room = next(room for room in machine.rooms if room.kind == "input")
    border = {
        (row, col)
        for row in range(input_room.top, input_room.bottom + 1)
        for col in range(input_room.left, input_room.right + 1)
        if row in (input_room.top, input_room.bottom)
        or col in (input_room.left, input_room.right)
    }
    blocked = set()
    for row, col in border:
        blocked.update(((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)))
    input_pipe = next(pipe for pipe in machine.pipes if pipe.source is input_room)
    blocked.difference_update(input_pipe.cells)
    return blocked


def _reroute_a_ring(text: str) -> str:
    machine = Machine.parse(text)
    controller = machine.rooms[CONTROLLER_ROOM_INDEX]
    old = next(
        pipe for pipe in machine.in_pipes[id(controller)] if len(pipe.cells) == 334
    )
    router = Router(text, extra_blocked=_input_clearance_cells(machine))
    router.erase(old.cells)
    path = router.route_safe(
        old.cells[0],
        old.cells[-1],
        into=(-1, 0),
        target=A_RING_CAPACITY,
        bounds=(router.h - 1, router.w - 1),
        out=(1, 0),
    )
    return router.apply(path, into=(-1, 0))


def build_matmul_controller_folded(base_text: str) -> str:
    """Fold the single-wall controller staircase and remove freed rows."""

    machine = Machine.parse(base_text)
    controller = machine.rooms[CONTROLLER_ROOM_INDEX]
    if not ports_are_single_walled(machine, controller):
        raise ValueError("Matrix controller ports must share one wall")
    folded, freed = fold_room(base_text, CONTROLLER_ROOM_INDEX)
    if freed != 48:
        raise ValueError(f"expected 48 freed controller rows, got {freed}")
    candidate, rows_dropped, cols_dropped = squeeze(
        folded,
        rows=True,
        cols=False,
    )
    if (rows_dropped, cols_dropped) != (44, 0):
        raise ValueError(
            f"expected rows-only squeeze (44, 0), got {(rows_dropped, cols_dropped)}"
        )
    return _reroute_a_ring(candidate)
