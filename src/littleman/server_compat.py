"""Pre-submission checks for known simulator/server compatibility differences.

The contest server rejects several layouts that the general local parser accepts:
rooms sharing wall cells, one-cell pipes, and input rooms with more than one
outward pipe start. Conversely, the server permits a little man to step into a
wall after its final send and lets already-sent output drain, while the strict
local judge historically stopped the machine immediately.

Use :func:`parse_server_compatible` or :func:`validate_layout` before submission
and the ``judge_*`` functions here for local validation. The strict parser-like
entry point layers every known server-side layout rejection on top of
``sim.Machine.parse``; it intentionally does not change the general simulator
parser because known divergences also run in the opposite direction.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import alexey_walljudge
from .judge import CaseResult, ProblemReport
from .sim import ARROWS, DOWN, LEFT, RIGHT, UP, Machine, Room

MIN_PIPE_CELLS = 2


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


def _find_shared_walls(machine: Machine) -> list[SharedWall]:
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


def find_shared_walls(text: str) -> list[SharedWall]:
    """Return every pair of parsed rooms with one or more shared wall cells."""

    return _find_shared_walls(Machine.parse(text))


def _validate_pipe_lengths(machine: Machine) -> None:
    bad = [
        (index, pipe)
        for index, pipe in enumerate(machine.pipes)
        if len(pipe.cells) < MIN_PIPE_CELLS
    ]
    if not bad:
        return
    details = ", ".join(
        f"pipe {index} at {pipe.cells[0]} ({len(pipe.cells)} cell)"
        for index, pipe in bad
    )
    raise ServerCompatibilityError(
        f"{len(bad)} pipe(s) shorter than {MIN_PIPE_CELLS} cells: {details}; "
        "the server rejects a pipe that reaches the next room in one cell -- "
        "leave a two-cell gap or bend the pipe"
    )


def validate_pipe_lengths(text: str) -> None:
    """Reject pipes shorter than the organizer loader's two-cell minimum."""

    _validate_pipe_lengths(Machine.parse(text))


def _outward_pipe_starts(machine: Machine, room: Room) -> tuple[tuple[int, int], ...]:
    """Return arrowheads that begin a pipe immediately outside ``room``.

    This deliberately mirrors the organizer's local start test rather than
    consulting ``machine.pipes``. The local parser marks globally traced pipe
    cells as used, so an arrowhead can be consumed by a pipe discovered from an
    earlier room and then disappear from the later input room's attributed pipe
    list. That is exactly how ``reverse_03`` hid its second input start.

    A body cell merely running parallel to a room wall is not a start. Counting
    every adjacent parsed pipe cell was the old false-positive source on the
    organizer-accepted ``matmul_05`` and ``matmul_06`` layouts.
    """

    height = len(machine.grid)
    width = len(machine.grid[0]) if height else 0
    border_and_direction = []
    for column in range(room.left, room.right + 1):
        border_and_direction.append((room.top, column, UP))
        border_and_direction.append((room.bottom, column, DOWN))
    for row in range(room.top, room.bottom + 1):
        border_and_direction.append((row, room.left, LEFT))
        border_and_direction.append((row, room.right, RIGHT))

    starts = set()
    for border_row, border_column, direction in border_and_direction:
        row = border_row + direction[0]
        column = border_column + direction[1]
        if not (0 <= row < height and 0 <= column < width):
            continue
        if ARROWS.get(machine.grid[row][column]) == direction:
            starts.add((row, column))
    return tuple(sorted(starts))


def _validate_io_pipe_counts(machine: Machine) -> None:
    for room in machine.rooms:
        kind = getattr(room, "kind", None)
        if kind != "input":
            continue
        starts = _outward_pipe_starts(machine, room)
        if len(starts) > 1:
            corner = (room.top, room.left)
            positions = ", ".join(str(position) for position in starts)
            raise ServerCompatibilityError(
                f"the {kind} room at {corner} has {len(starts)} outward pipe "
                f"starts at {positions} -- connect exactly one"
            )


def validate_io_pipe_counts(text: str) -> None:
    """Reject an input room with more than one outward-pointing pipe start.

    The server enforces this and our simulator can miss it. ``reverse_03``
    passed the local judge 8/8 and preflight READY, then came back from the
    server as ``the input room has more than one outgoing pipe -- connect
    exactly one at (0, 8)``, scoring 0/0.

    The relevant geometry is an arrowhead immediately outside the room whose
    backward cell is on the room border and whose direction points away from
    it. The check must inspect the grid independently of parsed pipe ownership:
    the local parser's global ``used`` set can assign such an arrowhead to a
    pipe discovered from another room first. Conversely, unrelated body cells
    that merely run alongside a wall do not create another outgoing pipe.

    Restricted to INPUT rooms on purpose. The observed server error only named
    the input room, and extending an adjacency heuristic to output rooms
    produced a false positive on the live, server-accepted ``tcp_06`` machine.
    """

    _validate_io_pipe_counts(Machine.parse(text))


def _raise_shared_wall(conflict: SharedWall) -> None:
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


def parse_server_compatible(text: str) -> Machine:
    """Parse locally, then apply every known organizer-side layout rejection.

    This is the parser-like entry point for pre-submission tooling. It returns
    the already parsed machine so callers do not need to parse the same program
    again. It is deliberately layered over :meth:`Machine.parse`: the project
    also preserves programs accepted by the server but rejected by the local
    literal parser, so the general simulator parser must remain independent.
    """

    machine = Machine.parse(text)
    _validate_pipe_lengths(machine)
    _validate_io_pipe_counts(machine)
    conflicts = _find_shared_walls(machine)
    if conflicts:
        _raise_shared_wall(conflicts[0])
    return machine


def validate_layout(text: str) -> None:
    """Reject every locally detectable layout known to fail server loading."""

    parse_server_compatible(text)


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
