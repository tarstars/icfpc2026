"""Adapt STATEFRAME color/address pairs to LLLM DRAW packed deltas."""

from __future__ import annotations

from .lllm_scan import _compile, _Fsm
from .llm_stateframe import FRAME_END


def pairpack_reference(tokens: list[int]) -> list[int]:
    out = []
    index = 0
    while tokens[index] != FRAME_END:
        color, addr = tokens[index : index + 2]
        out.append(addr * 16 + color)
        index += 2
    if index + 1 != len(tokens):
        raise ValueError("unexpected tokens after frame end")
    return [*out, FRAME_END]


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "color_r")
    fsm.sign(
        "color_r",
        "left",
        "r",
        neg="frame_end",
        zero="color_store",
        pos="color_store",
    )
    fsm.go("color_store", "right", "s", "addr_r")
    fsm.go("addr_r", "left", "rM", "addr_mul")
    fsm.go("addr_mul", "lit_r", " `0016`W*M", "color_again")
    fsm.go("color_again", "right", "r+", "packed_out")
    fsm.go("packed_out", "left", "s", "color_r")
    fsm.go("frame_end", "left", "sH", "frame_end")
    return fsm


def build_pairpack_room() -> list[str]:
    return _compile(_build_fsm())


CTRL_LEFT = 5
INPUT_ROW, OUTPUT_ROW = 2, 6
RING_OUT_ROW, RING_IN_ROW = 2, 9


def build_pairpack_rig() -> str:
    from .canvas import Canvas
    from .lllm_fetch import build_relay

    room = build_pairpack_room()
    right = CTRL_LEFT + len(room[0]) - 1
    relay_left = right + 5
    far = relay_left + 17
    cv = Canvas()
    cv.put(0, CTRL_LEFT, room)
    cv.put(INPUT_ROW - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(OUTPUT_ROW - 1, 0, ["+-+", "|O|", "+-+"])
    cv.put(20, relay_left, build_relay().render())
    cv.pipe([(INPUT_ROW, 3), (INPUT_ROW, CTRL_LEFT - 1)])
    cv.pipe([(OUTPUT_ROW, CTRL_LEFT - 1), (OUTPUT_ROW, 3)])
    cv.pipe(
        [
            (RING_OUT_ROW, right + 1),
            (RING_OUT_ROW, far),
            (21, far),
            (21, relay_left + 6),
        ]
    )
    cv.pipe(
        [
            (21, relay_left - 1),
            (21, right + 2),
            (RING_IN_ROW, right + 2),
            (RING_IN_ROW, right + 1),
        ]
    )
    return cv.render()
