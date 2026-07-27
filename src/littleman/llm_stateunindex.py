"""Restore source-grouped state after the indexed LLM action pass."""

from __future__ import annotations

from .canvas import Canvas
from .lllm_scan import _compile, _Fsm, _layout
from .llm_indexcopy import (
    INDEX_COPY_END,
    INDEX_COPY_SPLIT,
    add_indexcopy_network,
    build_indexcopy_room,
    indexmulticopy_reference,
)
from .llm_perimeter import ROOM_END
from .llm_roomfind import SETUP_END
from .llm_statebuild import PIPE_MASK
from .llm_stateindex import INDEX_END, stateunindex_reference


def stateunindex_core_reference(tokens: list[int]) -> list[int]:
    """Consume three delimited indexed copies and restore normalized state."""
    copies = []
    start = 0
    for copy_no in range(3):
        index = start
        while tokens[index] != SETUP_END:
            index += 12
        index += 2
        while tokens[index] != INDEX_END:
            index += 2
            while tokens[index] != PIPE_MASK:
                index += 2
            index += 2
            count = tokens[index + 1]
            index += 3 + count
        copies.append(tokens[start : index + 1])
        marker = INDEX_COPY_END if copy_no == 2 else INDEX_COPY_SPLIT
        if tokens[index + 1] != marker:
            raise ValueError(f"bad indexed-copy marker: {tokens[index + 1]}")
        start = index + 2
    if start != len(tokens) or copies[1:] != copies[:-1]:
        raise ValueError("indexed state copies disagree")
    return stateunindex_reference(copies[0])


def stateunindex_pipeline_reference(tokens: list[int]) -> list[int]:
    return stateunindex_core_reference(indexmulticopy_reference(tokens, 3))


def _build_matcher_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "event_r")
    fsm.go("event_r", "left", "rM", "query_0")
    for slot in range(2):
        fsm.go(f"query_{slot}", "left", "r-", f"result_{slot}")
        next_state = f"query_{slot + 1}" if slot == 0 else "event_r"
        fsm.sign(
            f"result_{slot}",
            "left",
            "",
            neg=f"miss_{slot}",
            zero=f"hit_{slot}",
            pos=f"miss_{slot}",
        )
        fsm.go(f"miss_{slot}", "left", "0s", next_state)
        fsm.go(f"hit_{slot}", "left", "1s", next_state)
    return fsm


def build_source_matcher_room() -> list[str]:
    return _compile(_build_matcher_fsm())


def _skip_header(fsm: _Fsm, name: str, target: str) -> None:
    fsm.go(name, "left", "r" * 10, f"{name}_end")
    fsm.go(f"{name}_end", "left", "r", target)


def _skip_record_tail(fsm: _Fsm, prefix: str, target: str) -> None:
    fsm.go(f"{prefix}_body_r", "left", "r", f"{prefix}_body_cmp")
    fsm.sign(
        f"{prefix}_body_cmp",
        "lit_l",
        f"M`{abs(PIPE_MASK)}`+",
        neg="bad_stream",
        zero=f"{prefix}_mask_r",
        pos=f"{prefix}_bit_r",
    )
    fsm.go(f"{prefix}_bit_r", "left", "r", f"{prefix}_body_r")
    fsm.go(f"{prefix}_mask_r", "left", "r" * 3 + "Mb", f"{prefix}_values")
    fsm.bp(
        f"{prefix}_values",
        "mid",
        "",
        zero=f"{prefix}_end_r",
        pos=f"{prefix}_value_r",
    )
    fsm.go(f"{prefix}_value_r", "left", "r", f"{prefix}_value_dec")
    fsm.bp(
        f"{prefix}_value_dec",
        "mid",
        "m",
        zero=f"{prefix}_end_r",
        pos=f"{prefix}_value_r",
    )
    fsm.go(f"{prefix}_end_r", "left", "r", target)


def _relay_record_tail(fsm: _Fsm, prefix: str, target: str) -> None:
    fsm.go(f"{prefix}_body_r", "left", "r", f"{prefix}_body_cmp")
    fsm.sign(
        f"{prefix}_body_cmp",
        "lit_l",
        f"M`{abs(PIPE_MASK)}`+",
        neg="bad_stream",
        zero=f"{prefix}_mask_restore",
        pos=f"{prefix}_body_restore",
    )
    fsm.go(f"{prefix}_body_restore", "left", "Ws", f"{prefix}_bit_r")
    fsm.go(f"{prefix}_bit_r", "left", "rs", f"{prefix}_body_r")
    fsm.go(f"{prefix}_mask_restore", "left", "Wsrsrs", f"{prefix}_count_r")
    fsm.go(f"{prefix}_count_r", "left", "rMbs", f"{prefix}_values")
    fsm.bp(
        f"{prefix}_values",
        "mid",
        "",
        zero=f"{prefix}_end_r",
        pos=f"{prefix}_value_r",
    )
    fsm.go(f"{prefix}_value_r", "left", "rs", f"{prefix}_value_dec")
    fsm.bp(
        f"{prefix}_value_dec",
        "mid",
        "m",
        zero=f"{prefix}_end_r",
        pos=f"{prefix}_value_r",
    )
    fsm.go(f"{prefix}_end_r", "left", "rs", target)


def _padding(fsm: _Fsm, prefix: str, count: int, target: str) -> None:
    state = f"{prefix}_pad_0"
    if count == 0:
        fsm.go(state, "mid", "", target)
        return
    for index in range(count):
        next_state = f"{prefix}_pad_{index + 1}" if index + 1 < count else target
        fsm.go(f"{prefix}_pad_{index}", "right", "0sr", next_state)


def _present_pipe_scan(
    fsm: _Fsm,
    prefix: str,
    marker: int,
    done: str,
) -> None:
    for slot in range(3):
        start = f"{prefix}_pipe_start_{slot}"
        fsm.go(start, "left", "r", f"{start}_cmp")
        positive = f"{prefix}_start_restore_{slot}" if slot < 2 else "bad_stream"
        fsm.sign(
            f"{start}_cmp",
            "lit_l",
            f"M`{abs(INDEX_END)}`+",
            neg="bad_stream",
            zero=f"{prefix}_index_end_{slot}",
            pos=positive,
        )
        if slot < 2:
            fsm.go(
                f"{prefix}_start_restore_{slot}",
                "left",
                "WM",
                f"{prefix}_source_r_{slot}",
            )
            fsm.go(
                f"{prefix}_source_r_{slot}",
                "left",
                "r",
                f"{prefix}_source_send_{slot}",
            )
            fsm.go(
                f"{prefix}_source_send_{slot}",
                "right",
                "sr",
                f"{prefix}_match_{slot}",
            )
            fsm.sign(
                f"{prefix}_match_{slot}",
                "mid",
                "",
                neg="bad_stream",
                zero=f"{prefix}_drop_{slot}_body_r",
                pos=f"{prefix}_emit_start_{slot}",
            )
            fsm.go(
                f"{prefix}_emit_start_{slot}",
                "left",
                "Ws",
                f"{prefix}_emit_{slot}_body_r",
            )
            target = f"{prefix}_pipe_start_{slot + 1}"
            _relay_record_tail(fsm, f"{prefix}_emit_{slot}", target)
            _skip_record_tail(fsm, f"{prefix}_drop_{slot}", target)

        pad = f"{prefix}_finish_{slot}_pad_0"
        fsm.go(f"{prefix}_index_end_{slot}", "mid", "", pad)
        marker_read = f"{prefix}_marker_r_{slot}"
        _padding(fsm, f"{prefix}_finish_{slot}", 2 - slot, marker_read)
        fsm.go(marker_read, "left", "r", f"{prefix}_marker_cmp_{slot}")
        fsm.sign(
            f"{prefix}_marker_cmp_{slot}",
            "lit_l",
            f"M`{abs(marker)}`+",
            neg="bad_stream",
            zero=f"{prefix}_room_end_{slot}",
            pos="bad_stream",
        )
        fsm.go(
            f"{prefix}_room_end_{slot}",
            "lit_l",
            f" `{abs(ROOM_END):04d}`Ns",
            done,
        )


def _absent_pipe_scan(
    fsm: _Fsm,
    prefix: str,
    marker: int,
    done: str,
) -> None:
    fsm.go(f"{prefix}_start_r", "left", "r", f"{prefix}_start_cmp")
    fsm.sign(
        f"{prefix}_start_cmp",
        "lit_l",
        f"M`{abs(INDEX_END)}`+",
        neg="bad_stream",
        zero=f"{prefix}_marker_r",
        pos=f"{prefix}_source_r",
    )
    fsm.go(f"{prefix}_source_r", "left", "r", f"{prefix}_record_body_r")
    _skip_record_tail(fsm, f"{prefix}_record", f"{prefix}_start_r")
    fsm.go(f"{prefix}_marker_r", "left", "r", f"{prefix}_marker_cmp")
    fsm.sign(
        f"{prefix}_marker_cmp",
        "lit_l",
        f"M`{abs(marker)}`+",
        neg="bad_stream",
        zero=done,
        pos="bad_stream",
    )


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "room_0_header_0")
    for room_no in range(3):
        marker = INDEX_COPY_END if room_no == 2 else INDEX_COPY_SPLIT
        next_room = "finish" if room_no == 2 else f"room_{room_no + 1}_header_0"
        for header_no in range(room_no + 1):
            name = f"room_{room_no}_header_{header_no}"
            target = (
                f"room_{room_no}_target_restore"
                if header_no == room_no
                else f"room_{room_no}_skip_{header_no}"
            )
            fsm.go(name, "left", "r", f"{name}_cmp")
            fsm.sign(
                f"{name}_cmp",
                "lit_l",
                f"M`{abs(SETUP_END)}`+",
                neg="bad_stream",
                zero=f"room_{room_no}_absent_split",
                pos=target,
            )
            if header_no < room_no:
                _skip_header(
                    fsm,
                    f"room_{room_no}_skip_{header_no}",
                    f"room_{room_no}_header_{header_no + 1}",
                )

        prefix = f"room_{room_no}"
        fsm.go(
            f"{prefix}_target_restore",
            "left",
            "Ws",
            f"{prefix}_event_store",
        )
        fsm.go(f"{prefix}_event_store", "right", "s", f"{prefix}_field_0")
        for field in range(10):
            target = (
                f"{prefix}_field_{field + 1}" if field < 9 else f"{prefix}_target_end"
            )
            fsm.go(f"{prefix}_field_{field}", "left", "rs", target)
        fsm.go(f"{prefix}_target_end", "left", "r", f"{prefix}_remaining")

        fsm.go(f"{prefix}_remaining", "left", "r", f"{prefix}_remaining_cmp")
        fsm.sign(
            f"{prefix}_remaining_cmp",
            "lit_l",
            f"M`{abs(SETUP_END)}`+",
            neg="bad_stream",
            zero=f"{prefix}_present_split",
            pos=f"{prefix}_remaining_skip",
        )
        _skip_header(fsm, f"{prefix}_remaining_skip", f"{prefix}_remaining")
        fsm.go(
            f"{prefix}_present_split",
            "left",
            "r",
            f"{prefix}_pipe_start_0",
        )
        _present_pipe_scan(fsm, prefix, marker, next_room)

        fsm.go(
            f"{prefix}_absent_split",
            "left",
            "r",
            f"{prefix}_absent_start_r",
        )
        _absent_pipe_scan(fsm, f"{prefix}_absent", marker, next_room)

    fsm.go(
        "finish",
        "lit_l",
        f" `{abs(SETUP_END):04d}`Ns",
        "room_0_header_0",
    )
    fsm.go("bad_stream", "left", "H", "bad_stream")
    return fsm


def build_stateunindex_room() -> list[str]:
    return _compile(_build_fsm(), extra_gap=96)


def _port_rows(
    fsm: _Fsm,
    *,
    service_on_right: bool,
) -> tuple[int, int, int, int]:
    _routes, blocks, _height = _layout(fsm)
    main_reads, main_writes, service_writes, service_reads = ([], [], [], [])
    for name, zone, code, _kind, _targets in fsm.blocks:
        for char in code:
            if char == "r":
                target = (
                    service_reads
                    if service_on_right and zone == "right"
                    else main_reads
                )
                target.append(blocks[name])
            elif char == "s":
                target = (
                    service_writes
                    if service_on_right and zone == "right"
                    else main_writes
                )
                target.append(blocks[name])

    def middle(rows: list[int]) -> int:
        return (min(rows) + max(rows)) // 2

    return tuple(
        middle(rows)
        for rows in (main_reads, main_writes, service_writes, service_reads)
    )


def _matcher_ports() -> tuple[int, int]:
    fsm = _build_matcher_fsm()
    _routes, blocks, _height = _layout(fsm)
    reads = []
    writes = []
    for name, zone, code, _kind, _targets in fsm.blocks:
        if zone != "left":
            continue
        reads.extend([blocks[name]] * code.count("r"))
        writes.extend([blocks[name]] * code.count("s"))
    return (min(reads) + max(reads)) // 2, (min(writes) + max(writes)) // 2


def add_stateunindex_core(
    cv: Canvas,
    *,
    top: int,
    left: int,
) -> tuple[tuple[int, int], tuple[int, int], int]:
    ctrl = build_stateunindex_room()
    matcher = build_source_matcher_room()
    ctrl_right = left + len(ctrl[0]) - 1
    matcher_top = top + len(ctrl) + 20
    matcher_left = ctrl_right + 30
    input_row, output_row, command_row, response_row = _port_rows(
        _build_fsm(),
        service_on_right=True,
    )
    matcher_input, matcher_output = _matcher_ports()
    cv.put(top, left, ctrl)
    cv.put(matcher_top, matcher_left, matcher)

    command_track = ctrl_right + 10
    response_track = ctrl_right + 5
    cv.pipe(
        [
            (top + command_row, ctrl_right + 1),
            (top + command_row, command_track),
            (matcher_top + matcher_input, command_track),
            (matcher_top + matcher_input, matcher_left - 1),
        ]
    )
    cv.pipe(
        [
            (matcher_top + matcher_output, matcher_left - 1),
            (matcher_top + matcher_output, response_track),
            (top + response_row, response_track),
            (top + response_row, ctrl_right + 1),
        ]
    )
    bottom = matcher_top + len(matcher)
    return (top + input_row, left - 1), (top + output_row, left - 1), bottom


def build_stateunindex_core_rig() -> str:
    cv = Canvas()
    ingress, egress, _bottom = add_stateunindex_core(cv, top=0, left=5)
    cv.put(ingress[0] - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(egress[0] - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(ingress[0], 3), ingress])
    cv.pipe([egress, (egress[0], 3)])
    return cv.render()


def build_stateunindex_rig() -> str:
    cv = Canvas()
    left = 25
    copy_in, copy_out = add_indexcopy_network(
        cv,
        top=0,
        left=left,
        copies=3,
    )
    core_top = len(build_indexcopy_room(copies=3)) + 50
    core_in, core_out, _bottom = add_stateunindex_core(
        cv,
        top=core_top,
        left=left,
    )
    track = 10
    cv.pipe(
        [
            copy_out,
            (copy_out[0], track),
            (core_in[0], track),
            core_in,
        ]
    )
    cv.put(copy_in[0] - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(core_out[0] - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(copy_in[0], 3), copy_in])
    cv.pipe([core_out, (core_out[0], 3)])
    return cv.render()
