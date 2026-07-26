"""Delimiter-safe physical copy of one indexed LLM state stream."""

from __future__ import annotations

from .canvas import Canvas
from .lllm_fetch import build_relay
from .lllm_scan import _compile, _Fsm
from .llm_stateindex import INDEX_END

INDEX_COPY_SPLIT = -5000
INDEX_COPY_END = -5100


def indexcopy_reference(tokens: list[int]) -> list[int]:
    if not tokens or tokens[-1] != INDEX_END:
        raise ValueError("index copy requires one complete indexed state")
    return [*tokens, INDEX_COPY_SPLIT, *tokens, INDEX_COPY_END]


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "item_r")
    fsm.go("item_r", "left", "r", "item_cmp")
    fsm.sign(
        "item_cmp",
        "lit_l",
        f"M`{abs(INDEX_END)}`+",
        neg="item_restore",
        zero="end_restore",
        pos="item_restore",
    )
    fsm.go("item_restore", "left", "Ws", "scratch_s")
    fsm.go("scratch_s", "right", "s", "item_r")
    fsm.go("end_restore", "left", "Ws", "end_scratch")
    fsm.go("end_scratch", "right", "s", "scratch_end")
    fsm.go("scratch_end", "lit_r", f" `{abs(INDEX_COPY_END)}`Ns", "split_out")
    fsm.go("split_out", "lit_l", f" `{abs(INDEX_COPY_SPLIT)}`Ns", "copy_r")
    fsm.go("copy_r", "right", "r", "copy_cmp")
    fsm.sign(
        "copy_cmp",
        "lit_r",
        f"M`{abs(INDEX_COPY_END)}`+",
        neg="copy_restore",
        zero="copy_end",
        pos="copy_restore",
    )
    fsm.go("copy_restore", "left", "Ws", "copy_r")
    fsm.go(
        "copy_end",
        "lit_l",
        f"M`{abs(INDEX_COPY_END)}`NsH",
        "copy_end",
    )
    return fsm


def build_indexcopy_room() -> list[str]:
    return _compile(_build_fsm())


CTRL_LEFT = 5
INPUT_ROW, OUTPUT_ROW = 2, 6
RING_OUT_ROW, RING_IN_ROW = 2, 9


def build_indexcopy_rig() -> str:
    room = build_indexcopy_room()
    right = CTRL_LEFT + len(room[0]) - 1
    relay_left = right + 5
    far = relay_left + 17
    buffer_bottom = 300
    cv = Canvas()
    cv.put(0, CTRL_LEFT, room)
    cv.put(20, relay_left, build_relay().render())
    cv.put(INPUT_ROW - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(OUTPUT_ROW - 1, 0, ["+-+", "|O|", "+-+"])
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
            (21, right + 3),
            (buffer_bottom, right + 3),
            (buffer_bottom, right + 2),
            (RING_IN_ROW, right + 2),
            (RING_IN_ROW, right + 1),
        ]
    )
    return cv.render()
