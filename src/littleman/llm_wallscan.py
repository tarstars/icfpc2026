"""Scan normalized LLM state for per-room wall-freeze flags."""

from __future__ import annotations

from .canvas import Canvas
from .lllm_fetch import build_relay
from .lllm_scan import _compile, _Fsm
from .llm_perimeter import ROOM_END
from .llm_pipetrace import PIPE_END
from .llm_roomfind import SETUP_END
from .llm_statebuild import PIPE_MASK, PIPE_VALUES
from .llm_wallhit import build_wallhit_room, wallhit_reference

WALLSCAN_END = -4400


def wallscan_reference(tokens: list[int]) -> list[int]:
    out = []
    index = 0
    while tokens[index] != SETUP_END:
        fields = tokens[index : index + 10]
        index += 10
        out.extend(wallhit_reference([*fields[1:5], fields[6]]))
        while tokens[index] != ROOM_END:
            index += 1
            while tokens[index] != PIPE_MASK:
                index += 2
            index += 2
            assert tokens[index] == PIPE_VALUES
            count = tokens[index + 1]
            index += 2 + count
            assert tokens[index] == PIPE_END
            index += 1
        index += 1
    return [*out, WALLSCAN_END]


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "item_r")
    fsm.go("item_r", "left", "r", "item_cmp")
    fsm.sign(
        "item_cmp",
        "lit_l",
        "M`1000`+",
        neg="bad_item",
        zero="scan_end",
        pos="bound_r_0",
    )
    fsm.go("bad_item", "left", "H", "bad_item")
    for index in range(4):
        target = f"bound_r_{index + 1}" if index < 3 else "ctrl_drop"
        fsm.go(f"bound_r_{index}", "left", "r", f"bound_s_{index}")
        fsm.go(f"bound_s_{index}", "right", "s", target)
    fsm.go("ctrl_drop", "left", "r", "addr_r")
    fsm.go("addr_r", "left", "r", "addr_s")
    fsm.go("addr_s", "right", "s", "state_drop")
    fsm.go("state_drop", "left", "rrr", "flag_r")
    fsm.go("flag_r", "right", "r", "flag_out")
    fsm.go("flag_out", "left", "s", "start_r")

    fsm.sign(
        "start_r",
        "left",
        "r",
        neg="room_end",
        zero="bad_start",
        pos="pipe_body_r",
    )
    fsm.go("bad_start", "left", "H", "bad_start")
    fsm.go("pipe_body_r", "left", "r", "pipe_body_cmp")
    fsm.sign(
        "pipe_body_cmp",
        "lit_l",
        f"M`{-PIPE_END:04d}`+",
        neg="pipe_body_r",
        zero="start_r",
        pos="pipe_body_r",
    )
    fsm.go("room_end", "left", "", "item_r")
    fsm.go(
        "scan_end",
        "lit_l",
        f"M`{-WALLSCAN_END:04d}`NsH",
        "scan_end",
    )
    return fsm


def build_wallscan_room() -> list[str]:
    return _compile(_build_fsm())


CTRL_LEFT = 5
INPUT_ROW, OUTPUT_ROW = 2, 6
CTRL_CMD_ROW, CTRL_RESP_ROW = 2, 9


def build_wallscan_rig() -> str:
    ctrl = build_wallscan_room()
    ctrl_right = CTRL_LEFT + len(ctrl[0]) - 1
    service_left = ctrl_right + 10
    service = build_wallhit_room()
    service_right = service_left + len(service[0]) - 1
    relay_left = service_right + 5
    far = relay_left + 17
    cv = Canvas()
    cv.put(0, CTRL_LEFT, ctrl)
    cv.put(0, service_left, service)
    cv.put(20, relay_left, build_relay().render())
    cv.put(INPUT_ROW - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(OUTPUT_ROW - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(INPUT_ROW, 3), (INPUT_ROW, CTRL_LEFT - 1)])
    cv.pipe([(OUTPUT_ROW, CTRL_LEFT - 1), (OUTPUT_ROW, 3)])
    cv.pipe([(CTRL_CMD_ROW, ctrl_right + 1), (CTRL_CMD_ROW, service_left - 1)])
    cv.pipe(
        [
            (6, service_left - 1),
            (6, ctrl_right + 4),
            (CTRL_RESP_ROW, ctrl_right + 4),
            (CTRL_RESP_ROW, ctrl_right + 1),
        ]
    )
    cv.pipe(
        [
            (2, service_right + 1),
            (2, far),
            (21, far),
            (21, relay_left + 6),
        ]
    )
    cv.pipe(
        [
            (21, relay_left - 1),
            (21, service_right + 2),
            (9, service_right + 2),
            (9, service_right + 1),
        ]
    )
    return cv.render()
