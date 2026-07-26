"""Physical exact wall-hit predicate for one normalized LLM room."""

from __future__ import annotations

from .lllm_scan import _compile, _Fsm


def wallhit_reference(tokens: list[int]) -> list[int]:
    """Map repeated ``left,right,top,bottom,addr`` records to booleans."""
    if len(tokens) % 5:
        raise ValueError("wall-hit input must contain five-token records")
    out = []
    for index in range(0, len(tokens), 5):
        left, right, top, bottom, addr = tokens[index : index + 5]
        row, col = divmod(addr, 16)
        out.append(
            int(col in (left % 16, right % 16) or row in (top // 16, bottom // 16))
        )
    return out


def _success(fsm: _Fsm, name: str, count: int) -> None:
    fsm.go(name, "right", "r" * count, f"{name}_out")
    fsm.go(f"{name}_out", "left", "1s", "left_r")


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
    fsm.go("addr_col_s", "right", "s", "left_col_r")

    # L,R,T,B,row,col -> compare col=L while preserving R,T,B,row,col.
    fsm.go("left_col_r", "right", "rM", "left_col_rotate")
    fsm.go("left_col_rotate", "right", "rsrsrsrsrs-", "left_col_cmp")
    fsm.sign(
        "left_col_cmp",
        "right",
        "",
        neg="right_col_r",
        zero="success5",
        pos="right_col_r",
    )

    # R,T,B,row,col -> compare col=R while preserving T,B,row,col.
    fsm.go("right_col_r", "right", "rM", "right_col_rotate")
    fsm.go("right_col_rotate", "right", "rsrsrsrs-", "right_col_cmp")
    fsm.sign(
        "right_col_cmp",
        "right",
        "",
        neg="top_row_r",
        zero="success4",
        pos="top_row_r",
    )

    # T,B,row,col -> compare row=T while preserving col,B,row.
    fsm.go("top_row_r", "right", "rM", "top_row_bottom")
    fsm.go("top_row_bottom", "right", "rs", "top_row_value")
    fsm.go("top_row_value", "right", "rs-", "top_row_cmp")
    fsm.sign(
        "top_row_cmp",
        "right",
        "",
        neg="bottom_col_drop",
        zero="success3",
        pos="bottom_col_drop",
    )

    # col,B,row -> compare row=B.
    fsm.go("bottom_col_drop", "right", "r", "bottom_row_r")
    fsm.go("bottom_row_r", "right", "rM", "row_r")
    fsm.go("row_r", "right", "r-", "bottom_row_cmp")
    fsm.sign(
        "bottom_row_cmp",
        "right",
        "",
        neg="miss",
        zero="success0",
        pos="miss",
    )
    fsm.go("miss", "left", "0s", "left_r")
    _success(fsm, "success5", 5)
    _success(fsm, "success4", 4)
    _success(fsm, "success3", 3)
    fsm.go("success0", "left", "1s", "left_r")
    return fsm


def build_wallhit_room() -> list[str]:
    return _compile(_build_fsm())


CTRL_LEFT = 5
INPUT_ROW, OUTPUT_ROW = 2, 6
RING_OUT_ROW, RING_IN_ROW = 2, 9


def build_wallhit_rig() -> str:
    from .canvas import Canvas
    from .lllm_fetch import build_relay

    room = build_wallhit_room()
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
