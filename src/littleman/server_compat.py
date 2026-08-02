"""Pre-submission checks for known simulator/server compatibility differences.

The contest server rejects several layouts that the general local parser accepts:
rooms sharing wall cells, one-cell pipes, and input rooms with more than one pipe
running against their wall. Conversely, the server permits a little man to step
into a wall after its final send and lets already-sent output drain, while the
strict local judge historically stopped the machine immediately.

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
from .sim import Machine, Room

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


def _validate_io_pipe_counts(machine: Machine) -> None:
    for room in machine.rooms:
        kind = getattr(room, "kind", None)
        if kind != "input":
            continue
        border = _border_cells(room)
        touching = set()
        for index, pipe in enumerate(machine.pipes):
            for row, column in pipe.cells:
                neighbours = (
                    (row - 1, column),
                    (row + 1, column),
                    (row, column - 1),
                    (row, column + 1),
                )
                if any(cell in border for cell in neighbours):
                    touching.add(index)
                    break
        if len(touching) > 1:
            corner = (room.top, room.left)
            raise ServerCompatibilityError(
                f"the {kind} room at {corner} has {len(touching)} pipes running "
                "against its wall -- connect exactly one (a pipe merely passing "
                "alongside still counts as connected to the server)"
            )


def validate_io_pipe_counts(text: str) -> None:
    """Reject an input room with more than one pipe running against its wall.

    The server enforces this and our simulator does not. A reverse-a-list
    candidate passed the local judge 8/8 and preflight READY, then came back
    from the server as ``the input room has more than one outgoing pipe --
    connect exactly one at (0, 8)``, scoring 0/0.

    The rule is about ADJACENCY, not about where a pipe starts and ends. Our
    simulator attributes a pipe to the rooms at its two ends, so a pipe that
    merely runs flush along an I/O room's wall on its way elsewhere is invisible
    to us and is a second connection to the server.

    Restricted to INPUT rooms on purpose. The observed server error only ever
    named the input room, and extending it to output rooms produced a false
    positive on `tcp_06.man`, a live machine accepted by the server.
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
