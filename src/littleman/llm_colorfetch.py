"""Raw-world service returning static DRAW colors for packed addresses."""

from __future__ import annotations

from .lllm_fetch import build_relay
from .lllm_scan import _compile, _Fsm
from .llm import (
    COLOR_ARITH,
    COLOR_ARROW,
    COLOR_DIGIT,
    COLOR_M,
    COLOR_SPACE,
    COLOR_SR,
)
from .llm_rawfetch import unpack_raw_world

WORLD_TOKENS = 64

COLOR_CLASSIFICATION = {
    **{ord(char): COLOR_ARROW for char in "^>vV<XH"},
    **{ord(char): COLOR_DIGIT for char in "0123456789"},
    ord("M"): COLOR_M,
    ord("+"): COLOR_ARITH,
    ord("-"): COLOR_ARITH,
    ord("s"): COLOR_SR,
    ord("r"): COLOR_SR,
}


def colorfetch_reference(world: list[int], requests: list[int]) -> list[int]:
    """Requests are ``addr*16`` so callers can keep a packed-delta counter."""
    raw = unpack_raw_world(world)
    return [
        COLOR_CLASSIFICATION.get(raw[packed // 16] & 0xFF, COLOR_SPACE)
        for packed in requests
    ]


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "lit_l", "@`0064`b", "load_r")
    fsm.go("load_r", "left", "r", "load_s")
    fsm.go("load_s", "right", "s", "load_count")
    fsm.bp("load_count", "mid", "m", zero="marker", pos="load_r")
    fsm.go("marker", "lit_r", " `0001`Ns", "request")

    fsm.go("request", "left", "rM", "request_div")
    fsm.go("request_div", "lit_r", " `0016`W/", "chain_a")
    fsm.go("chain_a", "right", "M8W+M4W/bWM", "chain_b")
    fsm.go("chain_b", "lit_r", " `0010`*M1{M", "align")
    fsm.sign(
        "align",
        "right",
        "r",
        neg="align_marker",
        zero="align_word",
        pos="align_word",
    )
    fsm.go("align_word", "right", "s", "align")
    fsm.go("align_marker", "right", "s", "rotate")
    fsm.bp("rotate", "mid", "m", zero="peel_a", pos="rotate_token")
    fsm.go("rotate_token", "right", "rs", "rotate")
    fsm.go("peel_a", "right", "/M", "peel_b")
    fsm.go("peel_b", "lit_r", " `1023`&", "class_0")

    entries = sorted(COLOR_CLASSIFICATION.items())
    for index, (char, color) in enumerate(entries):
        next_name = (
            f"class_{index + 1}" if index + 1 < len(entries) else "class_default"
        )
        fsm.sign(
            f"class_{index}",
            "lit_l",
            f"M`{char:04d}`W-",
            neg=f"class_restore_{index}",
            zero=f"class_match_{index}",
            pos=f"class_restore_{index}",
        )
        fsm.go(f"class_restore_{index}", "left", "+", next_name)
        fsm.go(
            f"class_match_{index}",
            "lit_l",
            f" `{color:04d}`",
            "output",
        )
    fsm.go("class_default", "left", "0", "output")
    fsm.go("output", "left", "s", "restore")
    fsm.sign(
        "restore",
        "right",
        "r",
        neg="restore_marker",
        zero="restore_word",
        pos="restore_word",
    )
    fsm.go("restore_word", "right", "s", "restore")
    fsm.go("restore_marker", "right", "s", "request")
    return fsm


def build_colorfetch_room() -> list[str]:
    return _compile(_build_fsm())


FETCH_LEFT = 5
CMD_ROW, RESP_ROW = 2, 6
RING_OUT_ROW, RING_IN_ROW = 2, 9


def build_colorfetch_rig() -> str:
    from .canvas import Canvas

    room = build_colorfetch_room()
    right = FETCH_LEFT + len(room[0]) - 1
    relay_left = right + 5
    far = relay_left + 17
    cv = Canvas()
    cv.put(0, FETCH_LEFT, room)
    cv.put(20, relay_left, build_relay().render())
    cv.put(CMD_ROW - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(RESP_ROW - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(CMD_ROW, 3), (CMD_ROW, FETCH_LEFT - 1)])
    cv.pipe([(RESP_ROW, FETCH_LEFT - 1), (RESP_ROW, 3)])
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
