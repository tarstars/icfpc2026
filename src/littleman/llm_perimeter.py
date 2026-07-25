"""Expand discovered LLM rooms into exterior pipe-start candidates."""

from __future__ import annotations

from .lllm_fetch import build_relay
from .lllm_scan import _Fsm, _compile
from .llm_cmpfetch import (
    CMD_ROW as FETCH_CMD_ROW,
    RESP_ROW as FETCH_RESP_ROW,
    build_compare_fetch_room,
)
from .llm_roomfind import SETUP_END, WORLD_WORDS

ROOM_END = -2000
KIND_PIPE = 1
KIND_UP = 2
KIND_DOWN = 3
KIND_LEFT = 4
KIND_RIGHT = 5
KIND_DASH = 6


def pack_candidate(kind: int, neighbor: int) -> int:
    """Preserve direction even when the exterior neighbor is off-canvas."""
    return kind * 1024 + neighbor + 256


def unpack_candidate(token: int) -> tuple[int, int]:
    kind, shifted = divmod(token, 1024)
    return kind, shifted - 256


def perimeter_reference(tokens: list[int]) -> list[int]:
    """Relay room tuples and append ordered exterior candidate requests."""
    out = list(tokens[:WORLD_WORDS])
    index = WORLD_WORDS
    while tokens[index] != SETUP_END:
        event, left_addr, right_addr, top_left, bottom_left = tokens[index : index + 5]
        index += 5
        out.extend((event, left_addr, right_addr, top_left, bottom_left))
        left = top_left % 16
        right = right_addr % 16
        top = top_left // 16
        bottom = bottom_left // 16
        out.extend(pack_candidate(KIND_UP, (top - 1) * 16 + col) for col in range(left, right + 1))
        out.extend(pack_candidate(KIND_RIGHT, row * 16 + right + 1) for row in range(top, bottom + 1))
        out.extend(pack_candidate(KIND_DOWN, (bottom + 1) * 16 + col) for col in range(right, left - 1, -1))
        out.extend(pack_candidate(KIND_LEFT, row * 16 + left - 1) for row in range(bottom, top - 1, -1))
        out.append(ROOM_END)
    return [*out, SETUP_END, *tokens[index + 1 :]]


def _literal(value: int) -> str:
    if value < 0:
        return f" `{-value:04d}`N"
    return f" `{value:04d}`"


def _step(fsm: _Fsm, name: str, delta: int, target: str, *, restore=False) -> None:
    prefix = "W" if restore else ""
    magnitude = abs(delta)
    if magnitude == 1:
        code = prefix + ("M1+" if delta > 0 else "M1W-")
        zone = "right"
    else:
        op = "+" if delta > 0 else "W-"
        code = prefix + f"M`{magnitude:04d}`{op}"
        zone = "lit_r"
        if restore:
            # Keep the literal tick at the compiler's fixed offset.
            fsm.go(name, "right", "W", name + "_restored")
            name = name + "_restored"
            code = f"M`{magnitude:04d}`{op}"
    fsm.go(name, zone, code, target)


def _query(fsm: _Fsm, name: str, kind: int, neg, zero, pos) -> None:
    fsm.sign(
        name,
        "lit_r",
        f"M`{kind * 256:04d}`+sr",
        neg=neg,
        zero=zero,
        pos=pos,
    )


def _emit(fsm: _Fsm, name: str, offset: int, target: str) -> None:
    fsm.go(
        name,
        "lit_l",
        f"M`{offset:04d}`+sW",
        target,
    )


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "load_r_0")
    for index in range(WORLD_WORDS):
        next_name = f"load_r_{index + 1}" if index + 1 < WORLD_WORDS else "item_r"
        fsm.go(f"load_r_{index}", "left", "r", f"load_fetch_{index}")
        fsm.go(f"load_fetch_{index}", "right", "s", f"load_out_{index}")
        fsm.go(f"load_out_{index}", "left", "s", next_name)

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
    fsm.go("event_out", "left", "Ws", "left_r")
    for name, next_name in (
        ("left", "right_r"),
        ("right", "top_r"),
        ("top", "bottom_r"),
        ("bottom", "topfind_seed"),
    ):
        fsm.go(f"{name}_r", "left", "r", f"{name}_out")
        fsm.go(f"{name}_out", "left", "s", next_name)

    # Re-find top-left from bottom-left; no rectangle storage is required.
    _step(fsm, "topfind_seed", -16, "topfind_query")
    _query(fsm, "topfind_query", KIND_PIPE, "top_found", "topfind_more", "top_found")
    _step(fsm, "topfind_more", -16, "topfind_query", restore=True)

    # Top edge: emit top-left, then '-' cells, then top-right '+'.
    fsm.go("top_found", "right", "W", "top_emit_first")
    _emit(fsm, "top_emit_first", KIND_UP * 1024 + 256 - 16, "top_step")
    _step(fsm, "top_step", 1, "top_query")
    _query(fsm, "top_query", KIND_DASH, "top_corner", "top_body", "top_corner")
    fsm.go("top_body", "right", "W", "top_emit_body")
    _emit(fsm, "top_emit_body", KIND_UP * 1024 + 256 - 16, "top_step")
    fsm.go("top_corner", "right", "W", "top_emit_corner")
    _emit(fsm, "top_emit_corner", KIND_UP * 1024 + 256 - 16, "right_emit_first")

    # Right edge, including both corners.
    _emit(fsm, "right_emit_first", KIND_RIGHT * 1024 + 256 + 1, "right_step")
    _step(fsm, "right_step", 16, "right_query")
    _query(fsm, "right_query", KIND_PIPE, "right_corner", "right_body", "right_corner")
    fsm.go("right_body", "right", "W", "right_emit_body")
    _emit(fsm, "right_emit_body", KIND_RIGHT * 1024 + 256 + 1, "right_step")
    fsm.go("right_corner", "right", "W", "right_emit_corner")
    _emit(fsm, "right_emit_corner", KIND_RIGHT * 1024 + 256 + 1, "bottom_emit_first")

    # Bottom edge, walked right-to-left.
    _emit(fsm, "bottom_emit_first", KIND_DOWN * 1024 + 256 + 16, "bottom_step")
    _step(fsm, "bottom_step", -1, "bottom_query")
    _query(fsm, "bottom_query", KIND_DASH, "bottom_corner", "bottom_body", "bottom_corner")
    fsm.go("bottom_body", "right", "W", "bottom_emit_body")
    _emit(fsm, "bottom_emit_body", KIND_DOWN * 1024 + 256 + 16, "bottom_step")
    fsm.go("bottom_corner", "right", "W", "bottom_emit_corner")
    _emit(fsm, "bottom_emit_corner", KIND_DOWN * 1024 + 256 + 16, "left_emit_first")

    # Left edge, walked bottom-to-top.
    _emit(fsm, "left_emit_first", KIND_LEFT * 1024 + 256 - 1, "left_step")
    _step(fsm, "left_step", -16, "left_query")
    _query(fsm, "left_query", KIND_PIPE, "left_corner", "left_body", "left_corner")
    fsm.go("left_body", "right", "W", "left_emit_body")
    _emit(fsm, "left_emit_body", KIND_LEFT * 1024 + 256 - 1, "left_step")
    fsm.go("left_corner", "right", "W", "left_emit_corner")
    _emit(fsm, "left_emit_corner", KIND_LEFT * 1024 + 256 - 1, "room_end")
    fsm.go("room_end", "lit_l", _literal(ROOM_END) + "s", "item_r")

    fsm.go("setup_end", "left", "Ws", "relay_r")
    fsm.go("relay_r", "left", "r", "relay_s")
    fsm.go("relay_s", "left", "s", "relay_r")
    return fsm


def build_perimeter_room() -> list[str]:
    return _compile(_build_fsm())


CTRL_LEFT = 5
CTRL_CMD_ROW, CTRL_RESP_ROW = 2, 9


def build_perimeter_rig() -> str:
    from .canvas import Canvas

    ctrl = build_perimeter_room()
    ctrl_right = CTRL_LEFT + len(ctrl[0]) - 1
    fetch_left = ctrl_right + 10
    fetch = build_compare_fetch_room()
    fetch_right = fetch_left + len(fetch[0]) - 1
    relay_left = fetch_right + 5
    far = relay_left + 17
    cv = Canvas()
    cv.put(0, CTRL_LEFT, ctrl)
    cv.put(0, fetch_left, fetch)
    cv.put(20, relay_left, build_relay().render())
    cv.put(1, 0, ["+-+", "|I|", "+-+"])
    cv.put(5, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(2, 3), (2, CTRL_LEFT - 1)])
    cv.pipe([(6, CTRL_LEFT - 1), (6, 3)])
    cv.pipe([(CTRL_CMD_ROW, ctrl_right + 1), (CTRL_CMD_ROW, fetch_left - 1)])
    cv.pipe(
        [
            (FETCH_RESP_ROW, fetch_left - 1),
            (FETCH_RESP_ROW, ctrl_right + 4),
            (CTRL_RESP_ROW, ctrl_right + 4),
            (CTRL_RESP_ROW, ctrl_right + 1),
        ]
    )
    cv.pipe([(2, fetch_right + 1), (2, far), (21, far), (21, relay_left + 6)])
    cv.pipe([(21, relay_left - 1), (21, fetch_right + 2), (9, fetch_right + 2), (9, fetch_right + 1)])
    return cv.render()
