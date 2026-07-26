"""Refresh each normalized room's previous-frame man address."""

from __future__ import annotations

from .lllm_scan import _compile, _Fsm
from .llm_perimeter import ROOM_END
from .llm_pipetrace import PIPE_END
from .llm_roomfind import SETUP_END, WORLD_WORDS
from .llm_statebuild import PIPE_MASK, PIPE_VALUES


def framebaseline_reference(tokens: list[int]) -> list[int]:
    out = list(tokens[:WORLD_WORDS])
    index = WORLD_WORDS
    while tokens[index] != SETUP_END:
        fields = list(tokens[index : index + 10])
        fields[9] = fields[6]
        out.extend(fields)
        index += 10
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
    return [*out, SETUP_END, *tokens[index + 1 :]]


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "lit_l", f"@`{WORLD_WORDS:04d}`b", "world_r")
    fsm.go("world_r", "left", "r", "world_s")
    fsm.go("world_s", "left", "s", "world_count")
    fsm.bp("world_count", "mid", "m", zero="item_r", pos="world_r")
    fsm.go("item_r", "left", "r", "item_cmp")
    fsm.sign(
        "item_cmp",
        "lit_l",
        "M`1000`+",
        neg="bad_item",
        zero="setup_end",
        pos="event_restore",
    )
    fsm.go("bad_item", "left", "H", "bad_item")
    fsm.go("event_restore", "left", "Ws", "bound_r_0")
    for index in range(4):
        target = f"bound_r_{index + 1}" if index < 3 else "ctrl_r"
        fsm.go(f"bound_r_{index}", "left", "rs", target)
    fsm.go("ctrl_r", "left", "rs", "addr_r")
    fsm.go("addr_r", "left", "rMs", "bi_r")
    fsm.go("bi_r", "left", "rs", "ai_r")
    fsm.go("ai_r", "left", "rs", "old_r")
    fsm.go("old_r", "left", "rWs", "start_r")
    fsm.sign(
        "start_r",
        "left",
        "r",
        neg="room_end",
        zero="bad_start",
        pos="start_restore",
    )
    fsm.go("bad_start", "left", "H", "bad_start")
    fsm.go("start_restore", "left", "s", "body_r")
    fsm.sign(
        "body_r",
        "left",
        "r",
        neg="mask_restore",
        zero="body_restore",
        pos="body_restore",
    )
    fsm.go("body_restore", "left", "s", "body_r")
    fsm.go("mask_restore", "left", "s", "mask_r")
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


def build_framebaseline_room() -> list[str]:
    return _compile(_build_fsm())


def build_framebaseline_rig() -> str:
    from .canvas import Canvas

    room = build_framebaseline_room()
    cv = Canvas()
    cv.put(0, 5, room)
    cv.put(1, 0, ["+-+", "|I|", "+-+"])
    cv.put(5, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(2, 3), (2, 4)])
    cv.pipe([(6, 4), (6, 3)])
    return cv.render()
