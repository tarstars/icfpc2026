"""Extract one room's fixed-width decision packet from an indexed state."""

from __future__ import annotations

from .canvas import Canvas
from .lllm_scan import _compile, _Fsm, _layout
from .llm_indexcopy import INDEX_COPY_END, INDEX_COPY_SPLIT
from .llm_packedcandidate import missing_pipe_context
from .llm_perimeter import ROOM_END
from .llm_pipecontext import (
    build_pipecontext_room,
    pipecontext_reference,
)
from .llm_pipetrace import PIPE_END
from .llm_roomcontext import (
    build_roomcontext_room,
    roomcontext_reference,
)
from .llm_roomfind import SETUP_END
from .llm_statebuild import PIPE_MASK, PIPE_VALUES
from .llm_stateindex import INDEX_END, INDEX_SPLIT

META_WORDS = 6


def _indexed_end(tokens: list[int], start: int = 0) -> int:
    """Return one past INDEX_END using grammar, not sentinel search."""
    index = start
    while tokens[index] != SETUP_END:
        index += 11
        if tokens[index] != ROOM_END:
            raise ValueError(f"missing indexed room end: {tokens[index]}")
        index += 1
    index += 1
    if tokens[index] != INDEX_SPLIT:
        raise ValueError(f"missing index split: {tokens[index]}")
    index += 1
    while tokens[index] != INDEX_END:
        index += 2
        while tokens[index] != PIPE_MASK:
            index += 2
        index += 2
        if tokens[index] != PIPE_VALUES:
            raise ValueError(f"missing pipe values: {tokens[index]}")
        count = tokens[index + 1]
        index += 2 + count
        if tokens[index] != PIPE_END:
            raise ValueError(f"missing pipe end: {tokens[index]}")
        index += 1
    return index + 1


def _headers_and_pipes(tokens: list[int]) -> tuple[list[list[int]], list[list[int]]]:
    headers = []
    index = 0
    while tokens[index] != SETUP_END:
        headers.append(list(tokens[index : index + 11]))
        index += 12
    index += 2
    pipes = []
    while tokens[index] != INDEX_END:
        start = index
        index += 2
        while tokens[index] != PIPE_MASK:
            index += 2
        index += 2
        count = tokens[index + 1]
        index += 2 + count + 1
        pipes.append(list(tokens[start:index]))
    return headers, pipes


def indexdecision_reference(tokens: list[int], room_no: int) -> list[int]:
    """Emit ``active, context, ctrl, A, pipe0, pipe1, indexed_state``."""
    first_end = _indexed_end(tokens)
    if tokens[first_end] != INDEX_COPY_SPLIT:
        raise ValueError(f"missing index-copy split: {tokens[first_end]}")
    second_start = first_end + 1
    second_end = _indexed_end(tokens, second_start)
    if tokens[second_end] != INDEX_COPY_END or second_end + 1 != len(tokens):
        raise ValueError("malformed index-copy tail")
    first = tokens[:first_end]
    second = tokens[second_start:second_end]
    if first != second:
        raise ValueError("indexed copies disagree")

    headers, records = _headers_and_pipes(first)
    if len(records) > 2:
        raise ValueError("LLM coordinator supports at most two pipes")
    meta = (
        roomcontext_reference(headers[room_no])
        if room_no < len(headers)
        else [0, 0, 0, 0]
    )
    pipes = [pipecontext_reference(record)[0] for record in records]
    pipes.extend([missing_pipe_context()] * (2 - len(pipes)))
    return [*meta, *pipes, *second]


def _skip_header(fsm: _Fsm, name: str, target: str) -> None:
    fsm.go(name, "left", "r" * 10, f"{name}_end")
    fsm.go(f"{name}_end", "left", "r", target)


def _pipe_record(fsm: _Fsm, slot: int, next_state: str) -> None:
    prefix = f"pipe_{slot}"
    fsm.go(f"{prefix}_start_restore", "right", "Ws", f"{prefix}_source_r")
    fsm.go(f"{prefix}_source_r", "left", "r", f"{prefix}_source_s")
    fsm.go(f"{prefix}_source_s", "right", "s", f"{prefix}_body_r")
    fsm.go(f"{prefix}_body_r", "left", "r", f"{prefix}_body_cmp")
    fsm.sign(
        f"{prefix}_body_cmp",
        "lit_r",
        f"M`{abs(PIPE_MASK)}`+",
        neg="bad_stream",
        zero=f"{prefix}_mask_restore",
        pos=f"{prefix}_body_restore",
    )
    fsm.go(f"{prefix}_body_restore", "right", "Ws", f"{prefix}_bit_r")
    fsm.go(f"{prefix}_bit_r", "left", "r", f"{prefix}_bit_s")
    fsm.go(f"{prefix}_bit_s", "right", "s", f"{prefix}_body_r")
    fsm.go(f"{prefix}_mask_restore", "right", "Ws", f"{prefix}_mask_r")
    fsm.go(f"{prefix}_mask_r", "left", "r", f"{prefix}_mask_s")
    fsm.go(f"{prefix}_mask_s", "right", "s", f"{prefix}_values_marker_r")
    fsm.go(
        f"{prefix}_values_marker_r",
        "left",
        "r",
        f"{prefix}_values_marker_s",
    )
    fsm.go(
        f"{prefix}_values_marker_s",
        "right",
        "s",
        f"{prefix}_count_r",
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
    fsm.go(f"{prefix}_end_s", "right", "s", f"{prefix}_response_r")
    fsm.go(f"{prefix}_response_r", "right", "r", f"{prefix}_response_out")
    fsm.go(f"{prefix}_response_out", "left", "s", next_state)


def _relay_indexed(
    fsm: _Fsm,
    done: str,
    *,
    consume_tail: bool = True,
) -> None:
    fsm.go("relay_header_r", "left", "r", "relay_header_cmp")
    fsm.sign(
        "relay_header_cmp",
        "lit_l",
        f"M`{abs(SETUP_END)}`+",
        neg="bad_stream",
        zero="relay_setup_restore",
        pos="relay_event_restore",
    )
    fsm.go("relay_event_restore", "left", "Ws", "relay_fields_0")
    fsm.go("relay_fields_0", "left", "rs" * 5, "relay_fields_1")
    fsm.go("relay_fields_1", "left", "rs" * 5, "relay_room_end")
    fsm.go("relay_room_end", "left", "rs", "relay_header_r")
    fsm.go("relay_setup_restore", "left", "Ws", "relay_split")
    fsm.go("relay_split", "left", "rs", "relay_pipe_start")

    fsm.go("relay_pipe_start", "left", "r", "relay_pipe_start_cmp")
    fsm.sign(
        "relay_pipe_start_cmp",
        "lit_l",
        f"M`{abs(INDEX_END)}`+",
        neg="bad_stream",
        zero="relay_index_end",
        pos="relay_pipe_start_restore",
    )
    fsm.go("relay_pipe_start_restore", "left", "Wsrs", "relay_body_r")
    fsm.go("relay_body_r", "left", "r", "relay_body_cmp")
    fsm.sign(
        "relay_body_cmp",
        "lit_l",
        f"M`{abs(PIPE_MASK)}`+",
        neg="bad_stream",
        zero="relay_mask_restore",
        pos="relay_body_restore",
    )
    fsm.go("relay_body_restore", "left", "Wsrs", "relay_body_r")
    fsm.go("relay_mask_restore", "left", "Wsrsrs", "relay_count_r")
    fsm.go("relay_count_r", "left", "rMbs", "relay_values")
    fsm.bp(
        "relay_values",
        "mid",
        "",
        zero="relay_pipe_end",
        pos="relay_value",
    )
    fsm.go("relay_value", "left", "rs", "relay_value_dec")
    fsm.bp(
        "relay_value_dec",
        "mid",
        "m",
        zero="relay_pipe_end",
        pos="relay_value",
    )
    fsm.go("relay_pipe_end", "left", "rs", "relay_pipe_start")
    after_index = "relay_copy_end" if consume_tail else done
    fsm.go("relay_index_end", "left", "Ws", after_index)
    if consume_tail:
        fsm.go("relay_copy_end", "left", "r", done)


def _build_fsm(room_no: int) -> _Fsm:
    if room_no not in range(3):
        raise ValueError(f"room number outside physical range: {room_no}")
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "header_start_0")
    for index in range(room_no + 1):
        name = f"header_start_{index}"
        positive = "target_event_restore" if index == room_no else f"skip_{index}"
        fsm.go(name, "left", "r", f"{name}_cmp")
        fsm.sign(
            f"{name}_cmp",
            "lit_l",
            f"M`{abs(SETUP_END)}`+",
            neg="bad_stream",
            zero="absent_meta",
            pos=positive,
        )
        if index < room_no:
            _skip_header(fsm, f"skip_{index}", f"header_start_{index + 1}")

    fsm.go("target_event_restore", "right", "Ws", "target_field_r_0")
    for index in range(10):
        target = f"target_field_r_{index + 1}" if index < 9 else "target_end_r"
        fsm.go(
            f"target_field_r_{index}",
            "left",
            "r",
            f"target_field_s_{index}",
        )
        fsm.go(f"target_field_s_{index}", "right", "s", target)
    fsm.go("target_end_r", "left", "r", "meta_r_0")
    for index in range(4):
        target = f"meta_r_{index + 1}" if index < 3 else "remaining_header_r"
        fsm.go(f"meta_r_{index}", "right", "r", f"meta_out_{index}")
        fsm.go(f"meta_out_{index}", "left", "s", target)

    fsm.go("absent_meta", "left", "0s0s0s0s", "split_r")
    fsm.go("remaining_header_r", "left", "r", "remaining_header_cmp")
    fsm.sign(
        "remaining_header_cmp",
        "lit_l",
        f"M`{abs(SETUP_END)}`+",
        neg="bad_stream",
        zero="split_r",
        pos="remaining_header_skip",
    )
    _skip_header(fsm, "remaining_header_skip", "remaining_header_r")
    fsm.go("split_r", "left", "r", "pipe_start_0")

    for slot in range(3):
        fsm.go(f"pipe_start_{slot}", "left", "r", f"pipe_start_cmp_{slot}")
        zero = f"pipe_pad_{slot}" if slot < 2 else "copy_split_r"
        positive = f"pipe_{slot}_start_restore" if slot < 2 else "bad_stream"
        fsm.sign(
            f"pipe_start_cmp_{slot}",
            "lit_l",
            f"M`{abs(INDEX_END)}`+",
            neg="bad_stream",
            zero=zero,
            pos=positive,
        )
        if slot < 2:
            _pipe_record(fsm, slot, f"pipe_start_{slot + 1}")
            fsm.go(
                f"pipe_pad_{slot}",
                "left",
                "0s" * (2 - slot),
                "copy_split_r",
            )

    fsm.go("copy_split_r", "left", "r", "relay_header_r")
    _relay_indexed(fsm, "header_start_0")
    fsm.go("bad_stream", "left", "H", "bad_stream")
    return fsm


def build_indexdecision_room(room_no: int) -> list[str]:
    return _compile(_build_fsm(room_no), extra_gap=96)


def _phase_rows(room_no: int) -> tuple[int, int, int, int]:
    fsm = _build_fsm(room_no)
    _routes, blocks, _height = _layout(fsm)
    room_commands = [
        blocks[name]
        for name in blocks
        if name == "target_event_restore" or name.startswith("target_field_s_")
    ]
    room_responses = [blocks[name] for name in blocks if name.startswith("meta_r_")]
    pipe_commands = [
        blocks[name]
        for name in blocks
        if name.startswith(("pipe_0_", "pipe_1_"))
        and (
            name.endswith(("_restore", "_s"))
            and not name.endswith("response_out")
        )
    ]
    pipe_responses = [
        blocks[name]
        for name in blocks
        if name in {"pipe_0_response_r", "pipe_1_response_r"}
    ]

    def middle(rows: list[int]) -> int:
        return (min(rows) + max(rows)) // 2

    return tuple(
        middle(rows)
        for rows in (room_commands, room_responses, pipe_commands, pipe_responses)
    )


def _io_rows(room_no: int) -> tuple[int, int]:
    fsm = _build_fsm(room_no)
    _routes, blocks, _height = _layout(fsm)
    service_reads = {
        name
        for name in blocks
        if name.startswith("meta_r_")
        or name in {"pipe_0_response_r", "pipe_1_response_r"}
    }
    service_writes = {
        name
        for name, zone, _code, _kind, _targets in fsm.blocks
        if zone == "right"
        and (
            name == "target_event_restore"
            or name.startswith("target_field_s_")
            or name.startswith(("pipe_0_", "pipe_1_"))
        )
        and name not in {"pipe_0_response_r", "pipe_1_response_r"}
    }
    reads = []
    writes = []
    for name, _zone, code, _kind, _targets in fsm.blocks:
        if name not in service_reads:
            reads.extend([blocks[name]] * code.count("r"))
        if name not in service_writes:
            writes.extend([blocks[name]] * code.count("s"))
    return (min(reads) + max(reads)) // 2, (min(writes) + max(writes)) // 2


def _add_service_ring(
    cv: Canvas,
    *,
    top: int,
    right: int,
) -> None:
    from .lllm_fetch import build_relay

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


def _route_service(
    cv: Canvas,
    *,
    ctrl_right: int,
    command_row: int,
    response_row: int,
    service_left: int,
    service_top: int,
    command_track: int,
    response_track: int,
) -> None:
    cv.pipe(
        [
            (command_row, ctrl_right + 1),
            (command_row, command_track),
            (service_top + 2, command_track),
            (service_top + 2, service_left - 1),
        ]
    )
    cv.pipe(
        [
            (service_top + 6, service_left - 1),
            (service_top + 6, response_track),
            (response_row, response_track),
            (response_row, ctrl_right + 1),
        ]
    )


def build_indexdecision_rig(room_no: int) -> str:
    ctrl = build_indexdecision_room(room_no)
    room_service = build_roomcontext_room()
    pipe_service = build_pipecontext_room()
    left = 5
    ctrl_right = left + len(ctrl[0]) - 1
    service_left = ctrl_right + 40
    room_top = len(ctrl) + 20
    pipe_top = room_top + len(room_service) + 20
    room_right = service_left + len(room_service[0]) - 1
    pipe_right = service_left + len(pipe_service[0]) - 1
    room_cmd, room_resp, pipe_cmd, pipe_resp = _phase_rows(room_no)
    input_row, output_row = _io_rows(room_no)

    cv = Canvas()
    cv.put(0, left, ctrl)
    cv.put(room_top, service_left, room_service)
    cv.put(pipe_top, service_left, pipe_service)
    cv.put(input_row - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(output_row - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(input_row, 3), (input_row, left - 1)])
    cv.pipe([(output_row, left - 1), (output_row, 3)])

    _route_service(
        cv,
        ctrl_right=ctrl_right,
        command_row=room_cmd,
        response_row=room_resp,
        service_left=service_left,
        service_top=room_top,
        command_track=service_left - 6,
        response_track=service_left - 10,
    )
    _route_service(
        cv,
        ctrl_right=ctrl_right,
        command_row=pipe_cmd,
        response_row=pipe_resp,
        service_left=service_left,
        service_top=pipe_top,
        command_track=service_left - 14,
        response_track=service_left - 18,
    )
    _add_service_ring(cv, top=room_top, right=room_right)
    _add_service_ring(cv, top=pipe_top, right=pipe_right)
    return cv.render()
