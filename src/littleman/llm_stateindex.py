"""Index normalized LLM state into room headers and a global pipe table."""

from __future__ import annotations

from .lllm_scan import _compile, _Fsm
from .llm_perimeter import ROOM_END
from .llm_pipetrace import PIPE_END
from .llm_roomfind import SETUP_END
from .llm_statebuild import PIPE_MASK, PIPE_VALUES

INDEX_SPLIT = -4800
INDEX_END = -4900


def stateindex_reference(tokens: list[int]) -> list[int]:
    """Move source-tagged pipe records behind the room-header stream."""
    rooms: list[int] = []
    pipes: list[int] = []
    index = 0
    while tokens[index] != SETUP_END:
        event = tokens[index]
        rooms.extend(tokens[index : index + 11])
        index += 11
        while tokens[index] != ROOM_END:
            start = tokens[index]
            pipes.extend((start, event))
            index += 1
            while tokens[index] != PIPE_MASK:
                pipes.extend(tokens[index : index + 2])
                index += 2
            pipes.extend(tokens[index : index + 2])
            index += 2
            if tokens[index] != PIPE_VALUES:
                raise ValueError(f"missing values marker: {tokens[index]}")
            count = tokens[index + 1]
            pipes.extend(tokens[index : index + 2 + count])
            index += 2 + count
            if tokens[index] != PIPE_END:
                raise ValueError(f"missing pipe end: {tokens[index]}")
            pipes.append(PIPE_END)
            index += 1
        rooms.append(ROOM_END)
        index += 1
    if index + 1 != len(tokens):
        raise ValueError("unexpected normalized-state tail")
    return [*rooms, SETUP_END, INDEX_SPLIT, *pipes, INDEX_END]


def stateunindex_reference(tokens: list[int]) -> list[int]:
    """Restore source-grouped normalized state from an indexed stream."""
    rooms: list[list[int]] = []
    pipes: list[tuple[int, list[int]]] = []
    index = 0
    while tokens[index] != SETUP_END:
        header = list(tokens[index : index + 11])
        index += 11
        if tokens[index] != ROOM_END:
            raise ValueError(f"missing indexed room end: {tokens[index]}")
        index += 1
        rooms.append(header)
    index += 1
    if tokens[index] != INDEX_SPLIT:
        raise ValueError(f"missing index split: {tokens[index]}")
    index += 1
    while tokens[index] != INDEX_END:
        start, source_event = tokens[index : index + 2]
        record = [start]
        index += 2
        while tokens[index] != PIPE_MASK:
            record.extend(tokens[index : index + 2])
            index += 2
        record.extend(tokens[index : index + 2])
        index += 2
        if tokens[index] != PIPE_VALUES:
            raise ValueError(f"missing indexed values marker: {tokens[index]}")
        count = tokens[index + 1]
        record.extend(tokens[index : index + 2 + count])
        index += 2 + count
        if tokens[index] != PIPE_END:
            raise ValueError(f"missing indexed pipe end: {tokens[index]}")
        record.append(PIPE_END)
        index += 1
        pipes.append((source_event, record))
    if index + 1 != len(tokens):
        raise ValueError("unexpected indexed-state tail")

    out: list[int] = []
    events = {header[0] for header in rooms}
    if len(events) != len(rooms):
        raise ValueError("room events are not unique")
    if any(source not in events for source, _record in pipes):
        raise ValueError("pipe has unknown source event")
    for header in rooms:
        out.extend(header)
        for source, record in pipes:
            if source == header[0]:
                out.extend(record)
        out.append(ROOM_END)
    return [*out, SETUP_END]


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "item_r")
    fsm.go("item_r", "left", "r", "item_cmp")
    fsm.sign(
        "item_cmp",
        "lit_l",
        "M`1000`+",
        neg="bad_item",
        zero="setup_restore",
        pos="event_restore",
    )
    fsm.go("bad_item", "left", "H", "bad_item")
    # Restore the event after the exact SETUP_END comparison, relay it, and
    # retain it in B as the pipe-source identity for the whole room.
    fsm.go("event_restore", "left", "WsM", "field_r_0")
    for index in range(10):
        target = f"field_r_{index + 1}" if index < 9 else "start_r"
        fsm.go(f"field_r_{index}", "left", "rs", target)

    fsm.sign(
        "start_r",
        "left",
        "r",
        neg="room_end",
        zero="bad_start",
        pos="start_store",
    )
    fsm.go("bad_start", "left", "H", "bad_start")
    # The global pipe record starts with (start, source_event).  W-s-W emits
    # B without losing either the current token or the retained event.
    fsm.go("start_store", "right", "sWsW", "body_r")
    fsm.sign(
        "body_r",
        "left",
        "r",
        neg="mask_store",
        zero="body_store",
        pos="body_store",
    )
    fsm.go("body_store", "right", "s", "bit_r")
    fsm.go("bit_r", "left", "r", "bit_store")
    fsm.go("bit_store", "right", "s", "body_r")

    fsm.go("mask_store", "right", "s", "mask_r")
    fsm.go("mask_r", "left", "r", "mask_value_store")
    fsm.go("mask_value_store", "right", "s", "values_marker_r")
    fsm.go("values_marker_r", "left", "r", "values_marker_store")
    fsm.go("values_marker_store", "right", "s", "count_r")
    # `b` copies A (not B) into BP, while the source event survives in B.
    fsm.go("count_r", "left", "rb", "count_store")
    fsm.go("count_store", "right", "s", "values_count")
    fsm.bp("values_count", "mid", "", zero="pipe_end_r", pos="value_r")
    fsm.go("value_r", "left", "r", "value_store")
    fsm.go("value_store", "right", "s", "values_dec")
    fsm.bp("values_dec", "mid", "m", zero="pipe_end_r", pos="value_r")
    fsm.go("pipe_end_r", "left", "r", "pipe_end_store")
    fsm.go("pipe_end_store", "right", "s", "start_r")

    fsm.go("room_end", "left", "s", "item_r")
    fsm.go("setup_restore", "left", "Ws", "split_out")
    fsm.go("split_out", "lit_l", f" `{abs(INDEX_SPLIT):04d}`Ns", "sentinel")
    fsm.go("sentinel", "lit_r", f" `{abs(INDEX_END):04d}`Ns", "drain_r")
    fsm.go("drain_r", "right", "r", "drain_cmp")
    fsm.sign(
        "drain_cmp",
        "lit_r",
        f"M`{abs(INDEX_END):04d}`+",
        neg="drain_restore",
        zero="index_end",
        pos="drain_restore",
    )
    fsm.go("drain_restore", "left", "Ws", "drain_r")
    fsm.go("index_end", "left", "WsH", "index_end")
    return fsm


def build_stateindex_room() -> list[str]:
    return _compile(_build_fsm())
