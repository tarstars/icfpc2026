"""Generated Matrix Multiply machine with 16 parallel column workers.

The parser stores A in a ring.  During B loading it broadcasts ``(column,
value)`` pairs; worker j retains only column j in its private ring.  For each
row of A the parser broadcasts ``(1, value)`` pairs followed by ``(0, 0)``.
Active workers multiply against their B column and accumulate a dot product.

At row end, a token travels through workers 1..16.  Active workers emit their
sum before forwarding the token, which serializes results in row-major order.
Worker 16 acknowledges the parser so the next A row cannot overtake output.
"""

from __future__ import annotations

from .canvas import Canvas
from .gradebook import CompiledRoom, Fsm, compile_fsm

PARSER_ZONES = {
    "logic": 0,
    "input": 5,
    "row_in": 15,
    "row_out": 20,
    "m_in": 45,
    "m_out": 50,
    "k_in": 75,
    "k_out": 80,
    "col_in": 105,
    "col_out": 110,
    "a_in": 135,
    "a_out": 140,
    "command": 125,
    "ack": 175,
}


def build_parser_fsm() -> Fsm:
    fsm = Fsm()

    # Preserve N, M, and K in one-value rings.  B retains N while M is read,
    # so multiplication gives the exact A element count in BP.
    fsm.go("start", "input", "@rM", "n_store")
    fsm.go("n_store", "row_out", "s", "m_read")
    fsm.go("m_read", "input", "r", "m_store")
    fsm.go("m_store", "m_out", "s", "a_count")
    fsm.go("a_count", "logic", "*b", "k_read")
    fsm.go("k_read", "input", "r", "k_store")
    fsm.go("k_store", "k_out", "s", "a_load")

    fsm.go("a_load", "input", "r", "a_store")
    fsm.go("a_store", "a_out", "s", "a_dec")
    fsm.bp("a_dec", "logic", "m", zero="b_count_m", positive="a_load")

    # BP = M*K.  The scalar rings are immediately requeued.
    fsm.go("b_count_m", "m_in", "rM", "b_count_m_restore")
    fsm.go("b_count_m_restore", "m_out", "s", "b_count_k")
    fsm.go("b_count_k", "k_in", "r", "b_count_k_restore")
    fsm.go("b_count_k_restore", "k_out", "s", "b_count_mul")
    fsm.go("b_count_mul", "logic", "*b1", "col_init")
    fsm.go("col_init", "col_out", "s", "b_col")

    # Broadcast every B value with its one-based column number.
    fsm.go("b_col", "col_in", "rM", "b_col_send")
    fsm.go("b_col_send", "command", "s", "b_value")
    fsm.go("b_value", "input", "r", "b_value_send")
    fsm.go("b_value_send", "command", "s", "col_next")
    fsm.go("col_next", "logic", "1+M", "col_k")
    fsm.go("col_k", "k_in", "r", "col_k_restore")
    fsm.go("col_k_restore", "k_out", "s", "col_compare")
    fsm.sign(
        "col_compare",
        "logic",
        "-",
        negative="col_reset",
        zero="col_keep",
        positive="col_keep",
    )
    fsm.go("col_keep", "logic", "W", "col_save")
    fsm.go("col_reset", "logic", "1", "col_save")
    fsm.go("col_save", "col_out", "s", "b_dec")
    fsm.bp("b_dec", "logic", "m", zero="b_end_type", positive="b_col")

    # Zero command terminates B loading.  The second zero is its fixed pad.
    fsm.go("b_end_type", "logic", "0", "b_end_type_send")
    fsm.go("b_end_type_send", "command", "s", "b_end_pad")
    fsm.go("b_end_pad", "logic", "0", "b_end_pad_send")
    fsm.go("b_end_pad_send", "command", "s", "row_start")

    # Row counter is N..0.  BP is free for the M values in each row.
    fsm.go("row_start", "row_in", "r", "row_check")
    fsm.sign(
        "row_check",
        "logic",
        "",
        negative="finish",
        zero="finish",
        positive="row_decrement",
    )
    fsm.go("row_decrement", "logic", "M1W-", "row_save")
    fsm.go("row_save", "row_out", "s", "row_m")
    fsm.go("row_m", "m_in", "rb", "row_m_restore")
    fsm.go("row_m_restore", "m_out", "s", "a_type")

    fsm.go("a_type", "logic", "1", "a_type_send")
    fsm.go("a_type_send", "command", "s", "a_ring_read")
    fsm.go("a_ring_read", "a_in", "r", "a_ring_write")
    fsm.go("a_ring_write", "a_out", "s", "a_value_send")
    fsm.go("a_value_send", "command", "s", "a_row_dec")
    fsm.bp("a_row_dec", "logic", "m", zero="row_end_type", positive="a_type")

    fsm.go("row_end_type", "logic", "0", "row_end_type_send")
    fsm.go("row_end_type_send", "command", "s", "row_end_pad")
    fsm.go("row_end_pad", "logic", "0", "row_end_pad_send")
    fsm.go("row_end_pad_send", "command", "s", "row_ack")
    fsm.go("row_ack", "ack", "r", "row_start")
    fsm.go("finish", "logic", "H", "finish")
    return fsm


WORKER_ZONES = {
    "logic": 0,
    "command": 5,
    "b_in": 23,
    "b_out": 30,
    "state_in": 45,
    "state_out": 55,
    "token_in": 70,
    "result": 78,
    "token_out": 86,
}


def build_worker_fsm(column: int) -> Fsm:
    fsm = Fsm()
    token_target = "token_emit" if column == 1 else "token_wait"

    fsm.go("start", "logic", "@0", "sum_init")
    fsm.go("sum_init", "state_out", "s", "load_col")
    fsm.go("load_col", "command", "rM", "load_col_check")
    fsm.sign(
        "load_col_check",
        "logic",
        "",
        negative="load_skip",
        zero="load_end_pad",
        positive="load_compare",
    )
    fsm.sign(
        "load_compare",
        "logic",
        f"`{column}`-",
        negative="load_skip",
        zero="load_value",
        positive="load_skip",
    )
    fsm.go("load_skip", "command", "r", "load_col")
    fsm.go("load_value", "command", "r", "load_value_store")
    fsm.go("load_value_store", "b_out", "s", "load_col")

    # Let every stored B value reach the incoming parking pipe, then remember
    # its count in BP.  BP>0 is the persistent active-column flag.
    fsm.go("load_end_pad", "command", "r", "load_settle")
    fsm.go("load_settle", "logic", "." * 80, "active_count")
    fsm.go("active_count", "b_in", "q", "command_type")

    fsm.go("command_type", "command", "r", "command_check")
    fsm.sign(
        "command_check",
        "logic",
        "",
        negative="row_end_pad",
        zero="row_end_pad",
        positive="active_branch",
    )
    # Keep this command receive adjacent to command_check.  Later accumulator
    # states sit nearer the bottom-side B/state pipes.
    fsm.go("row_end_pad", "command", "r", token_target)
    fsm.bp(
        "active_branch",
        "logic",
        "",
        zero="inactive_value",
        positive="active_value",
    )
    fsm.go("inactive_value", "command", "r", "command_type")

    # A=value goes to B; B-column value is read/requeued in A.  Product is
    # parked in B while the accumulated sum is received into A.
    fsm.go("active_value", "command", "rM", "b_value")
    fsm.go("b_value", "b_in", "r", "b_restore")
    fsm.go("b_restore", "b_out", "s", "product")
    fsm.go("product", "logic", "*M", "sum_read")
    fsm.go("sum_read", "state_in", "r+", "sum_write")
    fsm.go("sum_write", "state_out", "s", "command_type")

    if column > 1:
        fsm.go("token_wait", "token_in", "r", "token_emit")
    fsm.bp(
        "token_emit",
        "logic",
        "",
        zero="token_send",
        positive="result_read",
    )
    fsm.go("result_read", "state_in", "r", "result_send")
    fsm.go("result_send", "result", "s", "sum_zero")
    fsm.go("sum_zero", "logic", "0", "sum_reset")
    fsm.go("sum_reset", "state_out", "s", "token_send")
    fsm.go("token_send", "token_out", "0s", "command_type")
    return fsm


RELAY = [
    "+---+",
    "| @v|",
    "|>sv|",
    "|^r<|",
    "+---+",
]


def build_broadcaster(width: int) -> list[str]:
    grid = [[" "] * width for _ in range(5)]
    for col in range(width):
        grid[0][col] = grid[4][col] = "-"
    for row in range(5):
        grid[row][0] = grid[row][-1] = "|"
    for row, col in ((0, 0), (0, width - 1), (4, 0), (4, width - 1)):
        grid[row][col] = "+"
    center = width // 2
    for row, col, char in (
        (1, center - 3, ">"),
        (1, center - 2, "@"),
        (1, center - 1, "R"),
        (1, center, "S"),
        (1, center + 1, "v"),
        (2, center - 3, "^"),
        (2, center + 1, "v"),
        (3, center - 3, "^"),
        (3, center + 1, "<"),
    ):
        grid[row][col] = char
    return ["".join(row) for row in grid]


def build_result_collector(width: int) -> list[str]:
    grid = [[" "] * width for _ in range(5)]
    for col in range(width):
        grid[0][col] = grid[4][col] = "-"
    for row in range(5):
        grid[row][0] = grid[row][-1] = "|"
    for row, col in ((0, 0), (0, width - 1), (4, 0), (4, width - 1)):
        grid[row][col] = "+"
    center = width // 2
    for row, col, char in (
        (1, center - 3, ">"),
        (1, center - 2, "@"),
        (1, center - 1, "R"),
        (1, center, "s"),
        (1, center + 1, "v"),
        (2, center - 3, "^"),
        (2, center + 1, "v"),
        (3, center - 3, "^"),
        (3, center + 1, "<"),
    ):
        grid[row][col] = char
    return ["".join(row) for row in grid]


def _put_scalar_ring(
    canvas: Canvas,
    *,
    parser_bottom: int,
    relay_top: int,
    out_x: int,
    in_x: int,
) -> int:
    canvas.put(relay_top, out_x + 4, RELAY)
    canvas.pipe(
        [
            (parser_bottom + 1, out_x),
            (relay_top + 3, out_x),
            (relay_top + 3, out_x + 3),
        ]
    )
    canvas.pipe(
        [
            (relay_top + 2, out_x + 9),
            (relay_top + 2, out_x + 12),
            (relay_top + 6, out_x + 12),
            (relay_top + 6, in_x),
            (parser_bottom + 1, in_x),
        ]
    )
    return relay_top + 7


def _compile_workers() -> list[CompiledRoom]:
    return [
        compile_fsm(build_worker_fsm(column), WORKER_ZONES) for column in range(1, 17)
    ]


def build_matmul() -> str:
    workers = _compile_workers()
    worker_width = max(worker.width for worker in workers) + 2
    gap = 6
    margin = 8
    worker_offsets = [margin + i * (worker_width + gap) for i in range(16)]
    total_width = worker_offsets[-1] + worker_width + margin

    parser = compile_fsm(build_parser_fsm(), PARSER_ZONES)
    canvas = Canvas()
    parser_top = 5
    canvas.put(parser_top, 0, parser.rows)
    parser_bottom = parser_top + parser.height + 1

    # Input and final ack enter from below alongside the scalar rings, each at
    # its own zone.  This keeps every nearest receive unambiguous.
    input_x = parser.zones["input"]
    input_top = parser_bottom + 4
    canvas.put(input_top, input_x - 1, ["+-+", "|I|", "+-+"])
    canvas.pipe([(input_top - 1, input_x), (parser_bottom + 1, input_x)])

    scalar_top = parser_bottom + 8
    scalar_bottom = scalar_top
    for in_zone, out_zone in (
        ("row_in", "row_out"),
        ("m_in", "m_out"),
        ("k_in", "k_out"),
        ("col_in", "col_out"),
    ):
        scalar_bottom = max(
            scalar_bottom,
            _put_scalar_ring(
                canvas,
                parser_bottom=parser_bottom,
                relay_top=scalar_top,
                out_x=parser.zones[out_zone],
                in_x=parser.zones[in_zone],
            ),
        )

    # A ring.  Its return pipe traverses most of the machine width and has
    # ample capacity for all 256 values.
    a_out = parser.zones["a_out"]
    a_in = parser.zones["a_in"]
    a_relay_top = scalar_bottom + 6
    canvas.put(a_relay_top, a_out + 4, RELAY)
    canvas.pipe(
        [
            (parser_bottom + 1, a_out),
            (a_relay_top + 3, a_out),
            (a_relay_top + 3, a_out + 3),
        ]
    )
    a_return_row = a_relay_top + 10
    canvas.pipe(
        [
            (a_relay_top + 2, a_out + 9),
            (a_relay_top + 2, total_width - 4),
            (a_return_row, total_width - 4),
            (a_return_row, a_in),
            (parser_bottom + 1, a_in),
        ]
    )

    broadcaster_top = a_return_row + 8
    canvas.put(broadcaster_top, 0, build_broadcaster(total_width))
    broadcaster_bottom = broadcaster_top + 4
    broadcaster_center = total_width // 2
    parser_command_x = parser.zones["command"]
    canvas.pipe(
        [
            (parser_bottom + 1, parser_command_x),
            (broadcaster_top - 3, parser_command_x),
            (broadcaster_top - 3, broadcaster_center - 1),
            (broadcaster_top - 1, broadcaster_center - 1),
        ]
    )

    workers_top = broadcaster_bottom + 10
    for offset, worker in zip(worker_offsets, workers, strict=True):
        canvas.put(workers_top, offset, worker.rows)
        command_x = offset + worker.zones["command"]
        canvas.pipe(
            [
                (broadcaster_bottom + 1, command_x),
                (workers_top - 1, command_x),
            ]
        )

    rings_bottom = workers_top
    result_sources: list[tuple[int, int]] = []
    for offset, worker in zip(worker_offsets, workers, strict=True):
        bottom = workers_top + worker.height + 1
        b_out = offset + worker.zones["b_out"]
        b_in = offset + worker.zones["b_in"]
        state_out = offset + worker.zones["state_out"]
        state_in = offset + worker.zones["state_in"]
        result_x = offset + worker.zones["result"]

        state_top = bottom + 6
        canvas.put(state_top, state_out + 4, RELAY)
        canvas.pipe(
            [
                (bottom + 1, state_out),
                (state_top + 3, state_out),
                (state_top + 3, state_out + 3),
            ]
        )
        canvas.pipe(
            [
                (state_top + 2, state_out + 9),
                (state_top + 2, state_out + 12),
                (state_top + 6, state_out + 12),
                (state_top + 6, state_in),
                (bottom + 1, state_in),
            ]
        )

        b_top = bottom + 18
        canvas.put(b_top, b_out + 4, RELAY)
        canvas.pipe(
            [
                (bottom + 1, b_out),
                (b_top + 3, b_out),
                (b_top + 3, b_out + 3),
            ]
        )
        canvas.pipe(
            [
                (b_top + 2, b_out + 9),
                (b_top + 2, b_out + 16),
                (b_top + 9, b_out + 16),
                (b_top + 9, b_in),
                (bottom + 1, b_in),
            ]
        )
        result_sources.append((bottom + 1, result_x))
        rings_bottom = max(rings_bottom, b_top + 10)

    # Completion/output token passes left-to-right across all workers.
    token_row = rings_bottom + 3
    for index in range(15):
        source = workers[index]
        target = workers[index + 1]
        source_x = worker_offsets[index] + source.zones["token_out"]
        target_x = worker_offsets[index + 1] + target.zones["token_in"]
        source_bottom = workers_top + source.height + 1
        target_bottom = workers_top + target.height + 1
        canvas.pipe(
            [
                (source_bottom + 1, source_x),
                (token_row, source_x),
                (token_row, target_x),
                (target_bottom + 1, target_x),
            ]
        )

    # Worker 16 acknowledges the parser around the far-right edge.
    final_worker = workers[-1]
    final_token_x = worker_offsets[-1] + final_worker.zones["token_out"]
    final_bottom = workers_top + final_worker.height + 1
    parser_ack_x = parser.zones["ack"]
    far_right = total_width + 3
    canvas.pipe(
        [
            (final_bottom + 1, final_token_x),
            (token_row, final_token_x),
            (token_row, far_right),
            (parser_bottom + 3, far_right),
            (parser_bottom + 3, parser_ack_x),
            (parser_bottom + 1, parser_ack_x),
        ]
    )

    collector_top = rings_bottom + 9
    canvas.put(collector_top, 0, build_result_collector(total_width))
    for source in result_sources:
        canvas.pipe([source, (collector_top - 1, source[1])])

    output_top = collector_top + 10
    output_x = total_width // 2
    canvas.put(output_top, output_x - 1, ["+-+", "|O|", "+-+"])
    canvas.pipe([(collector_top + 5, output_x), (output_top - 1, output_x)])
    return canvas.render()
