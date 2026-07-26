"""Normalize rich LLM geometry into a mutable-ring runtime stream."""

from __future__ import annotations

from .lllm_scan import _compile, _Fsm
from .llm_perimeter import ROOM_END
from .llm_pipetrace import PIPE_END
from .llm_roomfind import SETUP_END, WORLD_WORDS

CTRL_EAST = 1
HEAD_BIT = 1 << 19
PIPE_MASK = -3500


def statebuild_reference(tokens: list[int]) -> list[int]:
    """Insert man state and descending pipe-cell bits into the rich stream."""
    out = list(tokens[:WORLD_WORDS])
    index = WORLD_WORDS
    while tokens[index] != SETUP_END:
        event, left, right, top, bottom = tokens[index : index + 5]
        index += 5
        man = -(event + 1)
        out.extend((event, left, right, top, bottom, CTRL_EAST, man, 0, 0, man))
        while tokens[index] != ROOM_END:
            out.append(tokens[index])
            index += 1
            bit = HEAD_BIT
            while tokens[index] != PIPE_END:
                out.extend((tokens[index], bit))
                index += 1
                bit //= 2
            tail_bit = bit * 2
            out.extend((PIPE_MASK, tail_bit - 1, PIPE_END))
            index += 1
        out.append(ROOM_END)
        index += 1
    return [*out, SETUP_END, *tokens[index + 1 :]]


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "lit_l", "@`0064`b", "world_r")
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
    fsm.go("event_restore", "left", "WsM1+NM", "bound_r_0")
    for index in range(4):
        target = f"bound_r_{index + 1}" if index < 3 else "state_ctrl"
        fsm.go(f"bound_r_{index}", "left", "rs", target)
    fsm.go("state_ctrl", "left", "1sWMs0s0sWs", "start_r")

    fsm.sign(
        "start_r",
        "left",
        "r",
        neg="room_end",
        zero="bad_start",
        pos="start_out",
    )
    fsm.go("bad_start", "left", "H", "bad_start")
    fsm.go("start_out", "left", "s", "bit_seed")
    fsm.go("bit_seed", "lit_l", " `524288`M", "cell_r")
    fsm.sign(
        "cell_r",
        "left",
        "r",
        neg="pipe_mask",
        zero="cell_out",
        pos="cell_out",
    )
    fsm.go("cell_out", "left", "sWMs2W/M", "cell_r")
    fsm.go("pipe_mask", "left", "WM2W*M1W-", "pipe_mask_out")
    fsm.go("pipe_mask_out", "lit_l", "M`3500`NsW", "pipe_mask_value")
    fsm.go("pipe_mask_value", "left", "s", "pipe_end")
    fsm.go("pipe_end", "lit_l", " `3000`Ns", "start_r")
    fsm.go("room_end", "left", "s", "item_r")
    fsm.go("setup_end", "left", "Ws", "tail_r")
    fsm.go("tail_r", "left", "r", "tail_s")
    fsm.go("tail_s", "left", "s", "tail_r")
    return fsm


def build_statebuild_room() -> list[str]:
    return _compile(_build_fsm())


CTRL_LEFT = 5
INPUT_ROW, OUTPUT_ROW = 2, 6


def build_statebuild_rig() -> str:
    from .canvas import Canvas

    room = build_statebuild_room()
    cv = Canvas()
    cv.put(0, CTRL_LEFT, room)
    cv.put(INPUT_ROW - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(OUTPUT_ROW - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(INPUT_ROW, 3), (INPUT_ROW, CTRL_LEFT - 1)])
    cv.pipe([(OUTPUT_ROW, CTRL_LEFT - 1), (OUTPUT_ROW, 3)])
    return cv.render()
