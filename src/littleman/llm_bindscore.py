"""Physical Manhattan/read-order score for LLM pipe binding."""

from __future__ import annotations

from .lllm_scan import _compile, _Fsm

DISPLAY = 16


def bindscore_reference(tokens: list[int]) -> list[int]:
    """Map repeated ``man_addr, endpoint_addr`` pairs to sortable scores."""
    if len(tokens) % 2:
        raise ValueError("bind-score input must contain address pairs")
    out = []
    for index in range(0, len(tokens), 2):
        man, endpoint = tokens[index : index + 2]
        mr, mc = divmod(man, DISPLAY)
        er, ec = divmod(endpoint, DISPLAY)
        out.append((abs(er - mr) + abs(ec - mc)) * 256 + endpoint)
    return out


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "man_r")

    # Scratch order after the prologue: man_row, man_col, endpoint,
    # endpoint_row, endpoint_col.
    fsm.go("man_r", "left", "rM", "man_div")
    fsm.go("man_div", "lit_r", " `0016`W/", "man_row_s")
    fsm.go("man_row_s", "right", "sW", "man_col_s")
    fsm.go("man_col_s", "right", "s", "endpoint_r")
    fsm.go("endpoint_r", "left", "rM", "endpoint_s")
    fsm.go("endpoint_s", "right", "s", "endpoint_div")
    fsm.go("endpoint_div", "lit_r", " `0016`W/", "endpoint_row_s")
    fsm.go("endpoint_row_s", "right", "sW", "endpoint_col_s")
    fsm.go("endpoint_col_s", "right", "s", "man_row_r")

    # Preserve man_col and endpoint while subtracting the rows.
    fsm.go("man_row_r", "right", "rM", "man_col_rotate")
    fsm.go("man_col_rotate", "right", "rs", "endpoint_rotate")
    fsm.go("endpoint_rotate", "right", "rs", "endpoint_row_r")
    fsm.go("endpoint_row_r", "right", "r-", "row_sign")
    fsm.sign(
        "row_sign",
        "right",
        "",
        neg="row_neg",
        zero="row_s",
        pos="row_s",
    )
    fsm.go("row_neg", "right", "N", "row_s")
    fsm.go("row_s", "right", "s", "endpoint_col_r")

    # Scratch is now endpoint_col, man_col, endpoint, row_distance.
    fsm.go("endpoint_col_r", "right", "rM", "man_col_r")
    fsm.go("man_col_r", "right", "r-", "col_sign")
    fsm.sign(
        "col_sign",
        "right",
        "",
        neg="col_neg",
        zero="col_s",
        pos="col_s",
    )
    fsm.go("col_neg", "right", "N", "col_s")
    fsm.go("col_s", "right", "s", "endpoint_again")

    # Scratch is endpoint, row_distance, col_distance. Compute
    # distance*256 + endpoint, which orders by distance then reading order.
    fsm.go("endpoint_again", "right", "rs", "row_distance")
    fsm.go("row_distance", "right", "rM", "col_distance")
    fsm.go("col_distance", "right", "r+M", "distance_scale")
    fsm.go("distance_scale", "lit_r", " `0256`*M", "endpoint_final")
    fsm.go("endpoint_final", "right", "r+", "score_out")
    fsm.go("score_out", "left", "s", "man_r")
    return fsm


def build_bindscore_room() -> list[str]:
    return _compile(_build_fsm())


CTRL_LEFT = 5
INPUT_ROW, OUTPUT_ROW = 2, 6
RING_OUT_ROW, RING_IN_ROW = 2, 9


def build_bindscore_rig() -> str:
    from .canvas import Canvas
    from .lllm_fetch import build_relay

    room = build_bindscore_room()
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
