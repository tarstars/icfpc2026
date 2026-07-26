"""Delimiter-safe physical copy of one normalized LLM state stream."""

from __future__ import annotations

from .lllm_scan import _compile, _Fsm
from .llm_roomfind import SETUP_END

COPY_SPLIT = -4600
COPY_END = -4700


def statecopy_reference(tokens: list[int]) -> list[int]:
    if not tokens or tokens[-1] != SETUP_END:
        raise ValueError("state copy requires one complete normalized state")
    return [*tokens, COPY_SPLIT, *tokens, COPY_END]


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "item_r")
    fsm.go("item_r", "left", "R", "item_cmp")
    fsm.sign(
        "item_cmp",
        "lit_l",
        "M`1000`+",
        neg="item_restore",
        zero="setup_restore",
        pos="item_restore",
    )
    fsm.go("item_restore", "left", "Ws", "scratch_s")
    fsm.go("scratch_s", "right", "s", "item_r")

    fsm.go("setup_restore", "left", "Ws", "setup_scratch")
    fsm.go("setup_scratch", "right", "s", "scratch_end")
    fsm.go("scratch_end", "lit_r", f" `{abs(COPY_END):04d}`Ns", "split_out")
    fsm.go("split_out", "lit_l", f" `{abs(COPY_SPLIT):04d}`Ns", "copy_r")

    fsm.go("copy_r", "right", "r", "copy_cmp")
    fsm.sign(
        "copy_cmp",
        "lit_r",
        f"M`{abs(COPY_END):04d}`+",
        neg="copy_restore",
        zero="copy_end",
        pos="copy_restore",
    )
    fsm.go("copy_restore", "left", "Ws", "copy_r")
    fsm.go("copy_end", "lit_l", f"M`{abs(COPY_END):04d}`Ns", "item_r")
    return fsm


def build_statecopy_room() -> list[str]:
    return _compile(_build_fsm())


CTRL_LEFT = 5
INPUT_ROW, OUTPUT_ROW = 2, 6
RING_OUT_ROW, RING_IN_ROW = 2, 9


def build_statecopy_rig() -> str:
    from .canvas import Canvas
    from .lllm_fetch import build_relay

    room = build_statecopy_room()
    right = CTRL_LEFT + len(room[0]) - 1
    relay_left = right + 5
    far = relay_left + 17
    buffer_bottom = 260
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
            (21, right + 3),
            (buffer_bottom, right + 3),
            (buffer_bottom, right + 2),
            (RING_IN_ROW, right + 2),
            (RING_IN_ROW, right + 1),
        ]
    )
    return cv.render()
