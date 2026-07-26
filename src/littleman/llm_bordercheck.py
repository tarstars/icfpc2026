"""Physical destination-wall ownership predicate for normalized LLM rooms."""

from __future__ import annotations

from .lllm_scan import _compile, _Fsm


def bordercheck_reference(tokens: list[int]) -> list[int]:
    """Map repeated ``left,right,top,bottom,addr`` records to booleans.

    The first four fields use the normalized room grammar: left/right are on
    the man's row, while top/bottom are on the left wall. ``addr`` is known
    by construction to be a destination-wall address, so rectangle
    containment is sufficient to identify its owning room.
    """
    if len(tokens) % 5:
        raise ValueError("border-check input must contain five-token records")
    out = []
    for index in range(0, len(tokens), 5):
        left, right, top, bottom, addr = tokens[index : index + 5]
        row, col = divmod(addr, 16)
        out.append(
            int(top // 16 <= row <= bottom // 16 and left % 16 <= col <= right % 16)
        )
    return out


def _drain(fsm: _Fsm, name: str, count: int) -> None:
    target = f"{name}_out"
    fsm.go(name, "right", "r" * count, target)
    fsm.go(target, "left", "0s", "left_r")


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "left_r")
    for name, target in (("left", "right_r"), ("right", "top_r")):
        fsm.go(f"{name}_r", "left", "rM", f"{name}_mask")
        fsm.go(f"{name}_mask", "lit_r", " `0015`&", f"{name}_s")
        fsm.go(f"{name}_s", "right", "s", target)
    for name, target in (("top", "bottom_r"), ("bottom", "addr_r")):
        fsm.go(f"{name}_r", "left", "rM", f"{name}_div")
        fsm.go(f"{name}_div", "lit_r", " `0016`W/", f"{name}_s")
        fsm.go(f"{name}_s", "right", "s", target)
    fsm.go("addr_r", "left", "rM", "addr_div")
    fsm.go("addr_div", "lit_r", " `0016`W/", "addr_row_s")
    fsm.go("addr_row_s", "right", "sW", "addr_col_s")
    fsm.go("addr_col_s", "right", "s", "lower_col_left")

    # Preserve the five values needed later while checking col >= left.
    fsm.go("lower_col_left", "right", "rM", "lower_col_rotate")
    fsm.go("lower_col_rotate", "right", "rsrsrsrsrs-", "lower_col_branch")
    fsm.sign(
        "lower_col_branch",
        "right",
        "",
        neg="fail5",
        zero="upper_col_right",
        pos="upper_col_right",
    )

    # Scratch: right, top, bottom, row, col. Check right >= col.
    fsm.go("upper_col_right", "right", "rM", "upper_col_rotate")
    fsm.go("upper_col_rotate", "right", "rsrsrsrW-", "upper_col_branch")
    fsm.sign(
        "upper_col_branch",
        "right",
        "",
        neg="fail3",
        zero="lower_row_top",
        pos="lower_row_top",
    )

    # Scratch: top, bottom, row. Check row >= top while preserving row.
    fsm.go("lower_row_top", "right", "rM", "lower_row_rotate")
    fsm.go("lower_row_rotate", "right", "rsrs-", "lower_row_branch")
    fsm.sign(
        "lower_row_branch",
        "right",
        "",
        neg="fail2",
        zero="upper_row_bottom",
        pos="upper_row_bottom",
    )

    # Scratch: bottom, row. Check bottom >= row.
    fsm.go("upper_row_bottom", "right", "rM", "upper_row_row")
    fsm.go("upper_row_row", "right", "rW-", "upper_row_branch")
    fsm.sign(
        "upper_row_branch",
        "right",
        "",
        neg="fail0",
        zero="success",
        pos="success",
    )
    fsm.go("success", "left", "1s", "left_r")
    _drain(fsm, "fail5", 5)
    _drain(fsm, "fail3", 3)
    _drain(fsm, "fail2", 2)
    fsm.go("fail0", "left", "0s", "left_r")
    return fsm


def build_bordercheck_room() -> list[str]:
    return _compile(_build_fsm())


CTRL_LEFT = 5
INPUT_ROW, OUTPUT_ROW = 2, 6
RING_OUT_ROW, RING_IN_ROW = 2, 9


def build_bordercheck_rig() -> str:
    from .canvas import Canvas
    from .lllm_fetch import build_relay

    room = build_bordercheck_room()
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
