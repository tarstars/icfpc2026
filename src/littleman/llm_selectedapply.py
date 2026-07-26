"""Apply one selected pipe record from a duplicated indexed state."""

from __future__ import annotations

from .canvas import Canvas
from .lllm_fetch import build_relay
from .lllm_scan import _compile, _Fsm, _layout
from .llm_actioncopy import ACTION_PREFIX_WORDS
from .llm_indexcopy import INDEX_COPY_END, INDEX_COPY_SPLIT
from .llm_indexdecision import (
    _headers_and_pipes,
    _indexed_end,
    _relay_indexed,
)
from .llm_pipeapply import build_pipeapply_room, pipeapply_reference
from .llm_pipetrace import PIPE_END
from .llm_roomfind import SETUP_END
from .llm_statebuild import PIPE_MASK, PIPE_VALUES
from .llm_stateindex import INDEX_END, INDEX_SPLIT


def selectedapply_reference(tokens: list[int]) -> list[int]:
    """Emit prefix, record-present, updated record, status/result, and state."""
    out = []
    index = 0
    while index < len(tokens):
        prefix = list(tokens[index : index + ACTION_PREFIX_WORDS])
        if len(prefix) != ACTION_PREFIX_WORDS:
            raise ValueError("truncated selected-action prefix")
        index += ACTION_PREFIX_WORDS
        first_end = _indexed_end(tokens, index)
        first = tokens[index:first_end]
        index = first_end
        if tokens[index] != INDEX_COPY_SPLIT:
            raise ValueError("missing selected-action copy split")
        index += 1
        second_end = _indexed_end(tokens, index)
        second = tokens[index:second_end]
        index = second_end
        if tokens[index] != INDEX_COPY_END:
            raise ValueError("missing selected-action copy end")
        index += 1
        if first != second:
            raise ValueError("selected-action copies disagree")

        active, op, _ctrl, ai, selected = prefix
        if not active:
            out.extend((*prefix, 0, 0, 0, *second))
            continue
        _headers, records = _headers_and_pipes(first)
        if selected not in range(len(records)):
            raise ValueError(f"selected pipe is absent: {selected}")
        record = records[selected]
        response = pipeapply_reference([op, ai, record[0], *record[2:]])
        out.extend((*prefix, 1, record[1], *response, *second))
    return out


def _drop_record(fsm: _Fsm, prefix: str, target: str) -> None:
    fsm.go(f"{prefix}_source", "left", "r", f"{prefix}_body_r")
    fsm.go(f"{prefix}_body_r", "left", "r", f"{prefix}_body_cmp")
    fsm.sign(
        f"{prefix}_body_cmp",
        "lit_l",
        f"M`{abs(PIPE_MASK)}`+",
        neg="bad_stream",
        zero=f"{prefix}_mask",
        pos=f"{prefix}_bit",
    )
    fsm.go(f"{prefix}_bit", "left", "r", f"{prefix}_body_r")
    fsm.go(f"{prefix}_mask", "left", "r", f"{prefix}_values_marker")
    fsm.go(f"{prefix}_values_marker", "left", "r", f"{prefix}_count")
    fsm.go(f"{prefix}_count", "left", "rb", f"{prefix}_values")
    fsm.bp(
        f"{prefix}_values",
        "mid",
        "",
        zero=f"{prefix}_end",
        pos=f"{prefix}_value",
    )
    fsm.go(f"{prefix}_value", "left", "r", f"{prefix}_value_dec")
    fsm.bp(
        f"{prefix}_value_dec",
        "mid",
        "m",
        zero=f"{prefix}_end",
        pos=f"{prefix}_value",
    )
    fsm.go(f"{prefix}_end", "left", "r", target)


def _drop_indexed(fsm: _Fsm, prefix: str, target: str) -> None:
    fsm.go(f"{prefix}_header_r", "left", "r", f"{prefix}_header_cmp")
    fsm.sign(
        f"{prefix}_header_cmp",
        "lit_l",
        f"M`{abs(SETUP_END)}`+",
        neg="bad_stream",
        zero=f"{prefix}_split",
        pos=f"{prefix}_header_tail",
    )
    fsm.go(
        f"{prefix}_header_tail",
        "left",
        "r" * 11,
        f"{prefix}_header_r",
    )
    fsm.go(f"{prefix}_split", "left", "r", f"{prefix}_pipe_start")
    fsm.go(
        f"{prefix}_pipe_start",
        "left",
        "r",
        f"{prefix}_pipe_start_cmp",
    )
    fsm.sign(
        f"{prefix}_pipe_start_cmp",
        "lit_l",
        f"M`{abs(INDEX_END)}`+",
        neg="bad_stream",
        zero=target,
        pos=f"{prefix}_record_source",
    )
    _drop_record(fsm, f"{prefix}_record", f"{prefix}_pipe_start")


def _drop_pipe_table(fsm: _Fsm, prefix: str, target: str) -> None:
    fsm.go(f"{prefix}_start", "left", "r", f"{prefix}_start_cmp")
    fsm.sign(
        f"{prefix}_start_cmp",
        "lit_l",
        f"M`{abs(INDEX_END)}`+",
        neg="bad_stream",
        zero=target,
        pos=f"{prefix}_record_source",
    )
    _drop_record(fsm, f"{prefix}_record", f"{prefix}_start")


def _apply_record(fsm: _Fsm, prefix: str, target: str) -> None:
    # Start is still in B after the indexed-end comparison. Append it behind
    # the preserved op/A pair, then send the command in service order.
    fsm.go(f"{prefix}_start_store", "right", "Ws", f"{prefix}_present")
    fsm.go(f"{prefix}_present", "left", "1s", f"{prefix}_scratch_op")
    for name, next_name in (
        ("op", "ai"),
        ("ai", "start"),
        ("start", "source"),
    ):
        fsm.go(
            f"{prefix}_scratch_{name}",
            "right",
            "r",
            f"{prefix}_command_{name}",
        )
        after = (
            f"{prefix}_scratch_{next_name}"
            if next_name != "source"
            else f"{prefix}_source_r"
        )
        fsm.go(f"{prefix}_command_{name}", "right", "s", after)

    fsm.go(f"{prefix}_source_r", "left", "r", f"{prefix}_source_out")
    fsm.go(f"{prefix}_source_out", "left", "s", f"{prefix}_body_r")
    fsm.go(f"{prefix}_body_r", "left", "r", f"{prefix}_body_cmp")
    fsm.sign(
        f"{prefix}_body_cmp",
        "lit_l",
        f"M`{abs(PIPE_MASK)}`+",
        neg="bad_stream",
        zero=f"{prefix}_mask_restore",
        pos=f"{prefix}_body_restore",
    )
    fsm.go(f"{prefix}_body_restore", "right", "Ws", f"{prefix}_bit_r")
    fsm.go(f"{prefix}_bit_r", "left", "r", f"{prefix}_bit_s")
    fsm.go(f"{prefix}_bit_s", "right", "s", f"{prefix}_body_r")
    fsm.go(f"{prefix}_mask_restore", "right", "Ws", f"{prefix}_mask_r")
    for name, next_name in (
        ("mask", "values_marker"),
        ("values_marker", "count"),
    ):
        fsm.go(f"{prefix}_{name}_r", "left", "r", f"{prefix}_{name}_s")
        fsm.go(
            f"{prefix}_{name}_s",
            "right",
            "s",
            f"{prefix}_{next_name}_r",
        )
    fsm.go(f"{prefix}_count_r", "left", "rMb", f"{prefix}_count_s")
    fsm.go(f"{prefix}_count_s", "right", "s", f"{prefix}_values")
    fsm.bp(
        f"{prefix}_values",
        "mid",
        "",
        zero=f"{prefix}_end_r",
        pos=f"{prefix}_value_r",
    )
    fsm.go(f"{prefix}_value_r", "left", "r", f"{prefix}_value_s")
    fsm.go(f"{prefix}_value_s", "right", "s", f"{prefix}_value_dec")
    fsm.bp(
        f"{prefix}_value_dec",
        "mid",
        "m",
        zero=f"{prefix}_end_r",
        pos=f"{prefix}_value_r",
    )
    fsm.go(f"{prefix}_end_r", "left", "r", f"{prefix}_end_s")
    fsm.go(f"{prefix}_end_s", "right", "s", f"{prefix}_response_start_r")

    fsm.go(
        f"{prefix}_response_start_r",
        "right",
        "r",
        f"{prefix}_response_start_out",
    )
    fsm.go(
        f"{prefix}_response_start_out",
        "left",
        "s",
        f"{prefix}_response_body_r",
    )
    fsm.go(
        f"{prefix}_response_body_r",
        "right",
        "r",
        f"{prefix}_response_body_cmp",
    )
    fsm.sign(
        f"{prefix}_response_body_cmp",
        "lit_r",
        f"M`{abs(PIPE_MASK)}`+",
        neg="bad_stream",
        zero=f"{prefix}_response_mask_restore",
        pos=f"{prefix}_response_body_restore",
    )
    fsm.go(
        f"{prefix}_response_body_restore",
        "left",
        "Ws",
        f"{prefix}_response_bit_r",
    )
    fsm.go(
        f"{prefix}_response_bit_r",
        "right",
        "r",
        f"{prefix}_response_bit_out",
    )
    fsm.go(
        f"{prefix}_response_bit_out",
        "left",
        "s",
        f"{prefix}_response_body_r",
    )
    fsm.go(
        f"{prefix}_response_mask_restore",
        "left",
        "Ws",
        f"{prefix}_response_mask_r",
    )
    for name, next_name in (
        ("mask", "values_marker"),
        ("values_marker", "count"),
    ):
        fsm.go(
            f"{prefix}_response_{name}_r",
            "right",
            "r",
            f"{prefix}_response_{name}_out",
        )
        fsm.go(
            f"{prefix}_response_{name}_out",
            "left",
            "s",
            f"{prefix}_response_{next_name}_r",
        )
    fsm.go(
        f"{prefix}_response_count_r",
        "right",
        "rMb",
        f"{prefix}_response_count_out",
    )
    fsm.go(
        f"{prefix}_response_count_out",
        "left",
        "s",
        f"{prefix}_response_values",
    )
    fsm.bp(
        f"{prefix}_response_values",
        "mid",
        "",
        zero=f"{prefix}_response_end_r",
        pos=f"{prefix}_response_value_r",
    )
    fsm.go(
        f"{prefix}_response_value_r",
        "right",
        "r",
        f"{prefix}_response_value_out",
    )
    fsm.go(
        f"{prefix}_response_value_out",
        "left",
        "s",
        f"{prefix}_response_value_dec",
    )
    fsm.bp(
        f"{prefix}_response_value_dec",
        "mid",
        "m",
        zero=f"{prefix}_response_end_r",
        pos=f"{prefix}_response_value_r",
    )
    fsm.go(
        f"{prefix}_response_end_r",
        "right",
        "r",
        f"{prefix}_response_end_out",
    )
    fsm.go(
        f"{prefix}_response_end_out",
        "left",
        "s",
        f"{prefix}_response_status_r",
    )
    fsm.go(
        f"{prefix}_response_status_r",
        "right",
        "r",
        f"{prefix}_response_status_out",
    )
    fsm.go(
        f"{prefix}_response_status_out",
        "left",
        "s",
        f"{prefix}_response_result_r",
    )
    fsm.go(
        f"{prefix}_response_result_r",
        "right",
        "r",
        f"{prefix}_response_result_out",
    )
    fsm.go(f"{prefix}_response_result_out", "left", "s", target)


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "active_r")
    fsm.go("active_r", "left", "r", "active_branch")
    fsm.sign(
        "active_branch",
        "mid",
        "",
        neg="bad_stream",
        zero="inactive_out",
        pos="active_out",
    )
    fsm.go("inactive_out", "left", "0s", "inactive_prefix")
    fsm.go("inactive_prefix", "left", "rs" * 4, "inactive_meta")
    fsm.go("inactive_meta", "left", "0s0s0s", "inactive_header_r")
    _drop_indexed(fsm, "inactive", "copy_split_r")

    fsm.go("active_out", "left", "1s", "op_r")
    fsm.go("op_r", "left", "r", "op_out")
    fsm.go("op_out", "left", "s", "op_store")
    fsm.go("op_store", "right", "s", "ctrl_relay")
    fsm.go("ctrl_relay", "left", "rs", "ai_r")
    fsm.go("ai_r", "left", "r", "ai_out")
    fsm.go("ai_out", "left", "s", "ai_store")
    fsm.go("ai_store", "right", "s", "selected_r")
    fsm.go("selected_r", "left", "rb", "selected_branch")
    fsm.sign(
        "selected_branch",
        "mid",
        "",
        neg="bad_stream",
        zero="selected_out",
        pos="selected_out",
    )
    fsm.go("selected_out", "left", "s", "active_header_r")

    fsm.go("active_header_r", "left", "r", "active_header_cmp")
    fsm.sign(
        "active_header_cmp",
        "lit_l",
        f"M`{abs(SETUP_END)}`+",
        neg="bad_stream",
        zero="active_split",
        pos="active_header_tail",
    )
    fsm.go("active_header_tail", "left", "r" * 11, "active_header_r")
    fsm.go("active_split", "left", "r", "pipe0_start")
    fsm.go("pipe0_start", "left", "r", "pipe0_start_cmp")
    fsm.sign(
        "pipe0_start_cmp",
        "lit_l",
        f"M`{abs(INDEX_END)}`+",
        neg="bad_stream",
        zero="bad_stream",
        pos="slot_branch",
    )
    fsm.bp(
        "slot_branch",
        "mid",
        "",
        zero="apply_start_store",
        pos="drop0_source",
    )
    _drop_record(fsm, "drop0", "pipe1_start")
    fsm.go("pipe1_start", "left", "r", "pipe1_start_cmp")
    fsm.sign(
        "pipe1_start_cmp",
        "lit_l",
        f"M`{abs(INDEX_END)}`+",
        neg="bad_stream",
        zero="bad_stream",
        pos="apply_start_store",
    )
    _apply_record(fsm, "apply", "post_start")
    _drop_pipe_table(fsm, "post", "copy_split_r")

    fsm.go("copy_split_r", "left", "r", "relay_header_r")
    _relay_indexed(fsm, "active_r")
    fsm.go("bad_stream", "left", "H", "bad_stream")
    return fsm


def build_selectedapply_room() -> list[str]:
    return _compile(_build_fsm(), extra_gap=128)


def _port_rows() -> tuple[int, int, int, int, int, int]:
    fsm = _build_fsm()
    _routes, blocks, _height = _layout(fsm)
    groups = ([], [], [], [], [], [])
    main_in, main_out, scratch_out, scratch_in, command, response = groups
    scratch_writes = {
        "op_store",
        "ai_store",
        "apply_start_store",
    }
    for name, zone, code, _kind, _targets in fsm.blocks:
        if name in scratch_writes:
            write_group = scratch_out
        elif name.startswith("apply_") and zone == "right" and "response" not in name:
            write_group = command
        else:
            write_group = main_out
        if name.startswith("apply_scratch_"):
            read_group = scratch_in
        elif name.startswith("apply_response_") and zone == "right":
            read_group = response
        else:
            read_group = main_in
        write_group.extend([blocks[name]] * code.count("s"))
        read_group.extend([blocks[name]] * code.count("r"))

    def middle(rows):
        return (min(rows) + max(rows)) // 2

    ports = [middle(rows) for rows in groups]
    # The three scratch writes are at rows 65, 73 and 134, immediately
    # followed by the apply-command send at 140. Row 108 is inside the
    # strict binding interval for all four operations.
    ports[2] = max(scratch_out) - 26
    return tuple(ports)


def _add_service_ring(cv: Canvas, *, top: int, right: int) -> None:
    relay_left = right + 5
    far = relay_left + 17
    cv.put(top + 20, relay_left, build_relay().render())
    cv.pipe(
        [
            (top + 2, right + 1),
            (top + 2, far),
            (top + 21, far),
            (top + 21, relay_left + 6),
        ]
    )
    cv.pipe(
        [
            (top + 21, relay_left - 1),
            (top + 21, right + 2),
            (top + 9, right + 2),
            (top + 9, right + 1),
        ]
    )


def build_selectedapply_rig() -> str:
    ctrl = build_selectedapply_room()
    service = build_pipeapply_room()
    left = 5
    ctrl_right = left + len(ctrl[0]) - 1
    scratch_relay_left = ctrl_right + 5
    scratch_far = scratch_relay_left + 17
    service_left = ctrl_right + 60
    service_top = len(ctrl) + 20
    service_right = service_left + len(service[0]) - 1
    input_row, output_row, scratch_out, scratch_in, command, response = _port_rows()
    scratch_relay_top = (scratch_out + scratch_in) // 2 - 1
    scratch_relay_row = scratch_relay_top + 1
    cv = Canvas()
    cv.put(0, left, ctrl)
    cv.put(service_top, service_left, service)
    cv.put(scratch_relay_top, scratch_relay_left, build_relay().render())
    cv.put(input_row - 1, 0, ["+-+", "|I|", "+-+"])
    output_box_row = output_row + 10
    cv.put(output_box_row - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(input_row, 3), (input_row, left - 1)])
    cv.pipe(
        [
            (output_row, left - 1),
            (output_box_row, left - 1),
            (output_box_row, 3),
        ]
    )
    cv.pipe(
        [
            (scratch_out, ctrl_right + 1),
            (scratch_out, scratch_far),
            (scratch_relay_row, scratch_far),
            (scratch_relay_row, scratch_relay_left + 6),
        ]
    )
    cv.pipe(
        [
            (scratch_relay_row, scratch_relay_left - 1),
            (scratch_relay_row, ctrl_right + 2),
            (scratch_in, ctrl_right + 2),
            (scratch_in, ctrl_right + 1),
        ]
    )
    command_track = service_left - 6
    response_track = service_left - 10
    cv.pipe(
        [
            (command, ctrl_right + 1),
            (command, command_track),
            (service_top + 2, command_track),
            (service_top + 2, service_left - 1),
        ]
    )
    cv.pipe(
        [
            (service_top + 6, service_left - 1),
            (service_top + 6, response_track),
            (response, response_track),
            (response, ctrl_right + 1),
        ]
    )
    _add_service_ring(cv, top=service_top, right=service_right)
    return cv.render()
