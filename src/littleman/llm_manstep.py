"""One non-pipe interpreted-man tick as a physical stream component."""

from __future__ import annotations

from .lllm_scan import _compile, _Fsm
from .llm_components import (
    CLASS_ADD,
    CLASS_BRANCH,
    CLASS_DIGIT,
    CLASS_HALT,
    CLASS_HEADING,
    CLASS_M,
    CLASS_RECV,
    CLASS_SEND,
    CLASS_SPACE,
    CLASS_SUB,
)
from .sim import wrap64

RING_SIZE = 6
STEP_DELTA = (-16, 1, 16, -1)


def manstep_reference(state: list[int], record: int) -> list[int]:
    """Transform ``CTRL,ADDR,BI,AI,OLD,K`` for one live non-pipe op."""
    ctrl, addr, bi, ai, old, count = state
    cls, value = (record & 255) >> 4, record & 15
    if cls == CLASS_HALT:
        ctrl |= 4
        return [ctrl, addr, bi, ai, old, count]
    if cls == CLASS_HEADING:
        ctrl = value
    elif cls == CLASS_DIGIT:
        ai = value
    elif cls == CLASS_M:
        bi = ai
    elif cls == CLASS_ADD:
        ai = wrap64(ai + bi)
    elif cls == CLASS_SUB:
        ai = wrap64(ai - bi)
    elif cls == CLASS_BRANCH:
        if ai:
            ctrl = (ctrl + (1 if ai > 0 else -1)) & 3
    elif cls in (CLASS_SEND, CLASS_RECV):
        return [ctrl, addr, bi, ai, old, count]
    elif cls != CLASS_SPACE:
        raise ValueError(f"unsupported manstep class: {cls}")
    addr += STEP_DELTA[ctrl]
    return [ctrl, addr, bi, ai, old, count]


def _relay(count: int) -> str:
    return "rs" * count


def _class_code(cls: int) -> str | None:
    if cls == CLASS_SPACE:
        return ""
    if cls == CLASS_HALT:
        return "rM4+s" + _relay(5)
    if cls == CLASS_HEADING:
        return "rWs" + _relay(5)
    if cls == CLASS_DIGIT:
        return _relay(3) + "rWs" + _relay(2)
    if cls == CLASS_M:
        return _relay(2) + "rrMss" + _relay(2)
    if cls == CLASS_ADD:
        return _relay(2) + "rMsr+s" + _relay(2)
    if cls == CLASS_SUB:
        return _relay(2) + "rMsr-s" + _relay(2)
    return None


def _move_arm(fsm: _Fsm, heading: int) -> None:
    start = f"move_arm_{heading}"
    if heading in (0, 2):
        fsm.go(start, "right", "rM", f"{start}_delta")
        sign = "N" if heading == 0 else ""
        fsm.go(f"{start}_delta", "lit_r", f" `0016`{sign}+s", f"{start}_tail")
    else:
        sign = "N" if heading == 3 else ""
        fsm.go(start, "right", f"rM1{sign}+s", f"{start}_tail")
    fsm.go(f"{start}_tail", "right", _relay(4), "output_0")


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "state_r_0")
    for index in range(RING_SIZE):
        target = f"state_r_{index + 1}" if index + 1 < RING_SIZE else "record_r"
        fsm.go(f"state_r_{index}", "left", "r", f"state_s_{index}")
        fsm.go(f"state_s_{index}", "right", "s", target)

    fsm.go("record_r", "left", "rM", "record_mask")
    fsm.go("record_mask", "lit_r", " `0255`W&M", "record_div")
    fsm.go("record_div", "lit_r", " `0016`W/b", "class_0")
    for cls in range(CLASS_RECV + 1):
        if cls < CLASS_RECV:
            fsm.bp(
                f"class_{cls}",
                "mid",
                "",
                zero=f"class_arm_{cls}",
                pos=f"class_dec_{cls}",
            )
            fsm.go(f"class_dec_{cls}", "mid", "m", f"class_{cls + 1}")
        else:
            fsm.go(f"class_{cls}", "mid", "", f"class_arm_{cls}")

        code = _class_code(cls)
        if cls in (CLASS_SEND, CLASS_RECV):
            fsm.go(f"class_arm_{cls}", "right", "", "output_0")
        elif code is None:
            fsm.go(f"class_arm_{cls}", "right", "", "branch_read")
        elif cls == CLASS_HALT:
            fsm.go(f"class_arm_{cls}", "right", code, "output_0")
        else:
            fsm.go(f"class_arm_{cls}", "right", code, "move_seed")

    fsm.go(
        "branch_read",
        "right",
        _relay(3) + "rMs" + _relay(2) + "W",
        "branch_sign",
    )
    fsm.sign(
        "branch_sign",
        "right",
        "",
        neg="branch_neg",
        zero="move_seed",
        pos="branch_pos",
    )
    fsm.go("branch_neg", "right", "rM3+M4W%s", "branch_neg_tail")
    fsm.go("branch_neg_tail", "right", _relay(5), "move_seed")
    fsm.go("branch_pos", "right", "rM1+M4W%s", "branch_pos_tail")
    fsm.go("branch_pos_tail", "right", _relay(5), "move_seed")

    fsm.go("move_seed", "right", "rsb", "move_0")
    for heading in range(4):
        if heading < 3:
            fsm.bp(
                f"move_{heading}",
                "mid",
                "",
                zero=f"move_arm_{heading}",
                pos=f"move_dec_{heading}",
            )
            fsm.go(
                f"move_dec_{heading}",
                "mid",
                "m",
                f"move_{heading + 1}",
            )
        else:
            fsm.go(f"move_{heading}", "mid", "", f"move_arm_{heading}")
        _move_arm(fsm, heading)

    for index in range(RING_SIZE):
        target = f"output_{index + 1}" if index + 1 < RING_SIZE else "state_r_0"
        fsm.go(f"output_{index}", "right", "r", f"output_s_{index}")
        fsm.go(f"output_s_{index}", "left", "s", target)
    return fsm


def build_manstep_room() -> list[str]:
    return _compile(_build_fsm())


CTRL_LEFT = 5
INPUT_ROW, OUTPUT_ROW = 2, 6
RING_OUT_ROW, RING_IN_ROW = 2, 9


def build_manstep_rig() -> str:
    from .canvas import Canvas
    from .lllm_fetch import build_relay

    room = build_manstep_room()
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
