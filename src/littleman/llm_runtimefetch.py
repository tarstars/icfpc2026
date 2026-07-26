"""Combined operation and static-color fetch for the physical LLM runtime."""

from __future__ import annotations

from .lllm_fetch import build_relay
from .llm import op_color
from .llm_opfetch import CLASSIFICATION, _build_fsm
from .llm_rawfetch import unpack_raw_world

RUNTIME_CLASSIFICATION = {
    char: op_color(chr(char)) * 256 + cls * 16 + value
    for char, (cls, value) in CLASSIFICATION.items()
}


def runtimefetch_reference(world: list[int], requests: list[int]) -> list[int]:
    raw = unpack_raw_world(world)
    return [RUNTIME_CLASSIFICATION.get(raw[addr] & 0xFF, 0) for addr in requests]


def build_runtimefetch_room() -> list[str]:
    from .lllm_scan import _compile

    return _compile(_build_fsm(RUNTIME_CLASSIFICATION))


FETCH_LEFT = 5
CMD_ROW, RESP_ROW = 2, 6
RING_OUT_ROW, RING_IN_ROW = 2, 9


def build_runtimefetch_rig() -> str:
    from .canvas import Canvas

    room = build_runtimefetch_room()
    right = FETCH_LEFT + len(room[0]) - 1
    relay_left = right + 5
    far = relay_left + 17
    cv = Canvas()
    cv.put(0, FETCH_LEFT, room)
    cv.put(20, relay_left, build_relay().render())
    cv.put(CMD_ROW - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(RESP_ROW - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(CMD_ROW, 3), (CMD_ROW, FETCH_LEFT - 1)])
    cv.pipe([(RESP_ROW, FETCH_LEFT - 1), (RESP_ROW, 3)])
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
