"""Compact ring-based Matrix Multiply machine.

This variant uses one controller instead of one worker per possible output
column.  A and B live in FIFO rings.  For each row of A, the controller
initializes K partial sums, then cycles the complete B matrix once:

    for a in A[row]:
        for b in B[a-column, :]:
            sums[column] += a * b

Both matrix rings return to canonical row-major order at the end of a result
row.  The sums are then emitted in row-major order.  The nested external
ring geometry gives the two 256-value stores enough capacity without the
very wide parallel-worker field used by :mod:`littleman.matmul`.
"""

from __future__ import annotations

from .canvas import Canvas
from .gradebook import CompiledRoom, Fsm, compile_fsm

ZONES = {
    "logic": 0,
    "input": 5,
    # A's endpoints enclose all other ring endpoints.  This permits a large
    # outer U-shaped return pipe and a disjoint nested B return pipe.
    "a_in": 10,
    "n_in": 14,
    "n_out": 16,
    "m_in": 22,
    "m_out": 24,
    "k_in": 30,
    "k_out": 32,
    "work_m_in": 38,
    "work_m_out": 40,
    "factor_in": 46,
    "factor_out": 48,
    "sum_in": 54,
    "sum_out": 56,
    "b_in": 62,
    "b_out": 64,
    "a_out": 72,
    # Keep output outside the nested matrix rings.
    "output": 78,
}


def build_controller_fsm() -> Fsm:
    fsm = Fsm()

    # Read dimensions and load A.  B retains N while M is read, so *b sets
    # the exact N*M load count in BP before K replaces B.
    fsm.go("start", "input", "@rM", "n_store")
    fsm.go("n_store", "n_out", "s", "m_read")
    fsm.go("m_read", "input", "r", "m_store")
    fsm.go("m_store", "m_out", "s", "a_count")
    fsm.go("a_count", "logic", "*b", "k_read")
    fsm.go("k_read", "input", "rM", "k_store")
    fsm.go("k_store", "k_out", "s", "a_load")
    fsm.go("a_load", "input", "r", "a_store")
    fsm.go("a_store", "a_out", "s", "a_dec")
    fsm.bp("a_dec", "logic", "m", zero="b_count_m", positive="a_load")

    # Load B using M*K as the count.  Scalar rings are immediately restored.
    fsm.go("b_count_m", "m_in", "rM", "b_count_m_restore")
    fsm.go("b_count_m_restore", "m_out", "s", "b_count_k")
    fsm.go("b_count_k", "k_in", "r", "b_count_k_restore")
    fsm.go("b_count_k_restore", "k_out", "s", "b_count")
    fsm.go("b_count", "logic", "*b", "b_load")
    fsm.go("b_load", "input", "r", "b_store")
    fsm.go("b_store", "b_out", "s", "b_dec")
    fsm.bp("b_dec", "logic", "m", zero="row_start", positive="b_load")

    # The N ring is a mutable rows-remaining counter.
    fsm.go("row_start", "n_in", "r", "row_check")
    fsm.sign(
        "row_check",
        "logic",
        "",
        negative="finish",
        zero="finish",
        positive="row_decrement",
    )
    fsm.go("row_decrement", "logic", "M1W-", "row_save")
    fsm.go("row_save", "n_out", "s", "sum_count_k")

    # Seed the sum ring with K zeroes.
    fsm.go("sum_count_k", "k_in", "r", "sum_count_k_restore")
    fsm.go("sum_count_k_restore", "k_out", "s", "sum_count_set")
    fsm.go("sum_count_set", "logic", "b", "sum_zero")
    fsm.go("sum_zero", "logic", "0", "sum_zero_send")
    fsm.go("sum_zero_send", "sum_out", "s", "sum_zero_dec")
    fsm.bp(
        "sum_zero_dec",
        "logic",
        "m",
        zero="row_m_read",
        positive="sum_zero",
    )

    # work_m holds the number of A elements left in this row.  BP is free for
    # the nested K loop.
    fsm.go("row_m_read", "m_in", "r", "row_m_restore")
    fsm.go("row_m_restore", "m_out", "s", "row_m_work")
    fsm.go("row_m_work", "work_m_out", "s", "a_read")

    fsm.go("a_read", "a_in", "r", "a_restore")
    fsm.go("a_restore", "a_out", "s", "factor_store")
    fsm.go("factor_store", "factor_out", "s", "product_count_k")

    # For one A element, cycle K values from both B and the partial-sum ring.
    # The factor ring restores the A value before every multiplication.
    fsm.go("product_count_k", "k_in", "r", "product_count_k_restore")
    fsm.go(
        "product_count_k_restore",
        "k_out",
        "s",
        "product_count_set",
    )
    fsm.go("product_count_set", "logic", "b", "factor_read")
    fsm.go("factor_read", "factor_in", "rM", "factor_restore")
    fsm.go("factor_restore", "factor_out", "s", "b_read")
    fsm.go("b_read", "b_in", "r", "b_restore")
    fsm.go("b_restore", "b_out", "s", "product")
    fsm.go("product", "logic", "*M", "sum_read")
    fsm.go("sum_read", "sum_in", "r+", "sum_restore")
    fsm.go("sum_restore", "sum_out", "s", "product_dec")
    fsm.bp(
        "product_dec",
        "logic",
        "m",
        zero="factor_drop",
        positive="factor_read",
    )

    # Remove the factor and decrement the persistent M loop counter.
    fsm.go("factor_drop", "factor_in", "r", "row_m_remaining")
    fsm.go("row_m_remaining", "work_m_in", "r", "row_m_decrement")
    fsm.go("row_m_decrement", "logic", "M1W-", "row_m_check")
    fsm.sign(
        "row_m_check",
        "logic",
        "",
        negative="emit_count_k",
        zero="emit_count_k",
        positive="row_m_save",
    )
    fsm.go("row_m_save", "work_m_out", "s", "a_read")

    # The K sums are already in column order.
    fsm.go("emit_count_k", "k_in", "r", "emit_count_k_restore")
    fsm.go("emit_count_k_restore", "k_out", "s", "emit_count_set")
    fsm.go("emit_count_set", "logic", "b", "emit_read")
    fsm.go("emit_read", "sum_in", "r", "emit_send")
    fsm.go("emit_send", "output", "s", "emit_dec")
    fsm.bp(
        "emit_dec",
        "logic",
        "m",
        zero="row_start",
        positive="emit_read",
    )

    fsm.go("finish", "logic", "H", "finish")
    return fsm


VERTICAL_RELAY = [
    "+----+",
    "|>@rv|",
    "|   s|",
    "|   v|",
    "|^<<<|",
    "|^   |",
    "+----+",
]


def _put_short_ring(
    canvas: Canvas,
    *,
    controller_bottom: int,
    relay_top: int,
    out_x: int,
    in_x: int,
) -> None:
    """Place a compact ring holding at most K (16) values."""
    canvas.put(relay_top, out_x - 3, VERTICAL_RELAY)
    canvas.pipe(
        [
            (controller_bottom + 1, out_x),
            (relay_top - 1, out_x),
        ]
    )
    return_x = out_x - 4
    canvas.pipe(
        [
            (relay_top + 7, out_x + 1),
            (relay_top + 10, out_x + 1),
            (relay_top + 10, return_x),
            (controller_bottom + 1, return_x),
            (controller_bottom + 1, in_x),
        ]
    )
    # The last cell bends upward into the controller.
    canvas.cells[(controller_bottom + 1, in_x)] = "^"


def _put_relay_input(
    canvas: Canvas,
    *,
    controller_bottom: int,
    relay_top: int,
    out_x: int,
) -> tuple[int, int]:
    """Connect a controller send zone to a relay and return its output cell."""
    canvas.put(relay_top, out_x - 3, VERTICAL_RELAY)
    canvas.pipe(
        [
            (controller_bottom + 1, out_x),
            (relay_top - 1, out_x),
        ]
    )
    return relay_top + 7, out_x + 1


def _compile_controller() -> CompiledRoom:
    return compile_fsm(build_controller_fsm(), ZONES)


def build_matmul_ring() -> str:
    controller = _compile_controller()
    canvas = Canvas()
    controller_top = 5
    canvas.put(controller_top, 0, controller.rows)
    controller_bottom = controller_top + controller.height + 1

    # Input enters from below.  Several load states sit low enough in the
    # controller that a top-side input would lose nearest-pipe resolution to
    # the scalar rings.
    input_x = controller.zones["input"]
    input_top = controller_bottom + 4
    canvas.put(input_top, input_x - 1, ["+-+", "|I|", "+-+"])
    canvas.pipe(
        [
            (input_top - 1, input_x),
            (controller_bottom + 1, input_x),
        ]
    )

    relay_top = controller_bottom + 4
    for in_zone, out_zone in (
        ("n_in", "n_out"),
        ("m_in", "m_out"),
        ("k_in", "k_out"),
        ("work_m_in", "work_m_out"),
        ("factor_in", "factor_out"),
        ("sum_in", "sum_out"),
    ):
        _put_short_ring(
            canvas,
            controller_bottom=controller_bottom,
            relay_top=relay_top,
            out_x=controller.zones[out_zone],
            in_x=controller.zones[in_zone],
        )

    # A is the outer U and B is nested inside it.  B ends before A's deeper
    # return row, so none of the four long vertical segments cross.
    a_out = controller.zones["a_out"]
    a_in = controller.zones["a_in"]
    a_start = _put_relay_input(
        canvas,
        controller_bottom=controller_bottom,
        relay_top=relay_top,
        out_x=a_out,
    )
    outer_right = controller.zones["output"] - 2
    outer_deep = relay_top + 142
    canvas.pipe(
        [
            a_start,
            (a_start[0] + 2, a_start[1]),
            (a_start[0] + 2, outer_right),
            (outer_deep, outer_right),
            (outer_deep, a_in),
            (controller_bottom + 1, a_in),
        ]
    )

    b_out = controller.zones["b_out"]
    b_in = controller.zones["b_in"]
    b_start = _put_relay_input(
        canvas,
        controller_bottom=controller_bottom,
        relay_top=relay_top,
        out_x=b_out,
    )
    # Column 80 is the clear corridor between the B and A relay rooms.
    inner_right = a_start[1] - 5
    inner_deep = b_start[0] + 126
    b_return_x = b_out - 4
    canvas.pipe(
        [
            b_start,
            (b_start[0] + 2, b_start[1]),
            (b_start[0] + 2, inner_right),
            (inner_deep, inner_right),
            (inner_deep, b_return_x),
            (controller_bottom + 1, b_return_x),
            (controller_bottom + 1, b_in),
        ]
    )
    canvas.cells[(controller_bottom + 1, b_in)] = "^"

    # A dedicated column beyond both nested rings carries results to O.
    output_x = controller.zones["output"]
    output_top = outer_deep + 7
    canvas.put(output_top, output_x - 1, ["+-+", "|O|", "+-+"])
    canvas.pipe(
        [
            (controller_bottom + 1, output_x),
            (output_top - 1, output_x),
        ]
    )
    return canvas.render()


def build_matmul_ring_compact() -> str:
    """Build the same ring algorithm in a near-square external layout.

    The controller and relay rooms are byte-identical to
    :func:`build_matmul_ring`.  Only the long A, B, and output pipes move:
    A forms an outer rectangle, B folds once inside it, and a final relay
    carries output through the clear upper-right corridor.
    """
    controller = _compile_controller()
    canvas = Canvas()
    controller_top = 5
    canvas.put(controller_top, 0, controller.rows)
    controller_bottom = controller_top + controller.height + 1

    input_x = controller.zones["input"]
    input_top = controller_bottom + 4
    canvas.put(input_top, input_x - 1, ["+-+", "|I|", "+-+"])
    canvas.pipe(
        [
            (input_top - 1, input_x),
            (controller_bottom + 1, input_x),
        ]
    )

    relay_top = controller_bottom + 4
    for in_zone, out_zone in (
        ("n_in", "n_out"),
        ("m_in", "m_out"),
        ("k_in", "k_out"),
        ("work_m_in", "work_m_out"),
        ("factor_in", "factor_out"),
        ("sum_in", "sum_out"),
    ):
        _put_short_ring(
            canvas,
            controller_bottom=controller_bottom,
            relay_top=relay_top,
            out_x=controller.zones[out_zone],
            in_x=controller.zones[in_zone],
        )

    a_out = controller.zones["a_out"]
    a_in = controller.zones["a_in"]
    a_start = _put_relay_input(
        canvas,
        controller_bottom=controller_bottom,
        relay_top=relay_top,
        out_x=a_out,
    )
    outer_top = a_start[0] + 2
    outer_bottom = controller_bottom + 51
    canvas.pipe(
        [
            a_start,
            (outer_top, a_start[1]),
            (outer_top, 175),
            (outer_bottom, 175),
            (outer_bottom, a_in),
            (controller_bottom + 1, a_in),
        ]
    )

    b_out = controller.zones["b_out"]
    b_in = controller.zones["b_in"]
    b_start = _put_relay_input(
        canvas,
        controller_bottom=controller_bottom,
        relay_top=relay_top,
        out_x=b_out,
    )
    b_return_x = b_out - 4
    inner_top = b_start[0] + 6
    inner_fold = b_start[0] + 8
    inner_bottom = controller_bottom + 43
    canvas.pipe(
        [
            b_start,
            (inner_top, b_start[1]),
            (inner_top, 170),
            (inner_bottom, 170),
            (inner_bottom, 100),
            (inner_fold, 100),
            (inner_fold, b_return_x),
            (controller_bottom + 1, b_return_x),
            (controller_bottom + 1, b_in),
        ]
    )
    canvas.cells[(controller_bottom + 1, b_in)] = "^"

    # Output uses the ninth vertical relay and stays outside A's right edge.
    output_start = _put_relay_input(
        canvas,
        controller_bottom=controller_bottom,
        relay_top=relay_top,
        out_x=controller.zones["output"],
    )
    output_top = controller_bottom + 27
    output_x = 181
    canvas.put(output_top, output_x - 1, ["+-+", "|O|", "+-+"])
    canvas.pipe(
        [
            output_start,
            (output_start[0] + 1, output_start[1]),
            (output_start[0] + 1, output_x),
            (output_top - 1, output_x),
        ]
    )
    return canvas.render()
