"""Map one fetched op over every man record in a normalized state cycle."""

from __future__ import annotations

from .lllm_fetch import build_relay
from .lllm_scan import _compile, _Fsm
from .llm_manstep import build_manstep_room, manstep_reference
from .llm_perimeter import ROOM_END
from .llm_pipetrace import PIPE_END
from .llm_roomfind import SETUP_END
from .llm_statebuild import PIPE_MASK, PIPE_VALUES


def manmap_reference(tokens: list[int]) -> list[int]:
    out = []
    index = 0
    while tokens[index] != SETUP_END:
        out.extend(tokens[index : index + 5])
        state = tokens[index + 5 : index + 10]
        record = tokens[index + 10]
        index += 11
        out.extend(manstep_reference([*state, 0], record)[:5])
        out.append(record)
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
    fsm.go("boot", "left", "@", "item_r")
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
    fsm.go("event_out", "left", "Ws", "bound_r_0")
    for index in range(4):
        target = f"bound_r_{index + 1}" if index < 3 else "state_r_0"
        fsm.go(f"bound_r_{index}", "left", "rs", target)
    for index in range(5):
        target = f"state_r_{index + 1}" if index < 4 else "dummy"
        fsm.go(f"state_r_{index}", "left", "r", f"state_s_{index}")
        fsm.go(f"state_s_{index}", "right", "s", target)
    fsm.go("dummy", "right", "0s", "record_r")
    fsm.go("record_r", "left", "rM", "record_s")
    fsm.go("record_s", "right", "s", "result_r_0")
    for index in range(6):
        if index < 5:
            target = f"result_r_{index + 1}"
            fsm.go(f"result_r_{index}", "right", "r", f"result_s_{index}")
            fsm.go(f"result_s_{index}", "left", "s", target)
        else:
            fsm.go("result_r_5", "right", "rW", "record_out")
    fsm.go("record_out", "left", "s", "start_r")
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


def build_manmap_room() -> list[str]:
    return _compile(_build_fsm())


CTRL_LEFT = 5
INPUT_ROW, OUTPUT_ROW = 2, 6
CTRL_CMD_ROW, CTRL_RESP_ROW = 2, 9


def build_manmap_rig() -> str:
    from .canvas import Canvas

    ctrl = build_manmap_room()
    ctrl_right = CTRL_LEFT + len(ctrl[0]) - 1
    service_left = ctrl_right + 10
    service = build_manstep_room()
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
    cv.pipe([(2, service_right + 1), (2, far), (21, far), (21, relay_left + 6)])
    cv.pipe(
        [
            (21, relay_left - 1),
            (21, service_right + 2),
            (9, service_right + 2),
            (9, service_right + 1),
        ]
    )
    return cv.render()
