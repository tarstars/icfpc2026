"""Named room contracts and isolated rigs for the Grade Book machine."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .canvas import Canvas
from .gradebook import RELAY


@dataclass(frozen=True)
class RoomContract:
    """Stable semantic name for one physical room in ``gradebook_04``."""

    name: str
    component: str
    legacy_name: str
    incoming: tuple[str, ...]
    outgoing: tuple[str, ...]


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
