"""Map the physical occupancy-mask transition over one LLM state cycle."""

from __future__ import annotations

from .lllm_fetch import build_relay
from .lllm_scan import _compile, _Fsm
from .llm_perimeter import ROOM_END
from .llm_pipemask import advance_mask, build_pipemask_room
from .llm_pipetrace import PIPE_END
from .llm_roomfind import SETUP_END, WORLD_WORDS
from .llm_statebuild import PIPE_MASK


def maskmap_reference(tokens: list[int]) -> list[int]:
    out = []
    index = 0
    while tokens[index] != SETUP_END:
        out.extend(tokens[index : index + 10])
        index += 10
        while tokens[index] != ROOM_END:
            out.append(tokens[index])
            index += 1
            while tokens[index] != PIPE_MASK:
                out.extend(tokens[index : index + 2])
                index += 2
            out.append(PIPE_MASK)
            out.append(advance_mask(tokens[index + 1]))
            out.append(PIPE_END)
            assert tokens[index + 2] == PIPE_END
            index += 3
        out.append(ROOM_END)
        index += 1
    return [*out, SETUP_END]


def maskprefix_reference(tokens: list[int]) -> list[int]:
    return [
        *tokens[:WORLD_WORDS],
        *maskmap_reference(tokens[WORLD_WORDS:]),
    ]


def _build_fsm(*, prefix_world: bool = False) -> _Fsm:
    fsm = _Fsm()
    if prefix_world:
        fsm.go("boot", "lit_l", "@`0064`b", "world_r")
        fsm.go("world_r", "left", "r", "world_s")
        fsm.go("world_s", "left", "s", "world_count")
        fsm.bp("world_count", "mid", "m", zero="item_r", pos="world_r")
    else:
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
        target = f"field_r_{index + 1}" if index < 8 else "start_r"
        fsm.go(f"field_r_{index}", "left", "rs", target)
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
    fsm.go("mask_r", "left", "r", "mask_send")
    fsm.go("mask_send", "right", "s", "mask_recv")
    fsm.go("mask_recv", "right", "r", "mask_out")
    fsm.go("mask_out", "left", "s", "pipe_end_r")
    fsm.go("pipe_end_r", "left", "rs", "start_r")
    fsm.go("room_end", "left", "s", "item_r")
    fsm.go("setup_end", "left", "Ws", "item_r")
    return fsm


def build_maskmap_room() -> list[str]:
    return _compile(_build_fsm())


def build_maskprefix_room() -> list[str]:
    return _compile(_build_fsm(prefix_world=True))


CTRL_LEFT = 5
INPUT_ROW, OUTPUT_ROW = 2, 6
CTRL_CMD_ROW, CTRL_RESP_ROW = 2, 9


def build_maskmap_rig() -> str:
    from .canvas import Canvas

    ctrl = build_maskmap_room()
    ctrl_right = CTRL_LEFT + len(ctrl[0]) - 1
    service_left = ctrl_right + 10
    service = build_pipemask_room()
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
