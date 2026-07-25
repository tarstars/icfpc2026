"""Generated streaming Sudoku Auditor machine.

One broadcaster sends every ``(row, column, value)`` triple to three workers.
The row, column, and box workers each maintain nine bit masks in a private
ring.  A worker rotates to its selected mask, sets ``1 << (value - 1)``, and
emits 1 when that bit was already present or 0 otherwise.  The aggregator
reads the three order-independent flags and outputs 1 only when their sum is
zero.
"""

from __future__ import annotations

from .canvas import Canvas
from .gradebook import CompiledRoom, Fsm, compile_fsm
from .matmul import RELAY, build_broadcaster

PARSER_ZONES = {
    "logic": 0,
    "input": 5,
    "command": 12,
}

WORKER_ZONES = {
    "logic": 0,
    "command": 7,
    "state_in": 20,
    "state_out": 27,
    "target_in": 42,
    "target_out": 49,
    "bit_in": 64,
    "bit_out": 71,
    "flag_in": 86,
    "flag_out": 93,
    "result": 108,
}

AGGREGATOR_ZONES = {
    "input": 0,
    "logic": 12,
    "output": 20,
}


def build_parser_fsm() -> Fsm:
    fsm = Fsm()
    fsm.go("start", "input", "@r", "send_row")
    fsm.go("send_row", "command", "s", "read_column")
    fsm.go("read_column", "input", "r", "send_column")
    fsm.go("send_column", "command", "s", "read_value")
    fsm.go("read_value", "input", "r", "send_value")
    fsm.go("send_value", "command", "s", "start")
    return fsm


def _add_worker_initialization(fsm: Fsm, command_start: str) -> None:
    fsm.go("start", "logic", "@9b", "init_zero")
    fsm.go("init_zero", "logic", "0", "init_send")
    fsm.go("init_send", "state_out", "s", "init_dec")
    fsm.bp(
        "init_dec",
        "logic",
        "m",
        zero=command_start,
        positive="init_zero",
    )


def _add_worker_update(fsm: Fsm, command_start: str) -> None:
    # Compute the value bit, then remember it in a one-value ring.
    fsm.go("bit_make", "logic", "M1W-W{", "bit_store")
    fsm.go("bit_store", "bit_out", "s", "target_read")

    # Rotate exactly target masks. The target itself remains in its scalar
    # ring until the remaining count (8-target) is needed.
    fsm.go("target_read", "target_in", "rM", "target_restore")
    fsm.go("target_restore", "target_out", "s", "skip_set")
    fsm.bp(
        "skip_set",
        "logic",
        "b",
        zero="mask_read",
        positive="skip_read",
    )
    fsm.go("skip_read", "state_in", "r", "skip_restore")
    fsm.go("skip_restore", "state_out", "s", "skip_dec")
    fsm.bp(
        "skip_dec",
        "logic",
        "m",
        zero="mask_read",
        positive="skip_read",
    )

    # Keep two copies of the old mask. One participates in OR; the second
    # lets new-old distinguish a newly inserted bit from a duplicate.
    fsm.go("mask_read", "state_in", "r", "mask_copy_one")
    fsm.go("mask_copy_one", "flag_out", "s", "mask_copy_two")
    fsm.go("mask_copy_two", "flag_out", "s", "bit_read")
    fsm.go("bit_read", "bit_in", "rM", "bit_restore")
    fsm.go("bit_restore", "bit_out", "s", "mask_for_update")
    fsm.go("mask_for_update", "flag_in", "r", "mask_update")
    fsm.go("mask_update", "logic", "|M", "mask_store")
    fsm.go("mask_store", "state_out", "s", "old_mask_read")
    fsm.go("old_mask_read", "flag_in", "r", "new_bit_test")
    fsm.sign(
        "new_bit_test",
        "logic",
        "W-",
        negative="flag_absent",
        zero="flag_duplicate",
        positive="flag_absent",
    )
    fsm.go("flag_duplicate", "logic", "1", "flag_store")
    fsm.go("flag_absent", "logic", "0", "flag_store")
    fsm.go("flag_store", "flag_out", "s", "remaining_target")

    fsm.go("remaining_target", "target_in", "r", "remaining_count")
    fsm.bp(
        "remaining_count",
        "logic",
        "M8-b",
        zero="bit_drop",
        positive="remaining_read",
    )
    fsm.go("remaining_read", "state_in", "r", "remaining_restore")
    fsm.go("remaining_restore", "state_out", "s", "remaining_dec")
    fsm.bp(
        "remaining_dec",
        "logic",
        "m",
        zero="bit_drop",
        positive="remaining_read",
    )

    fsm.go("bit_drop", "bit_in", "r", "flag_read")
    fsm.go("flag_read", "flag_in", "r", "result_send")
    fsm.go("result_send", "result", "s", command_start)


def build_worker_fsm(kind: str) -> Fsm:
    if kind not in {"row", "column", "box"}:
        raise ValueError(f"unknown Sudoku worker kind: {kind}")
    fsm = Fsm()
    command_start = {
        "row": "row_read",
        "column": "column_row_drop",
        "box": "box_row_read",
    }[kind]
    _add_worker_initialization(fsm, command_start)

    if kind == "row":
        fsm.go("row_read", "command", "r", "row_store")
        fsm.go("row_store", "target_out", "s", "row_column_drop")
        fsm.go("row_column_drop", "command", "r", "row_value")
        fsm.go("row_value", "command", "r", "bit_make")
    elif kind == "column":
        fsm.go("column_row_drop", "command", "r", "column_read")
        fsm.go("column_read", "command", "r", "column_store")
        fsm.go("column_store", "target_out", "s", "column_value")
        fsm.go("column_value", "command", "r", "bit_make")
    else:
        # box = 3*(row//3) + column//3. The target ring temporarily holds
        # row, and the bit ring temporarily holds column//3.
        fsm.go("box_row_read", "command", "r", "box_row_store")
        fsm.go("box_row_store", "target_out", "s", "box_column_read")
        fsm.go("box_column_read", "command", "r", "box_column_group")
        fsm.go("box_column_group", "logic", "M3W/", "box_column_store")
        fsm.go("box_column_store", "bit_out", "s", "box_row_read_back")
        fsm.go("box_row_read_back", "target_in", "r", "box_row_group")
        fsm.go("box_row_group", "logic", "M3W/", "box_row_times_three")
        fsm.go("box_row_times_three", "logic", "M3W*M", "box_column_read_back")
        fsm.go("box_column_read_back", "bit_in", "r+", "box_target_store")
        fsm.go("box_target_store", "target_out", "s", "box_value")
        fsm.go("box_value", "command", "r", "bit_make")

    _add_worker_update(fsm, command_start)
    return fsm


def build_aggregator_fsm() -> Fsm:
    fsm = Fsm()
    fsm.go("start", "input", "@RM", "flag_two")
    fsm.go("flag_two", "input", "R+M", "flag_three")
    fsm.go("flag_three", "input", "R+", "flag_check")
    fsm.sign(
        "flag_check",
        "logic",
        "",
        negative="invalid",
        zero="valid",
        positive="invalid",
    )
    fsm.go("valid", "logic", "1", "verdict_send")
    fsm.go("invalid", "logic", "0", "verdict_send")
    fsm.go("verdict_send", "output", "s", "start")
    return fsm


def _put_ring(
    canvas: Canvas,
    *,
    room_bottom: int,
    relay_top: int,
    out_x: int,
    in_x: int,
) -> int:
    canvas.put(relay_top, out_x + 4, RELAY)
    canvas.pipe(
        [
            (room_bottom + 1, out_x),
            (relay_top + 3, out_x),
            (relay_top + 3, out_x + 3),
        ]
    )
    canvas.pipe(
        [
            (relay_top + 2, out_x + 9),
            (relay_top + 2, out_x + 12),
            (relay_top + 7, out_x + 12),
            (relay_top + 7, in_x),
            (room_bottom + 1, in_x),
        ]
    )
    return relay_top + 8


def _compile_workers() -> list[CompiledRoom]:
    return [
        compile_fsm(build_worker_fsm(kind), WORKER_ZONES)
        for kind in ("row", "column", "box")
    ]


def build_sudoku() -> str:
    workers = _compile_workers()
    worker_width = max(worker.width for worker in workers) + 2
    gap = 8
    margin = 8
    worker_offsets = [margin + index * (worker_width + gap) for index in range(3)]
    total_width = worker_offsets[-1] + worker_width + margin

    parser = compile_fsm(build_parser_fsm(), PARSER_ZONES)
    canvas = Canvas()
    parser_top = 5
    canvas.put(parser_top, 0, parser.rows)
    parser_bottom = parser_top + parser.height + 1

    input_x = parser.zones["input"]
    canvas.put(0, input_x - 1, ["+-+", "|I|", "+-+"])
    canvas.pipe([(3, input_x), (parser_top - 1, input_x)])

    broadcaster_top = parser_bottom + 9
    canvas.put(broadcaster_top, 0, build_broadcaster(total_width))
    broadcaster_bottom = broadcaster_top + 4
    broadcaster_center = total_width // 2
    command_x = parser.zones["command"]
    canvas.pipe(
        [
            (parser_bottom + 1, command_x),
            (broadcaster_top - 3, command_x),
            (broadcaster_top - 3, broadcaster_center - 1),
            (broadcaster_top - 1, broadcaster_center - 1),
        ]
    )

    workers_top = broadcaster_bottom + 10
    for offset, worker in zip(worker_offsets, workers, strict=True):
        canvas.put(workers_top, offset, worker.rows)
        worker_command_x = offset + worker.zones["command"]
        worker_bottom = workers_top + worker.height + 1
        command_corridor_x = offset - 3
        canvas.pipe(
            [
                (broadcaster_bottom + 1, worker_command_x),
                (workers_top - 3, worker_command_x),
                (workers_top - 3, command_corridor_x),
                (worker_bottom + 3, command_corridor_x),
                (worker_bottom + 3, worker_command_x),
                (worker_bottom + 1, worker_command_x),
            ]
        )

    rings_bottom = workers_top
    result_sources = []
    for offset, worker in zip(worker_offsets, workers, strict=True):
        worker_bottom = workers_top + worker.height + 1
        relay_top = worker_bottom + 7
        for in_zone, out_zone in (
            ("state_in", "state_out"),
            ("target_in", "target_out"),
            ("bit_in", "bit_out"),
            ("flag_in", "flag_out"),
        ):
            rings_bottom = max(
                rings_bottom,
                _put_ring(
                    canvas,
                    room_bottom=worker_bottom,
                    relay_top=relay_top,
                    out_x=offset + worker.zones[out_zone],
                    in_x=offset + worker.zones[in_zone],
                ),
            )
        result_sources.append((worker_bottom + 1, offset + worker.zones["result"]))

    aggregator = compile_fsm(build_aggregator_fsm(), AGGREGATOR_ZONES)
    aggregator_top = rings_bottom + 10
    middle_result_x = result_sources[1][1]
    aggregator_left = middle_result_x - aggregator.width // 2
    canvas.put(aggregator_top, aggregator_left, aggregator.rows)
    aggregator_bottom = aggregator_top + aggregator.height + 1

    left_entry_row = aggregator_top + 3
    canvas.pipe(
        [
            result_sources[0],
            (left_entry_row, result_sources[0][1]),
            (left_entry_row, aggregator_left - 1),
        ]
    )
    canvas.cells[(left_entry_row, aggregator_left - 1)] = ">"

    canvas.pipe(
        [
            result_sources[1],
            (aggregator_top - 1, result_sources[1][1]),
        ]
    )

    aggregator_right = aggregator_left + aggregator.width + 1
    right_entry_row = aggregator_top + 5
    canvas.pipe(
        [
            result_sources[2],
            (right_entry_row, result_sources[2][1]),
            (right_entry_row, aggregator_right + 1),
        ]
    )
    canvas.cells[(right_entry_row, aggregator_right + 1)] = "<"

    output_x = aggregator_left + aggregator.zones["output"]
    output_top = aggregator_bottom + 6
    canvas.put(output_top, output_x - 1, ["+-+", "|O|", "+-+"])
    canvas.pipe(
        [
            (aggregator_bottom + 1, output_x),
            (output_top - 1, output_x),
        ]
    )
    return canvas.render()


def build_sudoku_two_row() -> str:
    """Build the same Sudoku machine with its workers packed in two rows.

    The row and column workers occupy the upper module row.  The taller box
    worker is centered beneath them.  A dedicated command route descends to
    the left of both rows, while the row-worker result moves through the gap
    between module rows before descending around the box worker.
    """

    workers = _compile_workers()
    worker_width = max(worker.width for worker in workers) + 2
    gap = 4
    margin = 6
    upper_offsets = (margin, margin + worker_width + gap)
    lower_offset = (2 * worker_width + gap - worker_width) // 2 + margin
    total_width = upper_offsets[1] + worker_width

    parser = compile_fsm(build_parser_fsm(), PARSER_ZONES)
    parser_top = 5
    parser_bottom = parser_top + parser.height + 1
    broadcaster_top = parser_bottom + 5
    broadcaster_bottom = broadcaster_top + 4
    upper_top = broadcaster_bottom + 6
    lower_top = upper_top + (workers[0].height + 2) + 2 + 14
    placements = [
        (upper_top, upper_offsets[0], workers[0]),
        (upper_top, upper_offsets[1], workers[1]),
        (lower_top, lower_offset, workers[2]),
    ]

    canvas = Canvas()
    canvas.put(parser_top, 0, parser.rows)

    input_x = parser.zones["input"]
    canvas.put(0, input_x - 1, ["+-+", "|I|", "+-+"])
    canvas.pipe([(3, input_x), (parser_top - 1, input_x)])

    canvas.put(broadcaster_top, 0, build_broadcaster(total_width))
    broadcaster_center = total_width // 2
    command_x = parser.zones["command"]
    canvas.pipe(
        [
            (parser_bottom + 1, command_x),
            (broadcaster_top - 3, command_x),
            (broadcaster_top - 3, broadcaster_center - 1),
            (broadcaster_top - 1, broadcaster_center - 1),
        ]
    )

    # The upper modules retain the baseline bottom-entry command route.
    for worker_top, offset, worker in placements[:2]:
        canvas.put(worker_top, offset, worker.rows)
        worker_command_x = offset + worker.zones["command"]
        worker_bottom = worker_top + worker.height + 1
        command_corridor_x = offset - 3
        canvas.pipe(
            [
                (broadcaster_bottom + 1, worker_command_x),
                (worker_top - 3, worker_command_x),
                (worker_top - 3, command_corridor_x),
                (worker_bottom + 3, command_corridor_x),
                (worker_bottom + 3, worker_command_x),
                (worker_bottom + 1, worker_command_x),
            ]
        )

    # The box command descends outside both worker rows and enters its bottom
    # command port.  Starting it at column 2 keeps it separate from the upper
    # row worker's command corridor at column 5.
    box_top, box_offset, box_worker = placements[2]
    canvas.put(box_top, box_offset, box_worker.rows)
    box_bottom = box_top + box_worker.height + 1
    box_command_x = box_offset + box_worker.zones["command"]
    canvas.pipe(
        [
            (broadcaster_bottom + 1, 2),
            (box_bottom + 3, 2),
            (box_bottom + 3, box_command_x),
            (box_bottom + 1, box_command_x),
        ]
    )

    rings_bottom = upper_top
    result_sources = []
    for worker_top, offset, worker in placements:
        worker_bottom = worker_top + worker.height + 1
        relay_top = worker_bottom + 7
        for in_zone, out_zone in (
            ("state_in", "state_out"),
            ("target_in", "target_out"),
            ("bit_in", "bit_out"),
            ("flag_in", "flag_out"),
        ):
            rings_bottom = max(
                rings_bottom,
                _put_ring(
                    canvas,
                    room_bottom=worker_bottom,
                    relay_top=relay_top,
                    out_x=offset + worker.zones[out_zone],
                    in_x=offset + worker.zones[in_zone],
                ),
            )
        result_sources.append((worker_bottom + 1, offset + worker.zones["result"]))

    aggregator = compile_fsm(build_aggregator_fsm(), AGGREGATOR_ZONES)
    aggregator_top = rings_bottom + 3
    box_result_x = result_sources[2][1]
    aggregator_left = box_result_x - aggregator.width // 2
    canvas.put(aggregator_top, aggregator_left, aggregator.rows)
    aggregator_bottom = aggregator_top + aggregator.height + 1

    # The upper-left result first exits through the empty row gap, then
    # descends just right of the box module into a second top entry.  Using a
    # top entry avoids crossing the box command's bottom horizontal segment.
    upper_gap_row = box_top - 2
    box_right_corridor = box_offset + worker_width + 3
    canvas.pipe(
        [
            result_sources[0],
            (upper_gap_row, result_sources[0][1]),
            (upper_gap_row, box_right_corridor),
            (aggregator_top - 1, box_right_corridor),
        ]
    )

    # The box result enters from above.
    canvas.pipe(
        [
            result_sources[2],
            (aggregator_top - 1, result_sources[2][1]),
        ]
    )

    # The upper-right result already lies outside the box module.
    aggregator_right = aggregator_left + aggregator.width + 1
    right_entry_row = aggregator_top + 5
    canvas.pipe(
        [
            result_sources[1],
            (right_entry_row, result_sources[1][1]),
            (right_entry_row, aggregator_right + 1),
        ]
    )
    canvas.cells[(right_entry_row, aggregator_right + 1)] = "<"

    output_x = aggregator_left + aggregator.zones["output"]
    output_top = aggregator_bottom + 3
    canvas.put(output_top, output_x - 1, ["+-+", "|O|", "+-+"])
    canvas.pipe(
        [
            (aggregator_bottom + 1, output_x),
            (output_top - 1, output_x),
        ]
    )
    return canvas.render()
