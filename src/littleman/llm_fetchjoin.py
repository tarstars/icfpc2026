"""Append runtime op records to each room in one normalized state cycle."""

from __future__ import annotations

from .lllm_fetch import build_relay
from .lllm_scan import _compile, _Fsm
from .llm_perimeter import ROOM_END
from .llm_pipetrace import PIPE_END
from .llm_roomfind import SETUP_END, WORLD_WORDS
from .llm_runtimefetch import (
    build_runtimefetch_room,
    runtimefetch_reference,
)
from .llm_statebuild import PIPE_MASK, PIPE_VALUES


def fetchjoin_reference(tokens: list[int]) -> list[int]:
    world = tokens[:WORLD_WORDS]
    out = []
    index = WORLD_WORDS
    while tokens[index] != SETUP_END:
        out.extend(tokens[index : index + 10])
        addr = tokens[index + 6]
        index += 10
        out.extend(runtimefetch_reference(world, [addr]))
        while tokens[index] != ROOM_END:
            out.append(tokens[index])
            index += 1
            while tokens[index] != PIPE_MASK:
                out.extend(tokens[index : index + 2])
                index += 2
            out.extend(tokens[index : index + 2])
            index += 2
            assert tokens[index] == PIPE_VALUES
            count = tokens[index + 1]
            out.extend(tokens[index : index + 2 + count])
            index += 2 + count
            assert tokens[index] == PIPE_END
            out.append(PIPE_END)
            index += 1
        out.append(ROOM_END)
        index += 1
    return [*out, SETUP_END]


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "lit_l", "@`0064`b", "world_r")
    fsm.go("world_r", "left", "r", "world_s")
    fsm.go("world_s", "right", "s", "world_count")
    fsm.bp("world_count", "mid", "m", zero="item_r", pos="world_r")

    fsm.go("item_r", "left", "r", "item_cmp")
    fsm.sign(
        "item_cmp",
        "lit_l",
        "M`1000`+",
        neg="bad_item",
        zero="setup_end",
        pos="event_out",
    )
    fsm.go("bad_item", "left", "H", "bad_item")
    fsm.go("event_out", "left", "Ws", "field_r_0")
    for index in range(9):
        if index == 5:  # ADDR is field 6 after the event.
            fsm.go("field_r_5", "left", "rMsW", "fetch_send")
            fsm.go("fetch_send", "right", "s", "field_r_6")
            continue
        target = f"field_r_{index + 1}" if index < 8 else "fetch_recv"
        fsm.go(f"field_r_{index}", "left", "rs", target)
    fsm.go("fetch_recv", "right", "r", "fetch_out")
    fsm.go("fetch_out", "left", "s", "start_r")

    fsm.sign(
        "start_r",
        "left",
        "r",
        neg="room_end",
        zero="bad_start",
        pos="start_out",
    )
    fsm.go("bad_start", "left", "H", "bad_start")
    fsm.go("start_out", "left", "s", "body_r")
    fsm.sign(
        "body_r",
        "left",
        "r",
        neg="mask_marker",
        zero="cell_out",
        pos="cell_out",
    )
    fsm.go("cell_out", "left", "s", "bit_r")
    fsm.go("bit_r", "left", "rs", "body_r")
    fsm.go("mask_marker", "left", "s", "mask_r")
    fsm.go("mask_r", "left", "rs", "values_marker_r")
    fsm.go("values_marker_r", "left", "rs", "values_count_r")
    fsm.go("values_count_r", "left", "rMbs", "values_count")
    fsm.bp("values_count", "mid", "", zero="pipe_end_r", pos="value_r")
    fsm.go("value_r", "left", "rs", "values_dec")
    fsm.bp("values_dec", "mid", "m", zero="pipe_end_r", pos="value_r")
    fsm.go("pipe_end_r", "left", "rs", "start_r")
    fsm.go("room_end", "left", "s", "item_r")
    fsm.go("setup_end", "left", "Ws", "item_r")
    return fsm


def build_fetchjoin_room() -> list[str]:
    return _compile(_build_fsm())


CTRL_LEFT = 5
INPUT_ROW, OUTPUT_ROW = 2, 6
CTRL_CMD_ROW, CTRL_RESP_ROW = 2, 9


def build_fetchjoin_rig() -> str:
    from .canvas import Canvas

    ctrl = build_fetchjoin_room()
    ctrl_right = CTRL_LEFT + len(ctrl[0]) - 1
    fetch_left = ctrl_right + 10
    fetch = build_runtimefetch_room()
    fetch_right = fetch_left + len(fetch[0]) - 1
    relay_left = fetch_right + 5
    far = relay_left + 17
    cv = Canvas()
    cv.put(0, CTRL_LEFT, ctrl)
    cv.put(0, fetch_left, fetch)
    cv.put(20, relay_left, build_relay().render())
    cv.put(INPUT_ROW - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(OUTPUT_ROW - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(INPUT_ROW, 3), (INPUT_ROW, CTRL_LEFT - 1)])
    cv.pipe([(OUTPUT_ROW, CTRL_LEFT - 1), (OUTPUT_ROW, 3)])
    cv.pipe([(CTRL_CMD_ROW, ctrl_right + 1), (CTRL_CMD_ROW, fetch_left - 1)])
    cv.pipe(
        [
            (6, fetch_left - 1),
            (6, ctrl_right + 4),
            (CTRL_RESP_ROW, ctrl_right + 4),
            (CTRL_RESP_ROW, ctrl_right + 1),
        ]
    )
    cv.pipe([(2, fetch_right + 1), (2, far), (21, far), (21, relay_left + 6)])
    cv.pipe(
        [
            (21, relay_left - 1),
            (21, fetch_right + 2),
            (9, fetch_right + 2),
            (9, fetch_right + 1),
        ]
    )
    return cv.render()
