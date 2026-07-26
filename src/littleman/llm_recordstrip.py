"""Drop transient fetched-op records after an LLM man-map cycle."""

from __future__ import annotations

from .lllm_scan import _compile, _Fsm
from .llm_perimeter import ROOM_END
from .llm_pipetrace import PIPE_END
from .llm_roomfind import SETUP_END
from .llm_statebuild import PIPE_MASK, PIPE_VALUES


def recordstrip_reference(tokens: list[int]) -> list[int]:
    out = []
    index = 0
    while tokens[index] != SETUP_END:
        out.extend(tokens[index : index + 10])
        index += 11
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
    fsm.go("event_out", "left", "Ws", "field_r_0")
    for index in range(9):
        target = f"field_r_{index + 1}" if index < 8 else "record_drop"
        fsm.go(f"field_r_{index}", "left", "rs", target)
    fsm.go("record_drop", "left", "r", "start_r")
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
    fsm.go("values_count_r", "left", "rMs", "values_count")
    fsm.bp("values_count", "mid", "", zero="pipe_end_r", pos="value_r")
    fsm.go("value_r", "left", "rs", "values_dec")
    fsm.bp("values_dec", "mid", "m", zero="pipe_end_r", pos="value_r")
    fsm.go("pipe_end_r", "left", "rs", "start_r")
    fsm.go("room_end", "left", "s", "item_r")
    fsm.go("setup_end", "left", "Ws", "item_r")
    return fsm


def build_recordstrip_room() -> list[str]:
    return _compile(_build_fsm())


CTRL_LEFT = 5
INPUT_ROW, OUTPUT_ROW = 2, 6


def build_recordstrip_rig() -> str:
    from .canvas import Canvas

    room = build_recordstrip_room()
    cv = Canvas()
    cv.put(0, CTRL_LEFT, room)
    cv.put(INPUT_ROW - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(OUTPUT_ROW - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(INPUT_ROW, 3), (INPUT_ROW, CTRL_LEFT - 1)])
    cv.pipe([(OUTPUT_ROW, CTRL_LEFT - 1), (OUTPUT_ROW, 3)])
    return cv.render()
