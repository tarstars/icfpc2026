"""Single-state-ring Sudoku auditor candidate.

The accepted baseline broadcasts each cell to three independent workers.  This
variant keeps all 27 row/column/box masks in one FIFO ring and updates the three
selected masks sequentially.  The state ring is restored to canonical order
before every verdict.
"""

from __future__ import annotations

from littleman.canvas import Canvas
from littleman.gradebook import Fsm, compile_fsm
from littleman.matmul_ring import VERTICAL_RELAY

ZONES = {
    "logic": 0,
    "input": 5,
    "state_in": 12,
    "state_out": 15,
    "skip_in": 23,
    "skip_out": 26,
    "bit_in": 34,
    "bit_out": 37,
    "old_in": 45,
    "old_out": 48,
    "flag_in": 56,
    "flag_out": 59,
    "r_in": 67,
    "r_out": 70,
    "c_in": 78,
    "c_out": 81,
    "box_in": 89,
    "box_out": 92,
    "output": 101,
}


def _add_skip(fsm: Fsm, prefix: str, next_name: str) -> None:
    fsm.go(f"{prefix}_count", "skip_in", "r", f"{prefix}_set")
    fsm.bp(
        f"{prefix}_set",
        "logic",
        "b",
        zero=next_name,
        positive=f"{prefix}_read",
    )
    fsm.go(f"{prefix}_read", "state_in", "r", f"{prefix}_restore")
    fsm.go(f"{prefix}_restore", "state_out", "s", f"{prefix}_dec")
    fsm.bp(
        f"{prefix}_dec",
        "logic",
        "m",
        zero=next_name,
        positive=f"{prefix}_read",
    )


def _add_update(fsm: Fsm, prefix: str, next_name: str) -> None:
    _add_skip(fsm, f"{prefix}_skip", f"{prefix}_mask")
    # Duplicate the old mask.  One copy is used for old&bit, one for old|bit.
    fsm.go(f"{prefix}_mask", "state_in", "r", f"{prefix}_old1")
    fsm.go(f"{prefix}_old1", "old_out", "s", f"{prefix}_old2")
    fsm.go(f"{prefix}_old2", "old_out", "s", f"{prefix}_bit")
    fsm.go(f"{prefix}_bit", "bit_in", "rM", f"{prefix}_bit_restore")
    fsm.go(f"{prefix}_bit_restore", "bit_out", "s", f"{prefix}_dup_old")
    fsm.go(f"{prefix}_dup_old", "old_in", "r&", f"{prefix}_flag")
    fsm.go(f"{prefix}_flag", "flag_out", "s", f"{prefix}_update_old")
    fsm.go(f"{prefix}_update_old", "old_in", "r|", f"{prefix}_state")
    fsm.go(f"{prefix}_state", "state_out", "s", next_name)


def build_fsm() -> Fsm:
    fsm = Fsm()
    # Seed the canonical [row0..8, col0..8, box0..8] mask ring.
    fsm.go("start", "logic", "@`27`b", "init_zero")
    fsm.go("init_zero", "logic", "0", "init_send")
    fsm.go("init_send", "state_out", "s", "init_dec")
    fsm.bp("init_dec", "logic", "m", zero="read_r", positive="init_zero")

    # Read r, c, v.  Keep r/c/box in one-token rings while deriving the four
    # skip counts that partition a 27-token state-ring scan.
    fsm.go("read_r", "input", "r", "store_r")
    fsm.go("store_r", "r_out", "s", "skip1")
    fsm.go("skip1", "skip_out", "s", "read_c")
    fsm.go("read_c", "input", "r", "store_c")
    fsm.go("store_c", "c_out", "s", "read_v")
    fsm.go("read_v", "input", "r", "make_bit")
    fsm.go("make_bit", "logic", "M1W-W{", "store_bit")
    fsm.go("store_bit", "bit_out", "s", "skip2_c")

    # skip2 = (9+c) - r - 1 = 8 + c - r.
    fsm.go("skip2_c", "c_in", "rM", "skip2_c_restore")
    fsm.go("skip2_c_restore", "c_out", "s", "skip2_r")
    fsm.go("skip2_r", "r_in", "r", "skip2_r_restore")
    fsm.go("skip2_r_restore", "r_out", "s", "skip2_calc")
    fsm.go("skip2_calc", "logic", "W-M8W+", "skip2_send")
    fsm.go("skip2_send", "skip_out", "s", "box_r")

    # box = 3*(r//3) + c//3.
    fsm.go("box_r", "r_in", "r", "box_r_restore")
    fsm.go("box_r_restore", "r_out", "s", "box_r_div")
    fsm.go("box_r_div", "logic", "M3W/M3W*", "box_partial")
    fsm.go("box_partial", "box_out", "s", "box_c")
    fsm.go("box_c", "c_in", "r", "box_c_restore")
    fsm.go("box_c_restore", "c_out", "s", "box_c_div")
    fsm.go("box_c_div", "logic", "M3W/M", "box_partial_read")
    fsm.go("box_partial_read", "box_in", "r+", "box_store")
    fsm.go("box_store", "box_out", "s", "skip3_box")

    # skip3 = (18+box) - (9+c) - 1 = 8 + box - c.
    fsm.go("skip3_box", "box_in", "rM", "skip3_box_restore")
    fsm.go("skip3_box_restore", "box_out", "s", "skip3_c")
    fsm.go("skip3_c", "c_in", "r", "skip3_c_restore")
    fsm.go("skip3_c_restore", "c_out", "s", "skip3_calc")
    fsm.go("skip3_calc", "logic", "W-M8W+", "skip3_send")
    fsm.go("skip3_send", "skip_out", "s", "skip4_box")

    # skip4 = 27 - (18+box) - 1 = 8 - box.
    fsm.go("skip4_box", "box_in", "rN", "skip4_calc")
    fsm.go("skip4_calc", "logic", "M8W+", "skip4_send")
    fsm.go("skip4_send", "skip_out", "s", "drop_r")
    fsm.go("drop_r", "r_in", "r", "drop_c")
    fsm.go("drop_c", "c_in", "r", "update1_skip_count")

    _add_update(fsm, "update1", "update2_skip_count")
    _add_update(fsm, "update2", "update3_skip_count")
    _add_update(fsm, "update3", "tail_count")
    _add_skip(fsm, "tail", "drop_bit")

    fsm.go("drop_bit", "bit_in", "r", "flag1")
    fsm.go("flag1", "flag_in", "rM", "flag2")
    fsm.go("flag2", "flag_in", "r+M", "flag3")
    fsm.go("flag3", "flag_in", "r+", "check")
    fsm.sign("check", "logic", "", negative="invalid", zero="valid", positive="invalid")
    fsm.go("valid", "logic", "1", "send")
    fsm.go("invalid", "logic", "0", "send")
    fsm.go("send", "output", "s", "read_r")
    return fsm


def _put_ring(
    canvas: Canvas,
    *,
    bottom: int,
    relay_top: int,
    in_x: int,
    out_x: int,
    extra_depth: int = 0,
) -> None:
    canvas.put(relay_top, out_x - 3, VERTICAL_RELAY)
    canvas.pipe([(bottom + 1, out_x), (relay_top - 1, out_x)])
    return_x = out_x - 4
    deep = relay_top + 10 + extra_depth
    canvas.pipe(
        [
            (relay_top + 7, out_x + 1),
            (deep, out_x + 1),
            (deep, return_x),
            (bottom + 1, return_x),
            (bottom + 1, in_x),
        ]
    )
    canvas.cells[(bottom + 1, in_x)] = "^"


def build_sudoku_single() -> str:
    controller = compile_fsm(build_fsm(), ZONES, right_padding=1)
    canvas = Canvas()
    top = 4
    canvas.put(top, 0, controller.rows)
    bottom = top + controller.height + 1
    relay_top = bottom + 5

    # Input and output occupy the two edge zones.  Every other connection is
    # an independent local ring below the controller.
    input_x = controller.zones["input"]
    canvas.put(relay_top, input_x - 1, ["+-+", "|I|", "+-+"])
    canvas.pipe([(relay_top - 1, input_x), (bottom + 1, input_x)])

    for in_name, out_name, depth in (
        ("state_in", "state_out", 8),   # >=27 cells
        ("skip_in", "skip_out", 0),    # four counts
        ("bit_in", "bit_out", 0),
        ("old_in", "old_out", 0),      # two old-mask copies
        ("flag_in", "flag_out", 0),    # three flags
        ("r_in", "r_out", 0),
        ("c_in", "c_out", 0),
        ("box_in", "box_out", 0),
    ):
        _put_ring(
            canvas,
            bottom=bottom,
            relay_top=relay_top,
            in_x=controller.zones[in_name],
            out_x=controller.zones[out_name],
            extra_depth=depth,
        )

    output_x = controller.zones["output"]
    output_top = relay_top + 17
    canvas.put(output_top, output_x - 1, ["+-+", "|O|", "+-+"])
    canvas.pipe([(bottom + 1, output_x), (output_top - 1, output_x)])
    return canvas.render()
