"""Three-room physical action coordinator for indexed LLM state."""

from __future__ import annotations

from .canvas import Canvas
from .llm_roomstage import _strip_io, build_roomstage_rig, roomstage_reference


def actioncoordinator_reference(tokens: list[int]) -> list[int]:
    state = list(tokens)
    for room_no in range(3):
        state = roomstage_reference(state, room_no)
    return state


def build_actioncoordinator_rig() -> str:
    cv = Canvas()
    column = 20
    top = 0
    placed = []
    for room_no in range(3):
        rows, ingress, egress = _strip_io(build_roomstage_rig(room_no))
        cv.put(top, column, rows)
        placed.append(
            (
                (top + ingress[0], column + ingress[1]),
                (top + egress[0], column + egress[1]),
            )
        )
        top += len(rows) + 20

    track = 10
    for (_ingress, egress), (ingress, _egress) in zip(placed, placed[1:]):
        cv.pipe(
            [
                egress,
                (egress[0], track),
                (ingress[0], track),
                ingress,
            ]
        )

    ingress = placed[0][0]
    egress = placed[-1][1]
    cv.put(ingress[0] - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(egress[0] - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(ingress[0], 3), ingress])
    cv.pipe([egress, (egress[0], 3)])
    return cv.render()
