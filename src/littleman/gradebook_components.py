"""Named room contracts and isolated rigs for the Grade Book machine."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .alexey_squeeze import squeeze
from .alexey_stairfold import merge_once, room_rows
from .canvas import Canvas
from .gradebook import RELAY, build_gradebook_no_delay
from .sim import Machine


@dataclass(frozen=True)
class RoomContract:
    """Stable semantic name for one physical room in ``gradebook_04``."""

    name: str
    component: str
    legacy_name: str
    incoming: tuple[str, ...]
    outgoing: tuple[str, ...]


@dataclass(frozen=True)
class FrontendBurst:
    """One broadcast burst followed by an acknowledgement barrier."""

    kind: str
    tokens: tuple[int, ...]


def frontend_reference(rounds: Sequence[dict]) -> tuple[FrontendBurst, ...]:
    """Normalize judge rounds into the command frontend's broadcast bursts."""

    if not rounds:
        raise ValueError("gradebook requires a roster round")
    roster = [int(value) for value in rounds[0]["in"]]
    if len(roster) < 2:
        raise ValueError("roster must start with N and K")
    students, subjects = roster[:2]
    record_width = subjects + 1
    if not 1 <= subjects <= 4 or len(roster) != 2 + students * record_width:
        raise ValueError("malformed roster")

    normalized = [students]
    cursor = 2
    for _ in range(students):
        record = roster[cursor : cursor + record_width]
        cursor += record_width
        normalized.extend(record)
        normalized.extend([0] * (4 - subjects))
    bursts = [FrontendBurst("roster", tuple(normalized))]

    operation_width = {1: 3, 2: 4, 3: 2, 4: 2}
    for round_index, round_ in enumerate(rounds[1:], start=1):
        raw = [int(value) for value in round_["in"]]
        if not raw:
            raise ValueError(f"round {round_index} lacks an operation count")
        count, cursor = raw[0], 1
        for _ in range(count):
            if cursor >= len(raw) or raw[cursor] not in operation_width:
                raise ValueError(f"round {round_index} has an invalid operation")
            operation = raw[cursor]
            width = operation_width[operation]
            values = raw[cursor : cursor + width]
            if len(values) != width:
                raise ValueError(f"round {round_index} has a truncated operation")
            cursor += width
            if operation == 1:
                normalized = [*values, 0]
            elif operation == 2:
                normalized = values
            else:
                normalized = [operation, 0, values[1], 0]
            bursts.append(FrontendBurst(f"operation[{operation}]", tuple(normalized)))
        if cursor != len(raw):
            raise ValueError(f"round {round_index} has trailing input")
    return tuple(bursts)


def compact_live_frontend(machine_text: str) -> tuple[str, ...]:
    """Crop the bank-spanning blank suffix from ``gradebook_04``'s frontend."""

    machine = Machine.parse(machine_text)
    candidates = [
        room
        for room in machine.rooms
        if len(machine.in_pipes.get(id(room), ())) == 2
        and len(machine.out_pipes.get(id(room), ())) == 4
    ]
    if len(candidates) != 1:
        raise ValueError("expected exactly one Grade Book command frontend")
    room = candidates[0]
    used = [
        (row, col)
        for row in range(room.top + 1, room.bottom)
        for col in range(room.left + 1, room.right)
        if machine.grid[row][col] != " "
    ]
    if not used:
        raise ValueError("command frontend is empty")
    relative_right = max(col - room.left for _, col in used) + 1
    rows = ["+" + "-" * (relative_right - 1) + "+"]
    for row in range(room.top + 1, room.bottom):
        interior = "".join(
            machine.grid[row][room.left + col] for col in range(1, relative_right)
        )
        rows.append("|" + interior + "|")
    rows.append(rows[0])
    return tuple(rows)


def build_frontend_rig(room: Sequence[str]) -> str:
    """Connect the two inputs and four outputs of a frontend room."""

    room = list(room)
    if len(room) < 22 or len(room[0]) < 28:
        raise ValueError("frontend room does not expose the frozen port columns")
    if len({len(row) for row in room}) != 1:
        raise ValueError("frontend room must be rectangular")
    canvas = Canvas()
    frontend_top = 5
    canvas.put(frontend_top, 0, room)
    canvas.put(0, 9, ["+-+", "|I|", "+-+"])
    canvas.pipe([(3, 10), (4, 10)])
    canvas.put(0, 19, ["+--+", "|@H|", "+--+"])
    canvas.pipe([(3, 20), (4, 20)])

    sink_top = frontend_top + len(room) + 5
    for column in (5, 12, 19, 26):
        canvas.put(sink_top, column - 1, ["+--+", "|@H|", "+--+"])
        canvas.pipe(
            [
                (frontend_top + len(room), column),
                (sink_top - 1, column),
            ]
        )
    return canvas.render()


def _engine(subject: int) -> RoomContract:
    incoming = ("command", "record_return", "scratch_return")
    if subject > 1:
        incoming += ("ack_previous",)
    return RoomContract(
        f"subject_engine[{subject}]",
        "subject_engine",
        f"w{subject}",
        incoming,
        ("record_send", "scratch_send", "result", "ack_next"),
    )


GRADEBOOK_04_ROOM_ORDER = (
    RoomContract("input_port", "input_port", "input", (), ("judge_input",)),
    RoomContract(
        "command_frontend",
        "command_frontend",
        "parser",
        ("judge_input", "ack_return"),
        tuple(f"command[{subject}]" for subject in range(1, 5)),
    ),
    *(_engine(subject) for subject in range(1, 5)),
    *(
        RoomContract(
            f"scratch_circulator[{subject}]",
            "fifo_circulator",
            f"relayB{subject}",
            ("scratch_send",),
            ("scratch_return",),
        )
        for subject in range(1, 5)
    ),
    *(
        RoomContract(
            f"record_circulator[{subject}]",
            "fifo_circulator",
            f"relayA{subject}",
            ("record_send",),
            ("record_return",),
        )
        for subject in range(1, 5)
    ),
    RoomContract(
        "result_arbiter",
        "result_arbiter",
        "collector",
        tuple(f"result[{subject}]" for subject in range(1, 5)),
        ("judge_output",),
    ),
    RoomContract(
        "output_port",
        "output_port",
        "output",
        ("judge_output",),
        (),
    ),
)


# The six-glyph loop needs one horizontal cell for @ before r/R.  A 3x2
# interior cannot hold that prologue plus both data operations and four turns.
FLAT_FIFO_CIRCULATOR = ("+----+", "|>@rv|", "|^s <|", "+----+")
COMPACT_RESULT_ARBITER = ("+----+", "|>@Rv|", "|^s <|", "+----+")
GRADEBOOK_COMPONENT_FOLD_PREFIXES = (
    (2, 24),
    (3, 25),
    (4, 25),
    (5, 26),
    (1, 34),
)


def _fold_room_prefix(text: str, room_index: int, merges: int) -> str:
    """Apply an exact, judge-selected number of staircase joins."""

    lines = text.rstrip("\n").split("\n")
    width = max(map(len, lines))
    grid = [list(line.ljust(width)) for line in lines]
    room = Machine.parse(text).rooms[room_index]
    rows = room_rows(grid, room)
    for _ in range(merges):
        folded = merge_once(rows)
        if folded is None:
            raise ValueError(
                f"room {room_index} has fewer than {merges} mergeable joins"
            )
        rows = folded
    for row in range(room.top + 1, room.bottom):
        for col in range(room.left + 1, room.right):
            grid[row][col] = " "
    for offset, cells in enumerate(rows):
        for col, glyph in cells:
            grid[room.top + 1 + offset][col] = glyph
    return "\n".join("".join(row).rstrip() for row in grid) + "\n"


def build_gradebook_component_optimized() -> str:
    """Reproduce the no-delay, judge-gated component optimization."""

    text = build_gradebook_no_delay()
    text, _, _ = squeeze(text, rows=True, cols=False)
    for room_index, merges in GRADEBOOK_COMPONENT_FOLD_PREFIXES:
        text = _fold_room_prefix(text, room_index, merges)
    text, _, _ = squeeze(text, rows=True, cols=False)
    return text


def build_fifo_circulator_rig(room: Sequence[str] = RELAY) -> str:
    """Place one circulator between I and O for protocol-level tests."""

    room = list(room)
    width = len(room[0])
    canvas = Canvas()
    canvas.put(1, 0, ["+-+", "|I|", "+-+"])
    canvas.put(0, 5, room)
    output_left = 5 + width + 2
    canvas.put(1, output_left, ["+-+", "|O|", "+-+"])
    canvas.pipe([(2, 3), (2, 4)])
    canvas.pipe([(2, 5 + width), (2, output_left - 1)])
    return canvas.render()


def _constant_source(value: int, active: bool) -> list[str]:
    if not 0 <= value <= 9:
        raise ValueError("arbiter rig source must be one decimal digit")
    body = f"@{value}sH" if active else "@H  "
    return ["+----+", f"|{body}|", "+----+"]


def build_result_arbiter_rig(active: Sequence[int] = (1, 2, 3, 4)) -> str:
    """Exercise four independent ready inputs and one output."""

    enabled = set(active)
    if not enabled <= {1, 2, 3, 4}:
        raise ValueError("active sources must be selected from 1..4")
    canvas = Canvas()
    canvas.put(10, 12, list(COMPACT_RESULT_ARBITER))
    canvas.put(5, 12, _constant_source(1, 1 in enabled))
    canvas.pipe([(8, 13), (9, 13)])
    canvas.put(16, 12, _constant_source(2, 2 in enabled))
    canvas.pipe([(15, 16), (14, 16)])
    canvas.put(10, 3, _constant_source(3, 3 in enabled))
    canvas.pipe([(11, 9), (11, 11)])
    canvas.put(10, 21, _constant_source(4, 4 in enabled))
    canvas.pipe([(12, 20), (12, 18)])
    canvas.put(0, 22, ["+-+", "|O|", "+-+"])
    canvas.pipe([(9, 15), (8, 15), (8, 20), (1, 20), (1, 21)])
    return canvas.render()
