"""Two-word physical pipe-candidate service for the indexed LLM coordinator."""

from __future__ import annotations

from .lllm_scan import _compile, _Fsm
from .llm_bordercheck import bordercheck_reference
from .llm_pipeapply import OP_RECV, OP_SEND

BYTE_MASK = 255


def pack_room_context(
    op: int,
    event: int,
    left: int,
    right: int,
    top: int,
    bottom: int,
    addr: int,
) -> int:
    """Pack the fixed room fields needed for candidate selection."""
    if op not in (OP_SEND, OP_RECV):
        raise ValueError(f"unknown pipe operation: {op}")
    event_addr = -event - 1
    fields = (event_addr, left, right, top, bottom, addr)
    if any(not 0 <= item <= BYTE_MASK for item in fields):
        raise ValueError(f"room context field outside byte range: {fields}")
    return (
        op
        | (event_addr << 1)
        | (left << 9)
        | (right << 17)
        | (top << 25)
        | (bottom << 33)
        | (addr << 41)
    )


def unpack_room_context(token: int) -> tuple[int, int, int, int, int, int, int]:
    op = token & 1
    event = -(((token >> 1) & BYTE_MASK) + 1)
    return (
        op,
        event,
        (token >> 9) & BYTE_MASK,
        (token >> 17) & BYTE_MASK,
        (token >> 25) & BYTE_MASK,
        (token >> 33) & BYTE_MASK,
        (token >> 41) & BYTE_MASK,
    )


def pack_pipe_context(source_event: int, head: int, tail: int, dest: int) -> int:
    source_addr = -source_event - 1
    fields = (source_addr, head, tail, dest)
    if any(not 0 <= item <= BYTE_MASK for item in fields):
        raise ValueError(f"pipe context field outside byte range: {fields}")
    return source_addr | (head << 8) | (tail << 16) | (dest << 24)


def unpack_pipe_context(token: int) -> tuple[int, int, int, int]:
    return tuple((token >> shift) & BYTE_MASK for shift in (0, 8, 16, 24))


def packedcandidate_reference(tokens: list[int]) -> list[int]:
    if len(tokens) % 2:
        raise ValueError("packed candidate input must contain word pairs")
    out = []
    for index in range(0, len(tokens), 2):
        op, event, left, right, top, bottom, _addr = unpack_room_context(tokens[index])
        source_addr, head, tail, dest = unpack_pipe_context(tokens[index + 1])
        if op == OP_SEND:
            target = head
            eligible = int(source_addr == -event - 1)
        else:
            target = tail
            eligible = bordercheck_reference([left, right, top, bottom, dest])[0]
        out.extend((target, eligible))
    return out


def _decode_ring_byte(
    fsm: _Fsm,
    name: str,
    shift: int,
    target: str,
) -> None:
    first = f"{name}_div" if shift else f"{name}_mask"
    fsm.go(name, "right", "rM", first)
    if shift:
        fsm.go(f"{name}_div", "lit_r", f" `{1 << shift:04d}`W/", f"{name}_mask")
    fsm.go(f"{name}_mask", "lit_r", "M`0255`W&", target)


def _drain_failure(fsm: _Fsm, name: str, count: int) -> None:
    fsm.go(name, "right", "r" * count, f"{name}_out")
    fsm.go(f"{name}_out", "left", "0s", "context_r")


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "context_r")
    fsm.go("context_r", "left", "r", "context_s")
    fsm.go("context_s", "right", "s", "pipe_r")
    fsm.go("pipe_r", "left", "r", "pipe_s")
    fsm.go("pipe_s", "right", "s", "op_context_r")

    # Keep the two-word ring in (pipe, context) order after decoding op.
    fsm.go("op_context_r", "right", "r", "op_context_s")
    fsm.go("op_context_s", "right", "s", "op_mask")
    fsm.go("op_mask", "lit_r", "M`0001`W&", "op_branch")
    fsm.sign(
        "op_branch",
        "mid",
        "",
        neg="bad_op",
        zero="send_pipe_rotate",
        pos="recv_pipe_rotate",
    )
    fsm.go("bad_op", "right", "H", "bad_op")

    # SEND: decode event, source and head, then compare event/source.
    fsm.go("send_pipe_rotate", "right", "rs", "send_event")
    _decode_ring_byte(fsm, "send_event", 1, "send_event_s")
    fsm.go("send_event_s", "right", "s", "send_pipe_dup_r")
    fsm.go("send_pipe_dup_r", "right", "r", "send_pipe_dup_s")
    fsm.go("send_pipe_dup_s", "right", "ss", "send_event_rotate")
    fsm.go("send_event_rotate", "right", "rs", "send_source")
    _decode_ring_byte(fsm, "send_source", 0, "send_source_s")
    fsm.go("send_source_s", "right", "s", "send_head")
    _decode_ring_byte(fsm, "send_head", 8, "send_head_s")
    fsm.go("send_head_s", "right", "s", "send_event_cmp_r")
    fsm.go("send_event_cmp_r", "right", "rM", "send_source_cmp_r")
    fsm.go("send_source_cmp_r", "right", "r-", "send_compare")
    fsm.sign(
        "send_compare",
        "mid",
        "",
        neg="send_ineligible_target",
        zero="send_eligible_target",
        pos="send_ineligible_target",
    )
    fsm.go("send_ineligible_target", "right", "r", "send_ineligible_out")
    fsm.go("send_ineligible_out", "left", "s0s", "context_r")
    fsm.go("send_eligible_target", "right", "r", "send_eligible_out")
    fsm.go("send_eligible_out", "left", "s1s", "context_r")

    # RECV: turn (pipe, context) into
    # (left, right, top, bottom, dest, target).
    fsm.go("recv_pipe_rotate", "right", "rs", "recv_context_r")
    fsm.go("recv_context_r", "right", "r", "recv_context_dup")
    fsm.go("recv_context_dup", "right", "ssss", "recv_pipe_rotate_2")
    fsm.go("recv_pipe_rotate_2", "right", "rs", "recv_ctx_left")
    for name, shift, target in (
        ("recv_ctx_left", 9, "recv_ctx_left_s"),
        ("recv_ctx_right", 17, "recv_ctx_right_s"),
        ("recv_ctx_top", 25, "recv_ctx_top_s"),
        ("recv_ctx_bottom", 33, "recv_ctx_bottom_s"),
    ):
        _decode_ring_byte(fsm, name, shift, target)
        next_name = {
            "recv_ctx_left": "recv_ctx_right",
            "recv_ctx_right": "recv_ctx_top",
            "recv_ctx_top": "recv_ctx_bottom",
            "recv_ctx_bottom": "recv_pipe_dup_r",
        }[name]
        fsm.go(target, "right", "s", next_name)
    fsm.go("recv_pipe_dup_r", "right", "r", "recv_pipe_dup_s")
    fsm.go("recv_pipe_dup_s", "right", "ss", "recv_bound_rotate_0")
    for index in range(4):
        target = f"recv_bound_rotate_{index + 1}" if index < 3 else "recv_dest"
        fsm.go(f"recv_bound_rotate_{index}", "right", "rs", target)
    _decode_ring_byte(fsm, "recv_dest", 24, "recv_dest_s")
    fsm.go("recv_dest_s", "right", "s", "recv_target")
    _decode_ring_byte(fsm, "recv_target", 16, "recv_target_s")
    fsm.go("recv_target_s", "right", "s", "recv_target_rotate_0")
    for index in range(5):
        target = f"recv_target_rotate_{index + 1}" if index < 4 else "recv_target_r"
        fsm.go(f"recv_target_rotate_{index}", "right", "rs", target)
    fsm.go("recv_target_r", "right", "r", "recv_target_out")
    fsm.go("recv_target_out", "left", "s", "recv_left_r")

    # Inline BORDERCHECK while the already-emitted target is not in scratch.
    for name, target in (("left", "recv_right_r"), ("right", "recv_top_r")):
        fsm.go(f"recv_{name}_r", "right", "rM", f"recv_{name}_mask")
        fsm.go(f"recv_{name}_mask", "lit_r", "M`0015`W&", f"recv_{name}_s")
        fsm.go(f"recv_{name}_s", "right", "s", target)
    for name, target in (("top", "recv_bottom_r"), ("bottom", "recv_addr_r")):
        fsm.go(f"recv_{name}_r", "right", "rM", f"recv_{name}_div")
        fsm.go(f"recv_{name}_div", "lit_r", " `0016`W/", f"recv_{name}_s")
        fsm.go(f"recv_{name}_s", "right", "s", target)
    fsm.go("recv_addr_r", "right", "rM", "recv_addr_div")
    fsm.go("recv_addr_div", "lit_r", " `0016`W/", "recv_addr_row_s")
    fsm.go("recv_addr_row_s", "right", "sW", "recv_addr_col_s")
    fsm.go("recv_addr_col_s", "right", "s", "recv_lower_col_left")

    fsm.go("recv_lower_col_left", "right", "rM", "recv_lower_col_rotate")
    fsm.go(
        "recv_lower_col_rotate",
        "right",
        "rsrsrsrsrs-",
        "recv_lower_col_branch",
    )
    fsm.sign(
        "recv_lower_col_branch",
        "right",
        "",
        neg="recv_fail5",
        zero="recv_upper_col_right",
        pos="recv_upper_col_right",
    )
    fsm.go("recv_upper_col_right", "right", "rM", "recv_upper_col_rotate")
    fsm.go(
        "recv_upper_col_rotate",
        "right",
        "rsrsrsrW-",
        "recv_upper_col_branch",
    )
    fsm.sign(
        "recv_upper_col_branch",
        "right",
        "",
        neg="recv_fail3",
        zero="recv_lower_row_top",
        pos="recv_lower_row_top",
    )
    fsm.go("recv_lower_row_top", "right", "rM", "recv_lower_row_rotate")
    fsm.go(
        "recv_lower_row_rotate",
        "right",
        "rsrs-",
        "recv_lower_row_branch",
    )
    fsm.sign(
        "recv_lower_row_branch",
        "right",
        "",
        neg="recv_fail2",
        zero="recv_upper_row_bottom",
        pos="recv_upper_row_bottom",
    )
    fsm.go("recv_upper_row_bottom", "right", "rM", "recv_upper_row_row")
    fsm.go("recv_upper_row_row", "right", "rW-", "recv_upper_row_branch")
    fsm.sign(
        "recv_upper_row_branch",
        "right",
        "",
        neg="recv_fail0",
        zero="recv_success",
        pos="recv_success",
    )
    fsm.go("recv_success", "left", "1s", "context_r")
    _drain_failure(fsm, "recv_fail5", 5)
    _drain_failure(fsm, "recv_fail3", 3)
    _drain_failure(fsm, "recv_fail2", 2)
    fsm.go("recv_fail0", "left", "0s", "context_r")
    return fsm


def build_packedcandidate_room() -> list[str]:
    return _compile(_build_fsm())


CTRL_LEFT = 5
INPUT_ROW, OUTPUT_ROW = 2, 6
RING_OUT_ROW, RING_IN_ROW = 2, 9


def build_packedcandidate_rig() -> str:
    from .canvas import Canvas
    from .lllm_fetch import build_relay

    room = build_packedcandidate_room()
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
