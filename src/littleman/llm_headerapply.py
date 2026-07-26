"""Apply selected pipe status/result to one indexed room header."""

from __future__ import annotations

from .canvas import Canvas
from .lllm_fetch import build_relay
from .lllm_scan import _compile, _Fsm, _layout
from .llm_indexdecision import _indexed_end, _relay_indexed
from .llm_manstep import STEP_DELTA
from .llm_pipeaction import parse_fetched_state, serialize_fetched_state
from .llm_pipeapply import OP_RECV, OP_SEND, STATUS_BLOCKED
from .llm_selectedreplace import HEADER_PREFIX_WORDS
from .llm_stateindex import stateindex_reference, stateunindex_reference


def headerapply_reference(tokens: list[int], room_no: int) -> list[int]:
    out = []
    index = 0
    while index < len(tokens):
        active, op, ctrl, _ai, status, result = tokens[
            index : index + HEADER_PREFIX_WORDS
        ]
        index += HEADER_PREFIX_WORDS
        end = _indexed_end(tokens, index)
        state = list(tokens[index:end])
        index = end
        if active and status != STATUS_BLOCKED:
            normalized = stateunindex_reference(state)
            rooms, pipes = parse_fetched_state(normalized)
            if room_no >= len(rooms):
                raise ValueError(f"active room is absent: {room_no}")
            room = rooms[room_no]
            if ctrl != room.ctrl:
                raise ValueError(f"control mismatch: {ctrl} != {room.ctrl}")
            room.addr += STEP_DELTA[ctrl & 3]
            if op == OP_RECV:
                room.ai = result
            elif op != OP_SEND:
                raise ValueError(f"unknown selected operation: {op}")
            state = stateindex_reference(serialize_fetched_state(rooms, pipes))
        out.extend(state)
    return out


def _build_fsm(room_no: int) -> _Fsm:
    if room_no not in range(3):
        raise ValueError(f"room number outside physical range: {room_no}")
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "active_r")
    fsm.go("active_r", "left", "r", "active_branch")
    fsm.sign(
        "active_branch",
        "mid",
        "",
        neg="bad_stream",
        zero="inactive_drop",
        pos="op_r",
    )
    fsm.go("inactive_drop", "left", "r" * 5, "relay_header_r")

    fsm.go("op_r", "left", "r", "op_store")
    fsm.go("op_store", "right", "s", "ctrl_ai_drop")
    fsm.go("ctrl_ai_drop", "left", "rr", "status_r")
    fsm.go("status_r", "left", "r", "status_branch")
    fsm.sign(
        "status_branch",
        "mid",
        "",
        neg="bad_stream",
        zero="blocked_result_drop",
        pos="result_r",
    )
    fsm.go("blocked_result_drop", "left", "r", "blocked_op_drop")
    fsm.go("blocked_op_drop", "right", "r", "relay_header_r")
    fsm.go("result_r", "left", "r", "result_store")
    fsm.go("result_store", "right", "s", "op_rotate")
    fsm.go("op_rotate", "right", "rs", "prior_0" if room_no else "target_static")

    for index in range(room_no):
        target = f"prior_{index + 1}" if index + 1 < room_no else "target_static"
        fsm.go(f"prior_{index}", "left", "rs" * 6, f"prior_tail_{index}")
        fsm.go(f"prior_tail_{index}", "left", "rs" * 6, target)

    # Event plus four bounds are unchanged.
    fsm.go("target_static", "left", "rs" * 5, "target_ctrl")
    fsm.go("target_ctrl", "left", "rbs", "target_addr")
    fsm.go("target_addr", "left", "r", "move_0")
    for heading in range(4):
        if heading < 3:
            fsm.bp(
                f"move_{heading}",
                "mid",
                "",
                zero=f"move_arm_{heading}",
                pos=f"move_dec_{heading}",
            )
            fsm.go(f"move_dec_{heading}", "mid", "m", f"move_{heading + 1}")
        else:
            fsm.go(f"move_{heading}", "mid", "", f"move_arm_{heading}")
        code = {
            0: "M`0016`N+s",
            1: "M1+s",
            2: "M`0016`+s",
            3: "M1N+s",
        }[heading]
        zone = "lit_l" if "`" in code else "left"
        fsm.go(f"move_arm_{heading}", zone, code, "target_bi")

    fsm.go("target_bi", "left", "rs", "result_rotate")
    fsm.go("result_rotate", "right", "rs", "op_get")
    fsm.go("op_get", "right", "rb", "op_branch")
    fsm.bp(
        "op_branch",
        "mid",
        "",
        zero="send_ai",
        pos="recv_ai_drop",
    )
    fsm.go("send_ai", "left", "rs", "send_result_drop")
    fsm.go("send_result_drop", "right", "r", "target_tail")
    fsm.go("recv_ai_drop", "left", "r", "recv_result")
    fsm.go("recv_result", "right", "r", "recv_ai_out")
    fsm.go("recv_ai_out", "left", "s", "target_tail")
    fsm.go("target_tail", "left", "rs" * 3, "relay_header_r")

    _relay_indexed(fsm, "active_r", consume_tail=False)
    fsm.go("bad_stream", "left", "H", "bad_stream")
    return fsm


def build_headerapply_room(room_no: int) -> list[str]:
    return _compile(_build_fsm(room_no), extra_gap=96)


def _port_rows(room_no: int) -> tuple[int, int, int, int]:
    fsm = _build_fsm(room_no)
    _routes, blocks, _height = _layout(fsm)
    groups = ([], [], [], [])
    main_in, main_out, scratch_out, scratch_in = groups
    for name, zone, code, _kind, _targets in fsm.blocks:
        (scratch_in if zone == "right" else main_in).extend(
            [blocks[name]] * code.count("r")
        )
        (scratch_out if zone == "right" else main_out).extend(
            [blocks[name]] * code.count("s")
        )

    def middle(rows):
        return (min(rows) + max(rows)) // 2

    return tuple(middle(rows) for rows in groups)


def build_headerapply_rig(room_no: int) -> str:
    room = build_headerapply_room(room_no)
    left = 5
    right = left + len(room[0]) - 1
    relay_left = right + 5
    far = relay_left + 17
    input_row, output_row, scratch_out, scratch_in = _port_rows(room_no)
    relay_top = (scratch_out + scratch_in) // 2 - 1
    relay_row = relay_top + 1
    cv = Canvas()
    cv.put(0, left, room)
    cv.put(relay_top, relay_left, build_relay().render())
    cv.put(input_row - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(output_row - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(input_row, 3), (input_row, left - 1)])
    cv.pipe([(output_row, left - 1), (output_row, 3)])
    cv.pipe(
        [
            (scratch_out, right + 1),
            (scratch_out, far),
            (relay_row, far),
            (relay_row, relay_left + 6),
        ]
    )
    cv.pipe(
        [
            (relay_row, relay_left - 1),
            (relay_row, right + 2),
            (scratch_in, right + 2),
            (scratch_in, right + 1),
        ]
    )
    return cv.render()
