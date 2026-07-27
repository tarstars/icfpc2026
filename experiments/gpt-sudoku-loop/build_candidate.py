"""Build the tagged-update-loop successor to accepted ``sudoku_05``."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from littleman.alexey_squeeze import squeeze
from littleman.alexey_stairfold import fold_room
from littleman.canvas import Canvas
from littleman.gradebook import Fsm, compile_fsm

HERE = Path(__file__).resolve().parent
PARENT_GENERATOR = HERE.parent / "gpt-submission-candidates" / "sudoku_single_generator.py"


def _parent():
    spec = importlib.util.spec_from_file_location("gpt_sudoku_parent", PARENT_GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(PARENT_GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_fsm() -> Fsm:
    f = Fsm()
    f.go("start", "logic", "@`27`b", "init_zero")
    f.go("init_zero", "logic", "0", "init_send")
    f.go("init_send", "state_out", "s", "init_dec")
    f.bp("init_dec", "logic", "m", zero="read_r", positive="init_zero")

    f.go("read_r", "input", "r", "store_r")
    f.go("store_r", "r_out", "s", "skip1")
    f.go("skip1", "skip_out", "s", "read_c")
    f.go("read_c", "input", "r", "store_c")
    f.go("store_c", "c_out", "s", "read_v")
    f.go("read_v", "input", "r", "make_bit")
    f.go("make_bit", "logic", "M1W-W{", "store_bit")
    f.go("store_bit", "bit_out", "s", "skip2_c")

    f.go("skip2_c", "c_in", "rM", "skip2_c_restore")
    f.go("skip2_c_restore", "c_out", "s", "skip2_r")
    f.go("skip2_r", "r_in", "r", "skip2_r_restore")
    f.go("skip2_r_restore", "r_out", "s", "skip2_calc")
    f.go("skip2_calc", "logic", "W-M8W+", "skip2_send")
    f.go("skip2_send", "skip_out", "s", "box_r")

    f.go("box_r", "r_in", "r", "box_r_restore")
    f.go("box_r_restore", "r_out", "s", "box_r_div")
    f.go("box_r_div", "logic", "M3W/M3W*", "box_partial")
    f.go("box_partial", "box_out", "s", "box_c")
    f.go("box_c", "c_in", "r", "box_c_restore")
    f.go("box_c_restore", "c_out", "s", "box_c_div")
    f.go("box_c_div", "logic", "M3W/M", "box_partial_read")
    f.go("box_partial_read", "box_in", "r+", "box_store")
    f.go("box_store", "box_out", "s", "skip3_box")

    f.go("skip3_box", "box_in", "rM", "skip3_box_restore")
    f.go("skip3_box_restore", "box_out", "s", "skip3_c")
    f.go("skip3_c", "c_in", "r", "skip3_c_restore")
    f.go("skip3_c_restore", "c_out", "s", "skip3_calc")
    f.go("skip3_calc", "logic", "W-M8W+", "skip3_send")
    f.go("skip3_send", "skip_out", "s", "tail_box")

    # Fourth count is tagged: box - 9 = -(tail + 1), in -9..-1.
    f.go("tail_box", "box_in", "rM9W-", "tail_send")
    f.go("tail_send", "skip_out", "s", "drop_r")
    f.go("drop_r", "r_in", "r", "drop_c")
    f.go("drop_c", "c_in", "r", "next_count")

    # The three nonnegative tokens reuse one update body.
    f.go("next_count", "skip_in", "r", "count_check")
    f.sign("count_check", "logic", "", negative="tail_decode",
           zero="mask", positive="skip_set")
    f.bp("skip_set", "logic", "b", zero="mask", positive="skip_read")
    f.go("skip_read", "state_in", "r", "skip_restore")
    f.go("skip_restore", "state_out", "s", "skip_dec")
    f.bp("skip_dec", "logic", "m", zero="mask", positive="skip_read")

    f.go("mask", "state_in", "r", "old1")
    f.go("old1", "old_out", "s", "old2")
    f.go("old2", "old_out", "s", "bit")
    f.go("bit", "bit_in", "rM", "bit_restore")
    f.go("bit_restore", "bit_out", "s", "dup_old")
    f.go("dup_old", "old_in", "r&", "flag")
    f.go("flag", "flag_out", "s", "update_old")
    f.go("update_old", "old_in", "r|", "state")
    f.go("state", "state_out", "s", "next_count")

    f.go("tail_decode", "logic", "NM1W-", "tail_set")
    f.bp("tail_set", "logic", "b", zero="drop_bit", positive="tail_read")
    f.go("tail_read", "state_in", "r", "tail_restore")
    f.go("tail_restore", "state_out", "s", "tail_dec")
    f.bp("tail_dec", "logic", "m", zero="drop_bit", positive="tail_read")

    f.go("drop_bit", "bit_in", "r", "flag1")
    f.go("flag1", "flag_in", "rM", "flag2")
    f.go("flag2", "flag_in", "r+M", "flag3")
    f.go("flag3", "flag_in", "r+", "check")
    f.sign("check", "logic", "", negative="invalid", zero="valid", positive="invalid")
    f.go("valid", "logic", "1", "send")
    f.go("invalid", "logic", "0", "send")
    f.go("send", "output", "s", "read_r")
    return f


def build() -> str:
    p = _parent()
    controller = compile_fsm(build_fsm(), p.ZONES, right_padding=1)
    canvas = Canvas()
    top = 4
    canvas.put(top, 0, controller.rows)
    bottom = top + controller.height + 1
    relay_top = bottom + 5
    input_x = controller.zones["input"]
    canvas.put(relay_top, input_x - 1, ["+-+", "|I|", "+-+"])
    canvas.pipe([(relay_top - 1, input_x), (bottom + 1, input_x)])
    for in_name, out_name, depth in (
        ("state_in", "state_out", 8), ("skip_in", "skip_out", 0),
        ("bit_in", "bit_out", 0), ("old_in", "old_out", 0),
        ("flag_in", "flag_out", 0), ("r_in", "r_out", 0),
        ("c_in", "c_out", 0), ("box_in", "box_out", 0),
    ):
        p._put_ring(canvas, bottom=bottom, relay_top=relay_top,
                    in_x=controller.zones[in_name],
                    out_x=controller.zones[out_name], extra_depth=depth)
    output_x = controller.zones["output"]
    output_top = relay_top + 17
    canvas.put(output_top, output_x - 1, ["+-+", "|O|", "+-+"])
    canvas.pipe([(bottom + 1, output_x), (output_top - 1, output_x)])

    folded, freed = fold_room(canvas.render(), 0)
    if freed != 54:
        raise AssertionError(f"folded rows drifted: {freed}")
    candidate, rows, cols = squeeze(folded, rows=True, cols=True)
    if (rows, cols) != (72, 54):
        raise AssertionError(f"squeeze drifted: {(rows, cols)}")
    lines = candidate.rstrip("\n").splitlines()
    if (max(map(len, lines)), len(lines)) != (77, 101):
        raise AssertionError("dimension drift")
    return candidate


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: build_candidate.py OUTPUT.man")
    Path(sys.argv[1]).write_text(build())


if __name__ == "__main__":
    main()
