"""Advance packed LLM pipe occupancy masks by one interpreted tick."""

from __future__ import annotations

from .lllm_fetch import build_relay
from .lllm_scan import _compile, _Fsm


def advance_mask(mask: int) -> int:
    """Shift all non-tail-blocked runs toward bit zero in one operation."""
    trailing = mask ^ (mask & (mask + 1))
    return trailing | ((mask ^ trailing) >> 1)


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "request")
    fsm.go("request", "left", "rM1+&~", "park_trailing")
    fsm.go("park_trailing", "right", "sW~M1W}M", "restore_trailing")
    fsm.go("restore_trailing", "right", "r|", "output")
    fsm.go("output", "left", "s", "request")
    return fsm


def build_pipemask_room() -> list[str]:
    return _compile(_build_fsm())


CTRL_LEFT = 5
INPUT_ROW, OUTPUT_ROW = 2, 6
RING_OUT_ROW, RING_IN_ROW = 2, 9


def build_pipemask_rig() -> str:
    from .canvas import Canvas

    room = build_pipemask_room()
    right = CTRL_LEFT + len(room[0]) - 1
    relay_left = right + 5
    far = relay_left + 17
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
            (21, right + 2),
            (RING_IN_ROW, right + 2),
            (RING_IN_ROW, right + 1),
        ]
    )
    return cv.render()
