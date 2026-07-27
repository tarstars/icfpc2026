"""Pack one indexed LLM room header for the action coordinator."""

from __future__ import annotations

from .canvas import Canvas
from .lllm_fetch import build_relay
from .lllm_scan import _compile, _Fsm
from .llm_components import CLASS_RECV, CLASS_SEND
from .llm_packedcandidate import pack_room_context
from .llm_pipeapply import OP_RECV, OP_SEND

HEADER_WORDS = 11
RESPONSE_WORDS = 4


def roomcontext_reference(tokens: list[int]) -> list[int]:
    """Map headers to ``active, packed_context, ctrl, A`` records."""
    if len(tokens) % HEADER_WORDS:
        raise ValueError("truncated room-context request")
    out = []
    for index in range(0, len(tokens), HEADER_WORDS):
        event, left, right, top, bottom, ctrl, addr, _bi, ai, _old, record = (
            tokens[index : index + HEADER_WORDS]
        )
        cls = (record & 255) >> 4
        op = {CLASS_SEND: OP_SEND, CLASS_RECV: OP_RECV}.get(cls)
        if ctrl & 4 or op is None:
            out.extend((0, 0, 0, 0))
            continue
        context = pack_room_context(op, event, left, right, top, bottom, addr)
        out.extend((1, context, ctrl, ai))
    return out


def _scale(fsm: _Fsm, name: str, factor: int, target: str) -> None:
    fsm.go(name, "right", "rM", f"{name}_mul")
    fsm.go(f"{name}_mul", "lit_r", f" `{factor}`W*s", target)


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "field_r_0")
    for index in range(HEADER_WORDS):
        target = f"field_r_{index + 1}" if index < HEADER_WORDS - 1 else "record_r"
        fsm.go(f"field_r_{index}", "left", "r", f"field_s_{index}")
        fsm.go(f"field_s_{index}", "right", "s", target)

    # Rotate the record to the head and classify only send/receive.
    fsm.go("record_r", "right", "rs" * 5, "record_rotate")
    fsm.go("record_rotate", "right", "rs" * 5 + "rM", "record_mask")
    fsm.go("record_mask", "lit_r", " `0255`W&", "record_div")
    fsm.go("record_div", "lit_r", "M`0016`W/", "send_cmp")
    fsm.go("send_cmp", "mid", "M9W-", "class_branch")
    fsm.sign(
        "class_branch",
        "mid",
        "",
        neg="inactive_drop",
        zero="send_op",
        pos="recv_cmp",
    )
    fsm.go("recv_cmp", "mid", "M1W-", "recv_branch")
    fsm.sign(
        "recv_branch",
        "mid",
        "",
        neg="inactive_drop",
        zero="recv_op",
        pos="inactive_drop",
    )
    fsm.go("send_op", "right", "0s", "ctrl_rotate")
    fsm.go("recv_op", "right", "1s", "ctrl_rotate")

    # Ring is the ten header fields followed by op. Rotate to ctrl, preserve
    # it, and reject a stopped man before emitting an active response.
    fsm.go("ctrl_rotate", "right", "rs" * 5, "ctrl_r")
    fsm.go("ctrl_r", "right", "rMs", "ctrl_mask")
    fsm.go("ctrl_mask", "lit_r", "M`0004`W&", "ctrl_branch")
    fsm.sign(
        "ctrl_branch",
        "mid",
        "",
        neg="bad_ctrl",
        zero="active_out",
        pos="inactive_drop_11",
    )
    fsm.go("bad_ctrl", "right", "H", "bad_ctrl")
    fsm.go("inactive_drop", "right", "r" * 10, "inactive_out")
    fsm.go("inactive_drop_11", "right", "r" * 11, "inactive_out")
    fsm.go("inactive_out", "left", "0s0s0s0s", "field_r_0")

    fsm.go("active_out", "left", "1s", "addr_scale")

    # Ring:
    # addr, B, A, old, event, left, right, top, bottom, op, ctrl.
    _scale(fsm, "addr_scale", 1 << 41, "bi_drop")
    fsm.go("bi_drop", "right", "r", "ai_rotate")
    fsm.go("ai_rotate", "right", "rs", "old_drop")
    fsm.go("old_drop", "right", "r", "op_rotate_early")
    fsm.go("op_rotate_early", "right", "rs", "event_scale")
    fsm.go("event_scale", "right", "rNM1W-M+s", "left_scale")
    _scale(fsm, "left_scale", 1 << 9, "right_scale")
    _scale(fsm, "right_scale", 1 << 17, "top_scale")
    _scale(fsm, "top_scale", 1 << 25, "bottom_scale")
    _scale(fsm, "bottom_scale", 1 << 33, "op_rotate")
    fsm.go("op_rotate", "right", "rs", "context_addr")

    # Ring:
    # scaled_addr, A, scaled_event, scaled_left, scaled_right, scaled_top,
    # scaled_bottom, op, ctrl.
    fsm.go("context_addr", "right", "rM", "ai_rotate_tail")
    fsm.go("ai_rotate_tail", "right", "rs", "context_add_0")
    for index in range(6):
        target = f"context_add_{index + 1}" if index < 5 else "context_out"
        fsm.go(f"context_add_{index}", "right", "r+M", target)
    fsm.go("context_out", "left", "s", "ctrl_out_r")
    fsm.go("ctrl_out_r", "right", "r", "ctrl_out")
    fsm.go("ctrl_out", "left", "s", "ai_out_r")
    fsm.go("ai_out_r", "right", "r", "ai_out")
    fsm.go("ai_out", "left", "s", "field_r_0")
    return fsm


def build_roomcontext_room() -> list[str]:
    return _compile(_build_fsm())


CTRL_LEFT = 5
INPUT_ROW, OUTPUT_ROW = 2, 6
RING_OUT_ROW, RING_IN_ROW = 2, 9


def build_roomcontext_rig() -> str:
    room = build_roomcontext_room()
    right = CTRL_LEFT + len(room[0]) - 1
    relay_left = right + 5
    far = relay_left + 17
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
            (21, right + 2),
            (RING_IN_ROW, right + 2),
            (RING_IN_ROW, right + 1),
        ]
    )
    return cv.render()
