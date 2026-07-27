"""Filter one LLM pipe summary for a send/receive binding request."""

from __future__ import annotations

from .canvas import Canvas
from .lllm_fetch import build_relay
from .lllm_scan import _compile, _Fsm
from .llm_bordercheck import bordercheck_reference, build_bordercheck_room
from .llm_pipeapply import OP_RECV, OP_SEND

REQUEST_WORDS = 9


def pipecandidate_reference(tokens: list[int]) -> list[int]:
    """Map records to ``target_endpoint, eligible`` pairs.

    Record grammar:
    ``op, room_no, source_no, left, right, top, bottom, dest_addr, target``.
    For sends, source equality decides eligibility. For receives, destination
    wall ownership decides it.
    """
    if len(tokens) % REQUEST_WORDS:
        raise ValueError("truncated pipe-candidate request")
    out = []
    for index in range(0, len(tokens), REQUEST_WORDS):
        op, room, source, left, right, top, bottom, dest, target = tokens[
            index : index + REQUEST_WORDS
        ]
        if op == OP_SEND:
            eligible = int(source == room)
        elif op == OP_RECV:
            eligible = bordercheck_reference([left, right, top, bottom, dest])[0]
        else:
            raise ValueError(f"unknown pipe operation: {op}")
        out.extend((target, eligible))
    return out


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "op_r")
    fsm.sign(
        "op_r",
        "left",
        "r",
        neg="bad_op",
        zero="send_room_r",
        pos="recv_room_drop",
    )
    fsm.go("bad_op", "left", "H", "bad_op")

    fsm.go("send_room_r", "left", "rM", "send_source_r")
    fsm.go("send_source_r", "left", "r-", "send_source_cmp")
    fsm.sign(
        "send_source_cmp",
        "left",
        "",
        neg="send_ineligible_skip",
        zero="send_eligible_skip",
        pos="send_ineligible_skip",
    )
    fsm.go("send_ineligible_skip", "left", "rrrrr", "send_ineligible_target")
    fsm.go("send_ineligible_target", "left", "rs0s", "op_r")
    fsm.go("send_eligible_skip", "left", "rrrrr", "send_eligible_target")
    fsm.go("send_eligible_target", "left", "rs1s", "op_r")

    fsm.go("recv_room_drop", "left", "rr", "recv_bound_r_0")
    for index in range(5):
        target = f"recv_bound_r_{index + 1}" if index < 4 else "recv_target_r"
        fsm.go(f"recv_bound_r_{index}", "left", "r", f"recv_bound_s_{index}")
        fsm.go(f"recv_bound_s_{index}", "right", "s", target)
    fsm.go("recv_target_r", "left", "rM", "recv_eligible_r")
    fsm.go("recv_eligible_r", "right", "r", "recv_target_out")
    fsm.go("recv_target_out", "left", "WsW", "recv_eligible_out")
    fsm.go("recv_eligible_out", "left", "s", "op_r")
    return fsm


def build_pipecandidate_room() -> list[str]:
    return _compile(_build_fsm())


CTRL_LEFT = 5
INPUT_ROW, OUTPUT_ROW = 2, 6
CTRL_CMD_ROW, CTRL_RESP_ROW = 2, 9


def build_pipecandidate_rig() -> str:
    ctrl = build_pipecandidate_room()
    ctrl_right = CTRL_LEFT + len(ctrl[0]) - 1
    service_left = ctrl_right + 10
    service = build_bordercheck_room()
    service_right = service_left + len(service[0]) - 1
    relay_left = service_right + 5
    far = relay_left + 17
    cv = Canvas()
    cv.put(0, CTRL_LEFT, ctrl)
    cv.put(0, service_left, service)
    cv.put(20, relay_left, build_relay().render())
    cv.put(INPUT_ROW - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(OUTPUT_ROW - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(INPUT_ROW, 3), (INPUT_ROW, CTRL_LEFT - 1)])
    cv.pipe([(OUTPUT_ROW, CTRL_LEFT - 1), (OUTPUT_ROW, 3)])
    cv.pipe([(CTRL_CMD_ROW, ctrl_right + 1), (CTRL_CMD_ROW, service_left - 1)])
    cv.pipe(
        [
            (6, service_left - 1),
            (6, ctrl_right + 4),
            (CTRL_RESP_ROW, ctrl_right + 4),
            (CTRL_RESP_ROW, ctrl_right + 1),
        ]
    )
    cv.pipe(
        [
            (2, service_right + 1),
            (2, far),
            (21, far),
            (21, relay_left + 6),
        ]
    )
    cv.pipe(
        [
            (21, relay_left - 1),
            (21, service_right + 2),
            (9, service_right + 2),
            (9, service_right + 1),
        ]
    )
    return cv.render()
