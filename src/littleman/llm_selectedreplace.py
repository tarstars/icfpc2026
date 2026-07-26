"""Replace one indexed pipe record with the selected apply response."""

from __future__ import annotations

from .canvas import Canvas
from .lllm_fetch import build_relay
from .lllm_scan import _compile, _Fsm, _layout
from .llm_indexdecision import _indexed_end, _relay_indexed
from .llm_pipetrace import PIPE_END
from .llm_roomfind import SETUP_END
from .llm_selectedapply import _drop_record
from .llm_statebuild import PIPE_MASK, PIPE_VALUES
from .llm_stateindex import INDEX_END, INDEX_SPLIT

SELECTED_PREFIX_WORDS = 5
HEADER_PREFIX_WORDS = 6


def _record_end(tokens: list[int], start: int) -> int:
    index = start + 1
    while tokens[index] != PIPE_MASK:
        index += 2
    index += 2
    if tokens[index] != PIPE_VALUES:
        raise ValueError(f"missing replacement values marker: {tokens[index]}")
    count = tokens[index + 1]
    index += 2 + count
    if tokens[index] != PIPE_END:
        raise ValueError(f"missing replacement pipe end: {tokens[index]}")
    return index + 1


def _replace_indexed_record(
    state: list[int],
    selected: int,
    replacement: list[int],
) -> list[int]:
    split = state.index(INDEX_SPLIT) + 1
    index = split
    records = []
    while state[index] != INDEX_END:
        end = _record_end(state, index + 1)
        records.append(list(state[index:end]))
        index = end
    if selected not in range(len(records)):
        raise ValueError(f"selected replacement slot is absent: {selected}")
    records[selected] = replacement
    return [
        *state[:split],
        *(item for record in records for item in record),
        INDEX_END,
    ]


def selectedreplace_reference(tokens: list[int]) -> list[int]:
    """Emit ``active, op, ctrl, A, status, result, updated_state``."""
    out = []
    index = 0
    while index < len(tokens):
        active, op, ctrl, ai, selected = tokens[
            index : index + SELECTED_PREFIX_WORDS
        ]
        index += SELECTED_PREFIX_WORDS
        present = tokens[index]
        index += 1
        replacement = None
        if active:
            if present != 1:
                raise ValueError("active replacement record is absent")
            source_event = tokens[index]
            index += 1
            end = _record_end(tokens, index)
            normalized = list(tokens[index:end])
            index = end
            replacement = [normalized[0], source_event, *normalized[1:]]
        elif present:
            raise ValueError("inactive replacement record is present")
        status, result = tokens[index : index + 2]
        index += 2
        state_end = _indexed_end(tokens, index)
        state = list(tokens[index:state_end])
        index = state_end
        if replacement is not None:
            state = _replace_indexed_record(state, selected, replacement)
        out.extend((active, op, ctrl, ai, status, result, *state))
    return out


def _relay_record(fsm: _Fsm, prefix: str, source: str, target: str) -> None:
    fsm.go(f"{prefix}_source", source, "r", f"{prefix}_source_out")
    fsm.go(f"{prefix}_source_out", "left", "s", f"{prefix}_body_r")
    fsm.go(f"{prefix}_body_r", source, "r", f"{prefix}_body_cmp")
    fsm.sign(
        f"{prefix}_body_cmp",
        "lit_r" if source == "right" else "lit_l",
        f"M`{abs(PIPE_MASK)}`+",
        neg="bad_stream",
        zero=f"{prefix}_mask_restore",
        pos=f"{prefix}_body_restore",
    )
    fsm.go(f"{prefix}_body_restore", "left", "Ws", f"{prefix}_bit_r")
    fsm.go(f"{prefix}_bit_r", source, "r", f"{prefix}_bit_out")
    fsm.go(f"{prefix}_bit_out", "left", "s", f"{prefix}_body_r")
    fsm.go(f"{prefix}_mask_restore", "left", "Ws", f"{prefix}_mask_r")
    for name, next_name in (
        ("mask", "values_marker"),
        ("values_marker", "count"),
    ):
        fsm.go(f"{prefix}_{name}_r", source, "r", f"{prefix}_{name}_out")
        fsm.go(
            f"{prefix}_{name}_out",
            "left",
            "s",
            f"{prefix}_{next_name}_r",
        )
    fsm.go(f"{prefix}_count_r", source, "rMb", f"{prefix}_count_out")
    fsm.go(f"{prefix}_count_out", "left", "s", f"{prefix}_values")
    fsm.bp(
        f"{prefix}_values",
        "mid",
        "",
        zero=f"{prefix}_end_r",
        pos=f"{prefix}_value_r",
    )
    fsm.go(f"{prefix}_value_r", source, "r", f"{prefix}_value_out")
    fsm.go(f"{prefix}_value_out", "left", "s", f"{prefix}_value_dec")
    fsm.bp(
        f"{prefix}_value_dec",
        "mid",
        "m",
        zero=f"{prefix}_end_r",
        pos=f"{prefix}_value_r",
    )
    fsm.go(f"{prefix}_end_r", source, "r", f"{prefix}_end_out")
    fsm.go(f"{prefix}_end_out", "left", "s", target)


def _store_record_tail(fsm: _Fsm, prefix: str, target: str) -> None:
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
    fsm.go(f"{prefix}_bit_r", "left", "r", f"{prefix}_bit_store")
    fsm.go(f"{prefix}_bit_store", "right", "s", f"{prefix}_body_r")
    fsm.go(f"{prefix}_mask_restore", "right", "Ws", f"{prefix}_mask_r")
    for name, next_name in (
        ("mask", "values_marker"),
        ("values_marker", "count"),
    ):
        fsm.go(f"{prefix}_{name}_r", "left", "r", f"{prefix}_{name}_store")
        fsm.go(
            f"{prefix}_{name}_store",
            "right",
            "s",
            f"{prefix}_{next_name}_r",
        )
    fsm.go(f"{prefix}_count_r", "left", "rMb", f"{prefix}_count_store")
    fsm.go(f"{prefix}_count_store", "right", "s", f"{prefix}_values")
    fsm.bp(
        f"{prefix}_values",
        "mid",
        "",
        zero=f"{prefix}_end_r",
        pos=f"{prefix}_value_r",
    )
    fsm.go(f"{prefix}_value_r", "left", "r", f"{prefix}_value_store")
    fsm.go(f"{prefix}_value_store", "right", "s", f"{prefix}_value_dec")
    fsm.bp(
        f"{prefix}_value_dec",
        "mid",
        "m",
        zero=f"{prefix}_end_r",
        pos=f"{prefix}_value_r",
    )
    fsm.go(f"{prefix}_end_r", "left", "r", f"{prefix}_end_store")
    fsm.go(f"{prefix}_end_store", "right", "s", target)


def _pipe_tail(fsm: _Fsm, prefix: str, target: str) -> None:
    fsm.go(f"{prefix}_start_r", "left", "r", f"{prefix}_start_cmp")
    fsm.sign(
        f"{prefix}_start_cmp",
        "lit_l",
        f"M`{abs(INDEX_END)}`+",
        neg="bad_stream",
        zero=f"{prefix}_index_out",
        pos=f"{prefix}_start_out",
    )
    fsm.go(f"{prefix}_start_out", "left", "Ws", f"{prefix}_record_source")
    _relay_record(fsm, f"{prefix}_record", "left", f"{prefix}_start_r")
    fsm.go(f"{prefix}_index_out", "left", "Ws", target)


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
    fsm.go("inactive_prefix", "left", "rs" * 3, "inactive_selected_drop")
    fsm.go("inactive_selected_drop", "left", "r", "inactive_present_r")
    fsm.go("inactive_present_r", "left", "r", "inactive_present_branch")
    fsm.sign(
        "inactive_present_branch",
        "mid",
        "",
        neg="bad_stream",
        zero="inactive_status",
        pos="bad_stream",
    )
    fsm.go("inactive_status", "left", "rsrs", "relay_header_r")
    _relay_indexed(fsm, "active_r", consume_tail=False)

    fsm.go("active_out", "left", "1s", "active_prefix")
    fsm.go("active_prefix", "left", "rs" * 3, "selected_r")
    fsm.go("selected_r", "left", "r", "selected_store")
    fsm.go("selected_store", "right", "s", "present_r")
    fsm.go("present_r", "left", "r", "present_branch")
    fsm.sign(
        "present_branch",
        "mid",
        "",
        neg="bad_stream",
        zero="bad_stream",
        pos="source_r",
    )
    fsm.go("source_r", "left", "rM", "replacement_start_r")
    fsm.go("replacement_start_r", "left", "r", "replacement_start_store")
    fsm.go(
        "replacement_start_store",
        "right",
        "sWs",
        "replacement_body_r",
    )
    _store_record_tail(fsm, "replacement", "status_r")
    fsm.go("status_r", "left", "rs", "result_r")
    fsm.go("result_r", "left", "rs", "state_header_r")

    fsm.go("state_header_r", "left", "r", "state_header_cmp")
    fsm.sign(
        "state_header_cmp",
        "lit_l",
        f"M`{abs(SETUP_END)}`+",
        neg="bad_stream",
        zero="state_setup_out",
        pos="state_event_out",
    )
    fsm.go("state_event_out", "left", "Ws", "state_header_tail_0")
    fsm.go("state_header_tail_0", "left", "rs" * 5, "state_header_tail_1")
    fsm.go("state_header_tail_1", "left", "rs" * 6, "state_header_r")
    fsm.go("state_setup_out", "left", "Ws", "state_split")
    fsm.go("state_split", "left", "rs", "selection_get")
    fsm.go("selection_get", "right", "rb", "pipe0_start_r")
    fsm.go("pipe0_start_r", "left", "r", "pipe0_start_cmp")
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
        zero="replace0_source",
        pos="relay0_start_out",
    )
    _drop_record(fsm, "replace0", "replacement_out_start")
    fsm.go("relay0_start_out", "left", "Ws", "relay0_source")
    _relay_record(fsm, "relay0", "left", "pipe1_start_r")
    fsm.go("pipe1_start_r", "left", "r", "pipe1_start_cmp")
    fsm.sign(
        "pipe1_start_cmp",
        "lit_l",
        f"M`{abs(INDEX_END)}`+",
        neg="bad_stream",
        zero="bad_stream",
        pos="replace1_source",
    )
    _drop_record(fsm, "replace1", "replacement_out_start")

    fsm.go("replacement_out_start", "right", "r", "replacement_start_out")
    fsm.go("replacement_start_out", "left", "s", "replacement_out_source")
    _relay_record(fsm, "replacement_out", "right", "tail_start_r")
    _pipe_tail(fsm, "tail", "active_r")
    fsm.go("bad_stream", "left", "H", "bad_stream")
    return fsm


def build_selectedreplace_room() -> list[str]:
    return _compile(_build_fsm(), extra_gap=128)


def _port_rows() -> tuple[int, int, int, int]:
    fsm = _build_fsm()
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


def build_selectedreplace_rig() -> str:
    room = build_selectedreplace_room()
    left = 5
    right = left + len(room[0]) - 1
    relay_left = right + 5
    far = relay_left + 17
    input_row, output_row, scratch_out, scratch_in = _port_rows()
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
