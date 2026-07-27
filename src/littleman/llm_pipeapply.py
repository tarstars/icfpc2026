"""Apply one selected send/receive command to one normalized pipe record."""

from __future__ import annotations

from .lllm_scan import _compile, _Fsm
from .llm_pipetrace import PIPE_END
from .llm_statebuild import PIPE_DEST_STATE, PIPE_MASK, PIPE_VALUES

OP_SEND = 0
OP_RECV = 1
STATUS_BLOCKED = 0
STATUS_SENT = 1
STATUS_RECEIVED = 2
SCRATCH_END = -1


def pipeapply_reference(tokens: list[int]) -> list[int]:
    """Return the transformed record followed by ``status, result``."""
    op, value, start = tokens[:3]
    index = 3
    body = []
    while tokens[index] != PIPE_MASK:
        body.extend(tokens[index : index + 2])
        index += 2
    mask = tokens[index + 1]
    index += 2
    if tokens[index] != PIPE_VALUES:
        raise ValueError(f"missing values marker: {tokens[index]}")
    count = tokens[index + 1]
    values = list(tokens[index + 2 : index + 2 + count])
    index += 2 + count
    if tokens[index] != PIPE_END or index + 1 != len(tokens):
        raise ValueError("malformed pipe record")

    bits = body[1:-2:2]
    if body[-2] != PIPE_DEST_STATE:
        raise ValueError(f"missing destination marker: {body[-2]}")
    status = STATUS_BLOCKED
    result = 0
    if op == OP_SEND and not mask & bits[0]:
        mask |= bits[0]
        values.append(value)
        status = STATUS_SENT
    elif op == OP_RECV and mask & bits[-1]:
        mask &= ~bits[-1]
        result = values.pop(0)
        status = STATUS_RECEIVED
    elif op not in (OP_SEND, OP_RECV):
        raise ValueError(f"unknown pipe operation: {op}")

    return [
        start,
        *body,
        PIPE_MASK,
        mask,
        PIPE_VALUES,
        len(values),
        *values,
        PIPE_END,
        status,
        result,
    ]


def _counted_relay(
    fsm: _Fsm,
    prefix: str,
    *,
    done: str,
    drop_first: bool = False,
) -> None:
    first = f"{prefix}_drop" if drop_first else f"{prefix}_count"
    fsm.bp(prefix, "mid", "", zero=done, pos=first)
    if drop_first:
        fsm.go(first, "left", "r", f"{prefix}_dec")
    fsm.go(f"{prefix}_count", "left", "rs", f"{prefix}_dec")
    fsm.bp(
        f"{prefix}_dec",
        "mid",
        "m",
        zero=done,
        pos=f"{prefix}_count",
    )


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "op_r")
    fsm.go("op_r", "left", "r", "op_store")
    fsm.go("op_store", "right", "s", "command_value_r")
    fsm.go("command_value_r", "left", "r", "command_value_store")
    fsm.go("command_value_store", "right", "s", "start_r")
    fsm.go("start_r", "left", "r", "start_out")
    fsm.go("start_out", "left", "s", "cell_r")

    fsm.go("cell_r", "left", "r", "cell_cmp")
    fsm.sign(
        "cell_cmp",
        "lit_l",
        f"M`{PIPE_DEST_STATE:04d}`-",
        neg="cell_restore",
        zero="dest_restore",
        pos="cell_restore",
    )
    fsm.go("cell_restore", "left", "Ws", "bit_r")
    fsm.go("bit_r", "left", "r", "bit_out")
    fsm.go("bit_out", "left", "s", "bit_store")
    fsm.go("bit_store", "right", "s", "cell_r")
    fsm.go("dest_restore", "left", "Ws", "dest_value_r")
    fsm.go("dest_value_r", "left", "rs", "mask_marker_r")
    fsm.go("mask_marker_r", "left", "rs", "scratch_end")
    fsm.go("scratch_end", "right", "M1Ns", "mask_r")
    fsm.go("mask_r", "left", "r", "mask_store")
    fsm.go("mask_store", "right", "s", "op_get")

    fsm.go("op_get", "right", "r", "op_branch")
    fsm.sign(
        "op_branch",
        "right",
        "",
        neg="bad_op",
        zero="send_value_get",
        pos="recv_value_get",
    )
    fsm.go("bad_op", "right", "H", "bad_op")
    for op in ("send", "recv"):
        fsm.go(f"{op}_value_get", "right", "r", f"{op}_value_rotate")
        fsm.go(f"{op}_value_rotate", "right", "s", f"{op}_head_get")
        fsm.go(f"{op}_head_get", "right", "r", f"{op}_head_queue")
        fsm.go(f"{op}_head_queue", "right", "sM", f"{op}_bit_next")
        fsm.go(f"{op}_bit_next", "right", "r", f"{op}_bit_cmp")
        fsm.sign(
            f"{op}_bit_cmp",
            "right",
            "",
            neg=f"{op}_mask_get",
            zero="bad_op",
            pos=f"{op}_bit_keep",
        )
        fsm.go(f"{op}_bit_keep", "right", "M", f"{op}_bit_next")

    # Send: preserve head and mask through the occupancy test.
    fsm.go("send_mask_get", "right", "r", "send_mask_queue")
    fsm.go("send_mask_queue", "right", "s", "send_value_rotate_2")
    fsm.go("send_value_rotate_2", "right", "rs", "send_head_get_2")
    fsm.go("send_head_get_2", "right", "rM", "send_mask_restore")
    fsm.go("send_mask_restore", "right", "r", "send_head_test")
    fsm.go("send_head_test", "right", "Ws&", "send_head_branch")
    fsm.sign(
        "send_head_branch",
        "right",
        "",
        neg="bad_op",
        zero="send_free_rotate",
        pos="send_blocked_out",
    )
    fsm.go("send_free_rotate", "right", "rs", "send_free_head")
    fsm.go("send_free_head", "right", "r+", "send_free_mask_out")
    fsm.go("send_free_mask_out", "left", "s", "send_status_store")
    fsm.go("send_status_store", "right", "1s", "send_values_marker_r")

    fsm.go("send_blocked_out", "left", "Ws", "send_blocked_rotate")
    fsm.go("send_blocked_rotate", "right", "rs", "send_blocked_head_drop")
    fsm.go("send_blocked_head_drop", "right", "r", "send_blocked_status")
    fsm.go("send_blocked_status", "right", "0s", "send_values_marker_r")

    # Receive: tail is in B when the scratch sentinel is reached.
    fsm.go("recv_mask_get", "right", "r", "recv_tail_queue")
    fsm.go("recv_tail_queue", "right", "Ws&", "recv_tail_branch")
    fsm.sign(
        "recv_tail_branch",
        "right",
        "",
        neg="bad_op",
        zero="recv_blocked_out",
        pos="recv_success_rotate",
    )
    fsm.go("recv_success_rotate", "right", "rs", "recv_success_head_drop")
    fsm.go("recv_success_head_drop", "right", "r", "recv_success_tail")
    fsm.go("recv_success_tail", "right", "rW-", "recv_success_mask_out")
    fsm.go("recv_success_mask_out", "left", "s", "recv_status_store")
    fsm.go("recv_status_store", "right", "2s", "recv_values_marker_r")

    fsm.go("recv_blocked_out", "left", "Ws", "recv_blocked_rotate")
    fsm.go("recv_blocked_rotate", "right", "rs", "recv_blocked_head_drop")
    fsm.go("recv_blocked_head_drop", "right", "r", "recv_blocked_tail_drop")
    fsm.go("recv_blocked_tail_drop", "right", "r", "recv_blocked_status")
    fsm.go("recv_blocked_status", "right", "0s", "recv_values_marker_r")

    for op in ("send", "recv"):
        fsm.go(f"{op}_values_marker_r", "left", "rs", f"{op}_count_r")
        fsm.go(f"{op}_count_r", "left", "rMb", f"{op}_scratch_value")
        fsm.go(f"{op}_scratch_value", "right", "rs", f"{op}_status_get")
        fsm.go(f"{op}_status_get", "right", "r", f"{op}_status_branch")
        fsm.sign(
            f"{op}_status_branch",
            "right",
            "",
            neg="bad_op",
            zero=f"{op}_blocked_count",
            pos=f"{op}_success_count",
        )

        fsm.go(
            f"{op}_blocked_count",
            "left",
            "WMs",
            f"{op}_blocked_value_drop",
        )
        fsm.go(
            f"{op}_blocked_value_drop",
            "right",
            "r",
            f"{op}_blocked_relay",
        )
        _counted_relay(
            fsm,
            f"{op}_blocked_relay",
            done=f"{op}_blocked_end_r",
        )
        fsm.go(f"{op}_blocked_end_r", "left", "r", f"{op}_blocked_end_out")
        fsm.go(
            f"{op}_blocked_end_out",
            "lit_l",
            "M`3000`Ns0s0s",
            "op_r",
        )

    fsm.go("send_success_count", "left", "WM1+Ms", "send_success_relay")
    _counted_relay(
        fsm,
        "send_success_relay",
        done="send_append_value",
    )
    fsm.go("send_append_value", "right", "r", "send_append_out")
    fsm.go("send_append_out", "left", "s", "send_success_end")
    fsm.go("send_success_end", "left", "r", "send_success_end_out")
    fsm.go("send_success_end_out", "left", "s1s0s", "op_r")

    fsm.go("recv_success_count", "left", "WM1W-Msm", "recv_dummy_drop")
    fsm.go("recv_dummy_drop", "right", "r", "recv_response_r")
    fsm.go("recv_response_r", "left", "r", "recv_response_store")
    fsm.go("recv_response_store", "right", "s", "recv_success_relay")
    _counted_relay(
        fsm,
        "recv_success_relay",
        done="recv_success_end_r",
    )
    fsm.go("recv_success_end_r", "left", "r", "recv_success_end_out")
    fsm.go("recv_success_end_out", "left", "s2s", "recv_result")
    fsm.go("recv_result", "right", "r", "recv_result_out")
    fsm.go("recv_result_out", "left", "s", "op_r")
    return fsm


def build_pipeapply_room() -> list[str]:
    return _compile(_build_fsm())


CTRL_LEFT = 5
INPUT_ROW, OUTPUT_ROW = 2, 6
RING_OUT_ROW, RING_IN_ROW = 2, 9


def build_pipeapply_rig() -> str:
    from .canvas import Canvas
    from .lllm_fetch import build_relay

    room = build_pipeapply_room()
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
