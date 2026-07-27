"""Conservative ring-margin optimization for the accepted Snake machine.

``snake_03`` restored pipe capacity after a raw geometry squeeze deadlocked
on a deliberately oversized 68-cell growth game. Its inherited
``ring_capacity`` helper includes a nine-cell display-token leg, so this
module also measures the actual six-leg state FIFO: the accepted artifact has
198 cells, this variant has 194, and a measured 192-cell variant deadlocks.
Only the longest restored leg, TICKC -> DRAW, is shortened; the shorter and
more locally constrained legs stay unchanged.
"""

from __future__ import annotations

from .alexey_piperoute import Router
from .sim import Machine
from .snake_components import _into_room, build_component_compact_snake
from .snake_fast import ring_capacity

ROUTE_ENDPOINTS = ((90, 144), (24, 144))
TARGET_ROUTE_CELLS = 85
EXPECTED_REPORTED_RING_CELLS = 203
EXPECTED_STATE_RING_CELLS = 194
ROUTE_BOUNDS = (128, 149)
STATE_STATION_SHAPES = frozenset(
    {
        (56, 75),  # IN
        (19, 70),  # DRAW
        (7, 16),  # TOKENSPLIT
        (26, 91),  # TICKA
        (38, 97),  # TICKB
        (13, 45),  # TICKC
    }
)


def state_ring_capacity(text: str) -> int:
    """Return capacity of the six state-FIFO legs, excluding display pipes."""

    machine = Machine.parse(text)
    stations = {
        id(room)
        for room in machine.rooms
        if (room.bottom - room.top + 1, room.right - room.left + 1)
        in STATE_STATION_SHAPES
    }
    if len(stations) != len(STATE_STATION_SHAPES):
        raise AssertionError("Snake state-station shapes changed")
    return sum(
        len(pipe.cells)
        for pipe in machine.pipes
        if id(pipe.source) in stations and id(pipe.dest) in stations
    )


def build_margin_snake() -> str:
    """Shorten the long TICKC -> DRAW ring leg by four cells."""

    text = build_component_compact_snake()
    machine = Machine.parse(text)
    pipe = next(
        candidate
        for candidate in machine.pipes
        if (candidate.cells[0], candidate.cells[-1]) == ROUTE_ENDPOINTS
    )
    router = Router(text)
    router.erase(pipe.cells)
    out = (
        pipe.cells[1][0] - pipe.cells[0][0],
        pipe.cells[1][1] - pipe.cells[0][1],
    )
    cells = router.route_safe(
        pipe.cells[0],
        pipe.cells[-1],
        into=_into_room(pipe),
        target=TARGET_ROUTE_CELLS,
        bounds=ROUTE_BOUNDS,
        out=out,
    )
    router.apply(cells, _into_room(pipe))
    result = router.text()
    if ring_capacity(result) != EXPECTED_REPORTED_RING_CELLS:
        raise AssertionError(
            f"Snake ring capacity drifted: {ring_capacity(result)} "
            f"!= {EXPECTED_REPORTED_RING_CELLS}"
        )
    if state_ring_capacity(result) != EXPECTED_STATE_RING_CELLS:
        raise AssertionError(
            f"Snake state-ring capacity drifted: {state_ring_capacity(result)} "
            f"!= {EXPECTED_STATE_RING_CELLS}"
        )
    return result
