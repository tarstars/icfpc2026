"""Call the composed selector for one prepared indexed decision."""

from __future__ import annotations

from .canvas import Canvas
from .lllm_scan import _compile, _Fsm, _layout
from .llm_candidateselect import (
    add_candidateselect_network,
    candidateselect_reference,
)
from .llm_decisionprep import PREP_WORDS
from .llm_indexdecision import _indexed_end, _relay_indexed

OUTPUT_WORDS = 5


def decisionselect_reference(tokens: list[int]) -> list[int]:
    """Emit ``active, op, ctrl, A, selected, indexed_state``."""
    out = []
    index = 0
    while index < len(tokens):
        active, op, ctrl, ai, context0, pipe0, context1, pipe1 = tokens[
            index : index + PREP_WORDS
        ]
        index += PREP_WORDS
        end = _indexed_end(tokens, index)
        state = tokens[index:end]
        index = end
        if active:
            selected = candidateselect_reference(
                [context0, pipe0, context1, pipe1]
            )[0]
            out.extend((1, op, ctrl, ai, selected))
        else:
            out.extend((0,) * OUTPUT_WORDS)
        out.extend(state)
    return out


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "active_r")
    fsm.go("active_r", "left", "r", "active_branch")
    fsm.sign(
        "active_branch",
        "mid",
        "",
        neg="bad_request",
        zero="inactive_drop",
        pos="active_out",
    )
    fsm.go("bad_request", "left", "H", "bad_request")
    fsm.go("inactive_drop", "left", "r" * 7, "inactive_out")
    fsm.go("inactive_out", "left", "0s" * OUTPUT_WORDS, "relay_header_r")

    fsm.go("active_out", "left", "1s", "op_relay")
    for name, target in (
        ("op", "ctrl_relay"),
        ("ctrl", "ai_relay"),
        ("ai", "request_r_0"),
    ):
        fsm.go(f"{name}_relay", "left", "rs", target)
    for index in range(4):
        target = f"request_r_{index + 1}" if index < 3 else "response_r"
        fsm.go(f"request_r_{index}", "left", "r", f"request_s_{index}")
        fsm.go(f"request_s_{index}", "right", "s", target)
    fsm.go("response_r", "right", "r", "response_out")
    fsm.go("response_out", "left", "s", "relay_header_r")

    _relay_indexed(fsm, "active_r", consume_tail=False)
    fsm.go("bad_stream", "left", "H", "bad_stream")
    return fsm


def build_decisionselect_room() -> list[str]:
    return _compile(_build_fsm(), extra_gap=96)


def _port_rows() -> tuple[int, int, int, int]:
    fsm = _build_fsm()
    _routes, blocks, _height = _layout(fsm)
    service_writes = {f"request_s_{index}" for index in range(4)}
    service_reads = {"response_r"}
    groups = ([], [], [], [])
    main_in, main_out, command, response = groups
    for name, _zone, code, _kind, _targets in fsm.blocks:
        (response if name in service_reads else main_in).extend(
            [blocks[name]] * code.count("r")
        )
        (command if name in service_writes else main_out).extend(
            [blocks[name]] * code.count("s")
        )

    def middle(rows):
        return (min(rows) + max(rows)) // 2

    return tuple(middle(rows) for rows in groups)


def build_decisionselect_rig() -> str:
    ctrl = build_decisionselect_room()
    left = 5
    ctrl_right = left + len(ctrl[0]) - 1
    service_left = ctrl_right + 40
    service_top = len(ctrl) + 20
    input_row, output_row, command_row, response_row = _port_rows()
    cv = Canvas()
    cv.put(0, left, ctrl)
    ingress, egress = add_candidateselect_network(
        cv,
        top=service_top,
        left=service_left,
    )
    cv.put(input_row - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(output_row - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(input_row, 3), (input_row, left - 1)])
    cv.pipe([(output_row, left - 1), (output_row, 3)])
    command_track = service_left - 6
    response_track = service_left - 10
    cv.pipe(
        [
            (command_row, ctrl_right + 1),
            (command_row, command_track),
            (ingress[0], command_track),
            ingress,
        ]
    )
    cv.pipe(
        [
            egress,
            (egress[0], response_track),
            (response_row, response_track),
            (response_row, ctrl_right + 1),
        ]
    )
    return cv.render()
