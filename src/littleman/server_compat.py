"""Pre-submission checks for known simulator/server compatibility differences.

The contest server rejects rooms that share wall cells, while the local parser
accepts them. Conversely, the server permits a little man to step into a wall
after its final send and lets already-sent output drain, while the strict local
judge stops the machine immediately.

Use :func:`validate_layout` before submission and the ``judge_*`` functions
here for local validation. Together they reject the known server-invalid
layout and accept the known server-valid final-wall-step behavior.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import alexey_walljudge
from .judge import CaseResult, ProblemReport
from .sim import Machine, Room


@dataclass(frozen=True)
class SharedWall:
    """One pair of local-parser rooms that overlap on their borders."""

    first_room: int
    second_room: int
    cells: tuple[tuple[int, int], ...]


class ServerCompatibilityError(ValueError):
    """Raised when a locally parseable layout is known to fail server loading."""


def _border_cells(room: Room) -> set[tuple[int, int]]:
    cells = {(room.top, column) for column in range(room.left, room.right + 1)}
    cells.update((room.bottom, column) for column in range(room.left, room.right + 1))
    cells.update((row, room.left) for row in range(room.top, room.bottom + 1))
    cells.update((row, room.right) for row in range(room.top, room.bottom + 1))
    return cells


def find_shared_walls(text: str) -> list[SharedWall]:
    """Return every pair of parsed rooms with one or more shared wall cells."""

    machine = Machine.parse(text)
    owners: dict[tuple[int, int], list[int]] = {}
    shared: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for room_index, room in enumerate(machine.rooms):
        for cell in _border_cells(room):
            for other_index in owners.get(cell, ()):
                shared.setdefault((other_index, room_index), []).append(cell)
            owners.setdefault(cell, []).append(room_index)
    return [
        SharedWall(first, second, tuple(sorted(cells)))
        for (first, second), cells in sorted(shared.items())
    ]


def validate_layout(text: str) -> None:
    """Reject layouts that exercise the server's stricter shared-wall rule."""

    conflicts = find_shared_walls(text)
    if not conflicts:
        return
    conflict = conflicts[0]
    coordinates = ", ".join(
        f"({row + 1},{column + 1})" for row, column in conflict.cells[:4]
    )
    if len(conflict.cells) > 4:
        coordinates += ", ..."
    raise ServerCompatibilityError(
        "rooms "
        f"{conflict.first_room} and {conflict.second_room} share "
        f"{len(conflict.cells)} wall cell(s) at {coordinates}"
    )


def judge_case(text: str, rounds, max_ticks: int = 5_000_000) -> CaseResult:
    """Validate server layout rules, then use final-wall-step semantics."""

    validate_layout(text)
    return alexey_walljudge.judge_case(text, rounds, max_ticks=max_ticks)


def judge_problem(
    text: str, problem: dict, max_ticks: int | None = None
) -> ProblemReport:
    """Validate server layout rules, then judge with server wall semantics."""

    validate_layout(text)
    return alexey_walljudge.judge_problem(text, problem, max_ticks=max_ticks)
