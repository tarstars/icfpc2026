#!/usr/bin/env python
"""Build the codex_3 Grade Book reverse-ack/result-handshake candidate."""

from __future__ import annotations

import hashlib
import pathlib

from littleman.canvas import Canvas
from littleman.gradebook import (
    Block,
    COMPACT_LAYOUT,
    PARSER_ZONES,
    RELAY,
    WORKER_ZONES,
    build_parser_fsm,
    build_result_collector,
    build_worker_fsm,
    compile_fsm,
)
from littleman.gradebook_components import _fold_room_prefix

EXPECTED_SHA256 = "bd83b5ae20e482697444bbe07c7df09f165707c1acb005f96addb63a955e3fc1"
REVERSED_FOLD_PREFIXES = ((2, 26), (3, 25), (4, 25), (5, 24), (1, 34))
RESULT_PARSER_ZONES = {**PARSER_ZONES, "result_ack": 25}


def _retarget(block: Block, target: str) -> Block:
    return Block(block.name, block.zone, block.code, block.kind, (target,))


def _build_parser_with_result_handshake():
    """Wait for both worker completion and collector emission on result ops."""
    original = build_parser_fsm()
    rewritten = []
    for block in original.blocks:
        if block.name in {"get_value_send", "avg_value_send", "top_value_send"}:
            rewritten.append(_retarget(block, "op_worker_ack_result"))
        elif block.name == "set_value_send":
            rewritten.append(_retarget(block, "op_worker_ack_set"))
        elif block.name == "op_ack":
            rewritten.extend(
                (
                    Block(
                        "op_worker_ack_result",
                        "ack",
                        "r",
                        "goto",
                        ("op_result_ack",),
                    ),
                    Block(
                        "op_result_ack",
                        "result_ack",
                        "r",
                        "goto",
                        ("op_dec",),
                    ),
                    Block(
                        "op_worker_ack_set",
                        "ack",
                        "r",
                        "goto",
                        ("op_dec",),
                    ),
                )
            )
        else:
            rewritten.append(block)
    original.blocks = rewritten
    return original


def _result_collector(width: int) -> list[str]:
    rows = build_result_collector(width)
    row = list(rows[1])
    row[width // 2] = "S"
    rows[1] = "".join(row)
    return rows


def _build_raw() -> str:
    layout = COMPACT_LAYOUT
    worker_zones = dict(WORKER_ZONES)
    worker_zones["ack_in"], worker_zones["ack_out"] = (
        worker_zones["ack_out"],
        worker_zones["ack_in"],
    )
    workers = {
        subject: compile_fsm(
            build_worker_fsm(subject, delay_cells=0),
            worker_zones,
            right_padding=layout.fsm_right_padding,
        )
        for subject in range(1, 5)
    }

    shift = 1
    physical_subjects = (4, 3, 2, 1)
    worker_width = max(worker.width for worker in workers.values()) + 2
    offsets = [
        shift + layout.margin + index * (worker_width + layout.worker_gap)
        for index in range(4)
    ]
    offset = dict(zip(physical_subjects, offsets, strict=True))
    total_width = max(offset.values()) + worker_width + layout.margin
    parser = compile_fsm(
        _build_parser_with_result_handshake(),
        RESULT_PARSER_ZONES,
        min_width=total_width - shift,
        right_padding=layout.fsm_right_padding,
    )

    canvas = Canvas()
    parser_top = 8
    canvas.put(parser_top, shift, parser.rows)
    parser_bottom = parser_top + parser.height + 1
    workers_top = parser_bottom + layout.worker_vertical_gap
    for subject in physical_subjects:
        canvas.put(workers_top, offset[subject], workers[subject].rows)

    # Keep the input and the final acknowledgement on separate top lanes.
    parser_input_x = shift + parser.zones["input"]
    input_left = 7
    canvas.put(2, input_left, ["+-+", "|I|", "+-+"])
    canvas.pipe(
        [
            (5, input_left + 1),
            (6, input_left + 1),
            (6, parser_input_x),
            (parser_top - 1, parser_input_x),
        ]
    )

    for subject in range(1, 5):
        worker = workers[subject]
        worker_bottom = workers_top + worker.height + 1
        command_x = offset[subject] + worker.zones["command"]
        route_x = offset[subject] - layout.command_left_clearance
        canvas.pipe(
            [
                (parser_bottom + 1, route_x),
                (worker_bottom + 2, route_x),
                (worker_bottom + 2, command_x),
                (worker_bottom + 1, command_x),
            ]
        )

    rings_bottom = workers_top
    result_sources = []
    for subject in range(1, 5):
        worker = workers[subject]
        worker_bottom = workers_top + worker.height + 1
        state_out = offset[subject] + worker.zones["state_out"]
        state_in = offset[subject] + worker.zones["state_in"]
        data_out = offset[subject] + worker.zones["data_out"]
        data_in = offset[subject] + worker.zones["data_in"]
        result_x = offset[subject] + worker.zones["result"]

        state_relay_top = worker_bottom + 8
        canvas.put(state_relay_top, state_out + 4, RELAY)
        canvas.pipe(
            [
                (worker_bottom + 1, state_out),
                (state_relay_top + 3, state_out),
                (state_relay_top + 3, state_out + 3),
            ]
        )
        canvas.pipe(
            [
                (state_relay_top + 2, state_out + 9),
                (state_relay_top + 2, state_out + 12),
                (state_relay_top + 6, state_out + 12),
                (state_relay_top + 6, state_in),
                (worker_bottom + 1, state_in),
            ]
        )

        data_relay_top = worker_bottom + 20
        canvas.put(data_relay_top, data_out + 4, RELAY)
        canvas.pipe(
            [
                (worker_bottom + 1, data_out),
                (data_relay_top + 3, data_out),
                (data_relay_top + 3, data_out + 3),
            ]
        )
        canvas.pipe(
            [
                (data_relay_top + 2, data_out + 9),
                (data_relay_top + 2, data_out + 14),
                (data_relay_top + 10, data_out + 14),
                (data_relay_top + 10, data_in - 18),
                (worker_bottom + 4, data_in - 18),
                (worker_bottom + 4, data_in),
                (worker_bottom + 1, data_in),
            ]
        )
        result_sources.append((worker_bottom + 1, result_x))
        rings_bottom = max(rings_bottom, data_relay_top + 11)

    # Logical 1 -> 2 -> 3 -> 4 is now physically right -> left.
    ack_row = rings_bottom + 3
    for subject in range(1, 4):
        source = workers[subject]
        target = workers[subject + 1]
        source_x = offset[subject] + source.zones["ack_out"]
        target_x = offset[subject + 1] + target.zones["ack_in"]
        source_bottom = workers_top + source.height + 1
        target_bottom = workers_top + target.height + 1
        canvas.pipe(
            [
                (source_bottom + 1, source_x),
                (ack_row, source_x),
                (ack_row, target_x),
                (target_bottom + 1, target_x),
            ]
        )

    final_worker = workers[4]
    final_x = offset[4] + final_worker.zones["ack_out"]
    final_bottom = workers_top + final_worker.height + 1
    parser_ack_x = shift + parser.zones["ack"]
    canvas.pipe(
        [
            (final_bottom + 1, final_x),
            (ack_row, final_x),
            (ack_row, 0),
            (0, 0),
            (0, parser_ack_x),
            (parser_top - 1, parser_ack_x),
        ]
    )

    collector_top = rings_bottom + 10
    collector_width = total_width - shift
    canvas.put(collector_top, shift, _result_collector(collector_width))
    for source in result_sources:
        canvas.pipe([source, (collector_top - 1, source[1])])

    # Collector confirmation returns outside all rooms and pipes.
    collector_right = shift + collector_width - 1
    outer_x = max(collector_right + 2, shift + parser.width + 2)
    result_source_x = collector_right - 2
    parser_result_x = shift + parser.zones["result_ack"]
    canvas.pipe(
        [
            (collector_top + 5, result_source_x),
            (collector_top + 6, result_source_x),
            (collector_top + 6, outer_x),
            (1, outer_x),
            (1, parser_result_x),
            (parser_top - 1, parser_result_x),
        ]
    )

    output_top = collector_top + 10
    center = shift + collector_width // 2
    canvas.put(output_top, center - 1, ["+-+", "|O|", "+-+"])
    canvas.pipe([(collector_top + 5, center), (output_top - 1, center)])
    return canvas.render()


def _squeeze_rows_preserving_top(text: str, preserve_top: int = 8) -> str:
    lines = text.rstrip("\n").split("\n")
    width = max(map(len, lines))
    rows = [line.ljust(width) for line in lines]
    rows = [
        row
        for index, row in enumerate(rows)
        if index < preserve_top or any(char not in " |" for char in row)
    ]
    return "\n".join(row.rstrip() for row in rows) + "\n"


def build_candidate() -> str:
    text = _squeeze_rows_preserving_top(_build_raw())
    for room_index, merges in REVERSED_FOLD_PREFIXES:
        text = _fold_room_prefix(text, room_index, merges)
    text = _squeeze_rows_preserving_top(text)
    lines = text.rstrip("\n").split("\n")
    dimensions = (max(map(len, lines)), len(lines))
    if dimensions != (379, 315):
        raise AssertionError(f"unexpected dimensions: {dimensions}")
    digest = hashlib.sha256(text.encode()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise AssertionError(f"unexpected sha256: {digest}")
    return text


def main() -> None:
    repo = pathlib.Path(__file__).resolve().parents[2]
    output = repo / "submissions" / "gradebook" / "codex3_gradebook_06.man"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_candidate())
    print(f"wrote {output}")
    print(f"size 379x315; sha256 {EXPECTED_SHA256}")


if __name__ == "__main__":
    main()
