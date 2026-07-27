"""Component-preserving geometry compaction for the accepted Snake machine.

``snake_fast`` already names and tests the logical components: IN, DRAW,
TICKA, TICKB, TICKC, the display block, and the I/O rooms.  This module
changes none of their instruction glyphs.  It removes globally empty rows
and columns from the assembled machine, shortening blank walks and pipe
runs while retaining enough capacity for the state ring.
"""

from __future__ import annotations

from dataclasses import dataclass

from .alexey_piperoute import Router
from .alexey_squeeze import squeeze
from .sim import Machine
from .snake_fast import MIN_RING_CELLS, build_fast_snake, ring_capacity


@dataclass(frozen=True)
class SnakeCompaction:
    """Measured properties of the deterministic geometry pass."""

    rows_removed: int
    columns_removed: int
    ring_cells: int


EXPECTED_COMPACTION = SnakeCompaction(
    rows_removed=25,
    columns_removed=6,
    ring_cells=207,
)

# Endpoints in the squeezed machine, with the minimum restored capacity.
# They are the three ring legs shortened below their accepted lengths.
RING_ROUTE_TARGETS = {
    ((90, 144), (24, 144)): 89,  # TICKC -> DRAW
    ((41, 87), (61, 40)): 74,  # TOKENSPLIT -> IN
    ((24, 86), (36, 79)): 26,  # DRAW -> TOKENSPLIT
}


def _into_room(pipe) -> tuple[int, int]:
    """Direction from a pipe's final cell into its destination wall."""

    row, column = pipe.cells[-1]
    room = pipe.dest
    if row == room.top - 1:
        return (1, 0)
    if row == room.bottom + 1:
        return (-1, 0)
    if column == room.left - 1:
        return (0, 1)
    if column == room.right + 1:
        return (0, -1)
    raise ValueError(f"pipe does not end beside its destination: {(row, column)}")


def compact_snake(text: str) -> tuple[str, SnakeCompaction]:
    """Squeeze geometry, then restore the accepted ring's buffer headroom."""

    compact, rows_removed, columns_removed = squeeze(
        text,
        rows=True,
        cols=True,
    )
    machine = Machine.parse(compact)
    by_endpoints = {(pipe.cells[0], pipe.cells[-1]): pipe for pipe in machine.pipes}
    selected = {endpoints: by_endpoints[endpoints] for endpoints in RING_ROUTE_TARGETS}
    router = Router(compact)
    for pipe in selected.values():
        router.erase(pipe.cells)
    for endpoints, target in sorted(
        RING_ROUTE_TARGETS.items(),
        key=lambda item: -item[1],
    ):
        pipe = selected[endpoints]
        out = (
            pipe.cells[1][0] - pipe.cells[0][0],
            pipe.cells[1][1] - pipe.cells[0][1],
        )
        cells = router.route_safe(
            pipe.cells[0],
            pipe.cells[-1],
            into=_into_room(pipe),
            target=target,
            bounds=(128, 149),
            out=out,
        )
        router.apply(cells, _into_room(pipe))
    compact = router.text()
    result = SnakeCompaction(
        rows_removed=rows_removed,
        columns_removed=columns_removed,
        ring_cells=ring_capacity(compact),
    )
    if result.ring_cells < MIN_RING_CELLS:
        raise ValueError(
            f"Snake ring capacity {result.ring_cells} is below "
            f"the required {MIN_RING_CELLS}"
        )
    return compact, result


def build_component_compact_snake() -> str:
    """Build the accepted fast machine and apply the frozen geometry pass."""

    compact, properties = compact_snake(build_fast_snake())
    if properties != EXPECTED_COMPACTION:
        raise AssertionError(
            f"Snake compaction drifted: {properties!r} != {EXPECTED_COMPACTION!r}"
        )
    return compact
