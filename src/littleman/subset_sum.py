"""Meet-in-the-middle Subset Sum machine.

The twenty input slots are split into two ten-value halves (missing tail
values are padded with zero).  Each generator enumerates 1,024 subset sums
and a ten-bit lexicographic mask.  Stable radix sorters order the first half
by descending sum and the second by ascending sum, with masks descending
inside equal-sum groups.  A two-pointer merge then examines at most 2,048
pairs and retains the lexicographically greatest combined mask.

The program is intentionally a correctness-first generated layout.  Large
sorter FIFO pipes provide enough capacity for 1,024 triples without relying
on timing-sensitive ``q`` counts.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from math import isqrt

from .alexey_sort_pipe import build_stage as build_sort_stage
from .canvas import Canvas
from .gradebook import CompiledRoom, Fsm, compile_fsm
from .matmul import RELAY

PARSER_ZONES = {
    "logic": 0,
    "input": 10,
    "values": 30,
    "gen_a": 110,
    "target": 130,
    "gen_b": 160,
    "rem_out": 300,
    "rem_in": 310,
    "pad_out": 400,
    "pad_in": 410,
}

GENERATOR_ZONES = {
    "logic": 0,
    "input": 10,
    "table": 25,
    "value_out": 500,
    "value_in": 510,
    "sum_out": 650,
    "sum_in": 660,
    "counter_out": 800,
    "counter_in": 810,
    "work_out": 950,
    "work_in": 960,
    "lex_out": 1100,
    "lex_in": 1110,
}

COUNTER_ZONES = {
    "logic": 0,
    "output": 20,
    "counter_out": 100,
    "counter_in": 110,
}

STAGE_ZONES = {
    "logic": 0,
    "init": 10,
    "stream_in": 40,
    "stream_out": 50,
    "value_out": 200,
    "value_in": 210,
}

SORTER_ZONES = {
    "logic": 0,
    "input": 10,
    "output": 280,
    "main_out": 400,
    "main_in": 410,
    "zero_out": 550,
    "zero_in": 560,
    "one_out": 700,
    "one_in": 710,
    "pass_out": 850,
    "pass_in": 860,
}

SORTER4_ZONES = {
    "logic": 0,
    "input": 4,
    "output": 8,
    "main_out": 12,
    "main_in": 16,
    "bucket0_out": 20,
    "bucket0_in": 24,
    "bucket1_out": 28,
    "bucket1_in": 32,
    "bucket2_out": 36,
    "bucket2_in": 40,
    "bucket3_out": 44,
    "bucket3_in": 48,
    "pass_out": 52,
    "pass_in": 56,
    "scratch_out": 60,
    "scratch_in": 64,
}

SEARCH_ZONES = {
    "logic": 0,
    "a_input": 10,
    "target_input": 40,
    "values_input": 70,
    "b_input": 100,
    "output": 120,
    "values_out": 1000,
    "values_in": 1010,
    "target_out": 1150,
    "target_in": 1160,
    "a_sum_out": 1300,
    "a_sum_in": 1310,
    "a_mask_out": 1450,
    "a_mask_in": 1460,
    "b_sum_out": 1600,
    "b_sum_in": 1610,
    "b_mask_out": 1750,
    "b_mask_in": 1760,
    "best_out": 1900,
    "best_in": 1910,
    "work_out": 2050,
    "work_in": 2060,
    "reverse_out": 2200,
    "reverse_in": 2210,
    "count_out": 2350,
    "count_in": 2360,
    "selected_out": 2500,
    "selected_in": 2510,
}

TEN = "5M+"
TWENTY = "5M+M+"
ONE_KIB = "2" + "M+" * 9
TWO_TO_31 = "1" + "M+" * 31

ENCODER_ZONES = {
    "logic": 0,
    "input": 8,
    "output": 16,
    "constant_out": 24,
    "constant_in": 32,
    "high_out": 40,
    "high_in": 48,
}

DECODER_ZONES = {
    "logic": 0,
    "input": 8,
    "output": 16,
    "constant_out": 24,
    "constant_in": 32,
    "aux_out": 40,
    "aux_in": 48,
}

MERGE_ZONES = {
    "logic": 0,
    "a_input": 4,
    "target_input": 12,
    "b_input": 20,
    "candidate_output": 0,
    "target_out": 80,
    "target_in": 84,
    "a_sum_out": 92,
    "a_sum_in": 96,
    "a_mask_out": 104,
    "a_mask_in": 108,
    "b_sum_out": 116,
    "b_sum_in": 120,
    "b_mask_out": 128,
    "b_mask_in": 132,
}

REDUCER_ZONES = {
    "logic": 0,
    "input": 10,
    "output": 20,
}

SELECTOR_ZONES = {
    "logic": 0,
    "values_input": 10,
    "mask_input": 40,
    "output": 70,
    "values_out": 800,
    "values_in": 810,
    "work_out": 1000,
    "work_in": 1010,
    "reverse_out": 1200,
    "reverse_in": 1210,
    "count_out": 1400,
    "count_in": 1410,
    "selected_out": 1600,
    "selected_in": 1610,
}


def reference_subset(values: list[int], target: int) -> list[int]:
    """Return the contest's lexicographically first subset."""
    count = len(values)
    for lex_mask in range((1 << count) - 1, -1, -1):
        chosen = [
            value
            for index, value in enumerate(values)
            if lex_mask & (1 << (count - 1 - index))
        ]
        if sum(chosen) == target:
            return chosen
    return []


def build_parser_fsm() -> Fsm:
    fsm = Fsm()
    fsm.go("start", "input", "@r" + "M1W-" * 10, "rem_store")
    fsm.go("rem_store", "rem_out", "s", "pad_init")
    fsm.go("pad_init", "logic", TEN, "pad_init_store")
    fsm.go("pad_init_store", "pad_out", "s", "a0_read")

    for index in range(10):
        read = f"a{index}_read"
        send_group = f"a{index}_group"
        send_values = f"a{index}_values"
        next_read = f"a{index + 1}_read" if index < 9 else "rem_read"
        fsm.go(read, "input", "r", send_group)
        fsm.go(send_group, "gen_a", "s", send_values)
        fsm.go(send_values, "values", "s", next_read)

    fsm.go("rem_read", "rem_in", "rb", "rem_restore")
    fsm.go("rem_restore", "rem_out", "s", "b_actual_check")
    fsm.bp(
        "b_actual_check",
        "logic",
        "",
        zero="target_read",
        positive="b_actual_read",
    )
    fsm.go("b_actual_read", "input", "r", "b_actual_group")
    fsm.go("b_actual_group", "gen_b", "s", "b_actual_values")
    fsm.go("b_actual_values", "values", "s", "b_actual_pad_read")
    fsm.go("b_actual_pad_read", "pad_in", "rM1W-", "b_actual_pad_store")
    fsm.go(
        "b_actual_pad_store",
        "pad_out",
        "s",
        "b_actual_decrement",
    )
    fsm.go("b_actual_decrement", "logic", "m", "b_actual_check")

    fsm.go("target_read", "input", "r", "target_send")
    fsm.go("target_send", "target", "s", "pad_count")
    fsm.go("pad_count", "pad_in", "rb", "pad_check")
    fsm.bp("pad_check", "logic", "", zero="halt", positive="pad_zero")
    fsm.go("pad_zero", "logic", "0", "pad_group")
    fsm.go("pad_group", "gen_b", "s", "pad_values")
    fsm.go("pad_values", "values", "s", "pad_decrement")
    fsm.go("pad_decrement", "logic", "m", "pad_check")
    fsm.go("halt", "logic", "H", "halt")
    return fsm


def _add_generator_bit(fsm: Fsm, index: int) -> None:
    prefix = f"bit{index}"
    next_target = f"bit{index + 1}_work" if index < 9 else "work_drop"
    fsm.go(f"{prefix}_work", "work_in", "rM2W/", f"{prefix}_work_store")
    fsm.go(f"{prefix}_work_store", "work_out", "s", f"{prefix}_test")
    fsm.sign(
        f"{prefix}_test",
        "logic",
        "W",
        negative=f"{prefix}_exclude_value",
        zero=f"{prefix}_exclude_value",
        positive=f"{prefix}_include_sum",
    )

    fsm.go(f"{prefix}_exclude_value", "value_in", "r", f"{prefix}_exclude_restore")
    fsm.go(
        f"{prefix}_exclude_restore",
        "value_out",
        "s",
        f"{prefix}_exclude_lex",
    )
    fsm.go(
        f"{prefix}_exclude_lex",
        "lex_in",
        "rM2W*",
        f"{prefix}_exclude_lex_store",
    )
    fsm.go(
        f"{prefix}_exclude_lex_store",
        "lex_out",
        "s",
        next_target,
    )

    fsm.go(f"{prefix}_include_sum", "sum_in", "rM", f"{prefix}_include_value")
    fsm.go(f"{prefix}_include_value", "value_in", "r", f"{prefix}_include_restore")
    fsm.go(
        f"{prefix}_include_restore",
        "value_out",
        "s+",
        f"{prefix}_include_sum_store",
    )
    fsm.go(
        f"{prefix}_include_sum_store",
        "sum_out",
        "s",
        f"{prefix}_include_lex",
    )
    fsm.go(
        f"{prefix}_include_lex",
        "lex_in",
        "rM2W*M1+",
        f"{prefix}_include_lex_store",
    )
    fsm.go(
        f"{prefix}_include_lex_store",
        "lex_out",
        "s",
        next_target,
    )


def build_generator_fsm() -> Fsm:
    fsm = Fsm()
    fsm.go("start", "logic", "@" + TEN + "b", "load_value")
    fsm.go("load_value", "input", "r", "load_value_store")
    fsm.go("load_value_store", "value_out", "s", "load_decrement")
    fsm.bp(
        "load_decrement",
        "logic",
        "m",
        zero="counter_zero",
        positive="load_value",
    )
    fsm.go("counter_zero", "logic", "0", "counter_init")
    fsm.go("counter_init", "counter_out", "s", "sum_zero")
    fsm.go("sum_zero", "logic", "0", "sum_init")
    fsm.go("sum_init", "sum_out", "s", "lex_zero")
    fsm.go("lex_zero", "logic", "0", "lex_init")
    fsm.go("lex_init", "lex_out", "s", "mask_count")
    fsm.go("mask_count", "logic", ONE_KIB + "b", "mask_read")

    fsm.go("mask_read", "counter_in", "r", "mask_counter_restore")
    fsm.go("mask_counter_restore", "counter_out", "s", "mask_work_store")
    fsm.go("mask_work_store", "work_out", "s", "bit0_work")

    for index in range(10):
        _add_generator_bit(fsm, index)

    fsm.go("work_drop", "work_in", "r", "sum_read")
    fsm.go("sum_read", "sum_in", "r", "sum_send")
    fsm.go("sum_send", "table", "s", "sum_reset")
    fsm.go("sum_reset", "logic", "0", "sum_reset_store")
    fsm.go("sum_reset_store", "sum_out", "s", "lex_read")
    fsm.go("lex_read", "lex_in", "r", "lex_send")
    fsm.go("lex_send", "table", "s", "lex_reset")
    fsm.go("lex_reset", "logic", "0", "lex_reset_store")
    fsm.go("lex_reset_store", "lex_out", "s", "mask_decrement")
    fsm.bp(
        "mask_decrement",
        "logic",
        "m",
        zero="counter_finish",
        positive="counter_next",
    )
    fsm.go("counter_next", "counter_in", "rM1+", "counter_next_store")
    fsm.go("counter_next_store", "counter_out", "s", "mask_read")
    fsm.go("counter_finish", "logic", "", "sentinel")
    fsm.go("sentinel", "logic", "1N", "sentinel_send")
    fsm.go("sentinel_send", "table", "s", "halt")
    fsm.go("halt", "logic", "H", "halt")
    return fsm


def build_counter_fsm() -> Fsm:
    fsm = Fsm()
    fsm.go("start", "logic", "@" + ONE_KIB + "M1W-", "counter_init")
    fsm.go("counter_init", "counter_out", "s", "mask_count")
    fsm.go("mask_count", "logic", ONE_KIB + "b", "counter_read")
    fsm.go("counter_read", "counter_in", "r", "counter_restore")
    fsm.go("counter_restore", "counter_out", "s", "mask_send")
    fsm.go("mask_send", "output", "Ms", "sum_zero")
    fsm.go("sum_zero", "logic", "0", "sum_send")
    fsm.go("sum_send", "output", "sW", "mask_copy_send")
    fsm.go("mask_copy_send", "output", "Ws", "counter_decrement")
    fsm.bp(
        "counter_decrement",
        "logic",
        "m",
        zero="sentinel",
        positive="counter_next",
    )
    fsm.go("counter_next", "counter_in", "rM1W-", "counter_next_store")
    fsm.go("counter_next_store", "counter_out", "s", "counter_read")
    fsm.go("sentinel", "logic", "1N", "sentinel_send")
    fsm.go("sentinel_send", "output", "s", "halt")
    fsm.go("halt", "logic", "H", "halt")
    return fsm


def build_bit_stage_fsm(index: int, *, first: bool, last: bool) -> Fsm:
    if not 0 <= index < 10:
        raise ValueError(f"invalid subset stage index: {index}")
    fsm = Fsm()
    init_zone = "init" if first else "stream_in"
    for position in range(10):
        read = f"init{position}_read"
        after_read = f"init{position}_after"
        next_read = f"init{position + 1}_read" if position < 9 else "packet_read"
        fsm.go(read, init_zone, ("@" if position == 0 else "") + "r", after_read)
        if last:
            if position == index:
                fsm.go(after_read, "value_out", "s", next_read)
            else:
                fsm.go(after_read, "logic", "", next_read)
        elif position == index:
            fsm.go(after_read, "stream_out", "s", f"init{position}_store")
            fsm.go(f"init{position}_store", "value_out", "s", next_read)
        else:
            fsm.go(after_read, "stream_out", "s", next_read)

    packet_zone = "stream_in"
    fsm.sign(
        "packet_read",
        packet_zone,
        "r",
        negative="sentinel_send",
        zero="key_divide",
        positive="key_divide",
    )
    fsm.go("key_divide", "logic", "M2W/", "key_ready")
    if last:
        fsm.go("key_ready", "logic", "W", "bit_test")
    else:
        fsm.go("key_ready", "stream_out", "sW", "bit_test")
    fsm.sign(
        "bit_test",
        "logic",
        "",
        negative="zero_sum",
        zero="zero_sum",
        positive="one_sum",
    )

    fsm.go("zero_sum", packet_zone, "r", "zero_sum_send")
    fsm.go("zero_sum_send", "stream_out", "s", "zero_lex")
    fsm.go("zero_lex", packet_zone, "rM2W*", "zero_lex_send")
    fsm.go("zero_lex_send", "stream_out", "s", "packet_read")

    fsm.go("one_sum", packet_zone, "rM", "one_value")
    fsm.sign(
        "one_value",
        "value_in",
        "r",
        negative="one_value_restore",
        zero="padded_value_restore",
        positive="one_value_restore",
    )
    fsm.go("one_value_restore", "value_out", "s+", "one_sum_send")
    fsm.go("one_sum_send", "stream_out", "s", "one_lex")
    fsm.go("one_lex", packet_zone, "rM2W*M1+", "one_lex_send")
    fsm.go("one_lex_send", "stream_out", "s", "packet_read")

    fsm.go("padded_value_restore", "value_out", "sW", "padded_sum_send")
    fsm.go("padded_sum_send", "stream_out", "s", "padded_lex")
    fsm.go(
        "padded_lex",
        packet_zone,
        "rM2W*",
        "padded_lex_send",
    )
    fsm.go("padded_lex_send", "stream_out", "s", "packet_read")

    fsm.go("sentinel_send", "stream_out", "s", "halt")
    fsm.go("halt", "logic", "H", "halt")
    return fsm


def _power_of_two_code(value: int) -> str:
    exponent = value.bit_length() - 1
    if value <= 0 or value != 1 << exponent:
        raise ValueError("systolic sorter size must be a positive power of two")
    return "1" if exponent == 0 else "2" + "M+" * (exponent - 1)


def build_systolic_encoder_fsm(*, descending: bool, count: int = 1024) -> Fsm:
    """Encode pairs into ascending scalar keys and append flush/reset tokens."""

    count_code = _power_of_two_code(count)
    fsm = Fsm()
    if descending:
        # key = 2^31 - (sum * 1024 + mask)
        fsm.go("start", "logic", "@" + TWO_TO_31, "constant_store")
        fsm.go("constant_store", "constant_out", "s", "count_init")
    else:
        # key = sum * 1024 + (1023 - mask)
        fsm.go(
            "start",
            "logic",
            "@" + ONE_KIB + "M1W-",
            "constant_store",
        )
        fsm.go("constant_store", "constant_out", "s", "high_init")
        fsm.go("high_init", "logic", TWO_TO_31, "high_store")
        fsm.go("high_store", "high_out", "s", "count_init")

    fsm.go("count_init", "logic", count_code + "b", "sum_read")
    fsm.go("sum_read", "input", "r" + "M+" * 10 + "M", "mask_read")
    if descending:
        fsm.go("mask_read", "input", "r+", "combined_store")
    else:
        fsm.go("mask_read", "input", "rN+", "combined_store")
    fsm.go("combined_store", "logic", "M", "constant_read")
    fsm.go("constant_read", "constant_in", "r", "constant_restore")
    fsm.go(
        "constant_restore",
        "constant_out",
        "s-" if descending else "s+",
        "key_send",
    )
    fsm.go("key_send", "output", "s", "entry_decrement")
    fsm.bp(
        "entry_decrement",
        "logic",
        "m",
        zero="input_sentinel",
        positive="sum_read",
    )

    fsm.go("input_sentinel", "input", "r", "flush_count")
    fsm.go("flush_count", "logic", count_code + "b", "high_read")
    high_in = "constant_in" if descending else "high_in"
    high_out = "constant_out" if descending else "high_out"
    fsm.go("high_read", high_in, "rM1+", "high_restore")
    fsm.go("high_restore", high_out, "WsW", "flush_send")
    fsm.go("flush_send", "output", "s", "flush_decrement")
    fsm.bp(
        "flush_decrement",
        "logic",
        "m",
        zero="reset_value",
        positive="flush_send",
    )
    fsm.go("reset_value", "logic", "1N", "reset_send")
    fsm.go("reset_send", "output", "s", "halt")
    fsm.go("halt", "logic", "H", "halt")
    return fsm


def build_systolic_decoder_fsm(*, descending: bool, count: int = 1024) -> Fsm:
    """Drop warm-up tokens, decode sorted keys, and restore pair framing."""

    count_code = _power_of_two_code(count)
    fsm = Fsm()
    if descending:
        fsm.go("start", "logic", "@" + TWO_TO_31, "constant_store")
        fsm.go("constant_store", "constant_out", "s", "aux_init")
        fsm.go("aux_init", "logic", ONE_KIB, "aux_store")
    else:
        fsm.go("start", "logic", "@" + ONE_KIB, "constant_store")
        fsm.go("constant_store", "constant_out", "s", "aux_init")
        fsm.go("aux_init", "logic", ONE_KIB + "M1W-", "aux_store")
    fsm.go("aux_store", "aux_out", "s", "warmup_count")

    fsm.go("warmup_count", "logic", count_code + "b", "warmup_read")
    fsm.go("warmup_read", "input", "r", "warmup_decrement")
    fsm.bp(
        "warmup_decrement",
        "logic",
        "m",
        zero="entry_count",
        positive="warmup_read",
    )
    fsm.go("entry_count", "logic", count_code + "b", "key_read")

    if descending:
        fsm.go("key_read", "input", "rM", "constant_read")
        fsm.go("constant_read", "constant_in", "r", "constant_restore")
        fsm.go("constant_restore", "constant_out", "s-", "combined_store")
        fsm.go("combined_store", "logic", "M", "divisor_read")
        fsm.go("divisor_read", "aux_in", "r", "divisor_restore")
        fsm.go("divisor_restore", "aux_out", "sW/", "sum_send")
        fsm.go("sum_send", "output", "sW", "mask_send")
    else:
        fsm.go("key_read", "input", "rM", "divisor_read")
        fsm.go("divisor_read", "constant_in", "r", "divisor_restore")
        fsm.go("divisor_restore", "constant_out", "sW/", "sum_send")
        fsm.go("sum_send", "output", "sW", "remainder_store")
        fsm.go("remainder_store", "logic", "M", "mask_constant_read")
        fsm.go("mask_constant_read", "aux_in", "r", "mask_constant_restore")
        fsm.go("mask_constant_restore", "aux_out", "s-", "mask_send")

    fsm.go("mask_send", "output", "s", "entry_decrement")
    fsm.bp(
        "entry_decrement",
        "logic",
        "m",
        zero="reset_read",
        positive="key_read",
    )
    fsm.go("reset_read", "input", "r", "sentinel_send")
    fsm.go("sentinel_send", "output", "s", "halt")
    fsm.go("halt", "logic", "H", "halt")
    return fsm


def _add_radix_phase(
    fsm: Fsm,
    prefix: str,
    *,
    first_buffer: str,
    finish_target: str,
) -> None:
    second_buffer = "zero" if first_buffer == "one" else "one"
    fsm.go(
        f"{prefix}_pass_start",
        "logic",
        ONE_KIB + "b",
        f"{prefix}_key_read",
    )
    fsm.go(
        f"{prefix}_key_read",
        "main_in",
        "rM2W/",
        f"{prefix}_key_test",
    )
    fsm.sign(
        f"{prefix}_key_test",
        "logic",
        "W",
        negative=f"{prefix}_zero_key",
        zero=f"{prefix}_zero_key",
        positive=f"{prefix}_one_key",
    )
    for buffer_name in ("zero", "one"):
        key = f"{prefix}_{buffer_name}_key"
        fsm.go(key, "logic", "W", f"{prefix}_{buffer_name}_key_send")
        fsm.go(
            f"{prefix}_{buffer_name}_key_send",
            f"{buffer_name}_out",
            "s",
            f"{prefix}_{buffer_name}_sum",
        )
        fsm.go(
            f"{prefix}_{buffer_name}_sum",
            "main_in",
            "r",
            f"{prefix}_{buffer_name}_sum_send",
        )
        fsm.go(
            f"{prefix}_{buffer_name}_sum_send",
            f"{buffer_name}_out",
            "s",
            f"{prefix}_{buffer_name}_mask",
        )
        fsm.go(
            f"{prefix}_{buffer_name}_mask",
            "main_in",
            "r",
            f"{prefix}_{buffer_name}_mask_send",
        )
        fsm.go(
            f"{prefix}_{buffer_name}_mask_send",
            f"{buffer_name}_out",
            "s",
            f"{prefix}_entry_decrement",
        )
    fsm.bp(
        f"{prefix}_entry_decrement",
        "logic",
        "m",
        zero=f"{prefix}_zero_sentinel",
        positive=f"{prefix}_key_read",
    )
    fsm.go(f"{prefix}_zero_sentinel", "logic", "1N", f"{prefix}_zero_mark")
    fsm.go(
        f"{prefix}_zero_mark",
        "zero_out",
        "s",
        f"{prefix}_one_sentinel",
    )
    fsm.go(f"{prefix}_one_sentinel", "logic", "1N", f"{prefix}_one_mark")
    fsm.go(
        f"{prefix}_one_mark",
        "one_out",
        "s",
        f"{prefix}_{first_buffer}_drain",
    )

    for buffer_name, next_target in (
        (first_buffer, f"{prefix}_{second_buffer}_drain"),
        (second_buffer, f"{prefix}_pass_decrement"),
    ):
        fsm.sign(
            f"{prefix}_{buffer_name}_drain",
            f"{buffer_name}_in",
            "r",
            negative=next_target,
            zero=f"{prefix}_{buffer_name}_restore",
            positive=f"{prefix}_{buffer_name}_restore",
        )
        fsm.go(
            f"{prefix}_{buffer_name}_restore",
            "main_out",
            "s",
            f"{prefix}_{buffer_name}_drain",
        )

    fsm.go(f"{prefix}_pass_decrement", "pass_in", "rM1W-", f"{prefix}_pass_check")
    fsm.sign(
        f"{prefix}_pass_check",
        "logic",
        "",
        negative=finish_target,
        zero=finish_target,
        positive=f"{prefix}_pass_store",
    )
    fsm.go(
        f"{prefix}_pass_store",
        "pass_out",
        "s",
        f"{prefix}_pass_start",
    )


def build_sorter_fsm(*, descending: bool) -> Fsm:
    fsm = Fsm()
    fsm.go("start", "logic", "@" + ONE_KIB + "b", "load_sum")
    fsm.go("load_sum", "input", "rM", "load_mask")
    fsm.go("load_mask", "input", "r", "load_key_send")
    fsm.go("load_key_send", "main_out", "Ws", "load_sum_send")
    fsm.go("load_sum_send", "main_out", "sW", "load_mask_send")
    fsm.go("load_mask_send", "main_out", "s", "load_decrement")
    fsm.bp(
        "load_decrement",
        "logic",
        "m",
        zero="input_sentinel",
        positive="load_sum",
    )
    fsm.go("input_sentinel", "input", "r", "primary_count")
    fsm.go("primary_count", "logic", TWENTY, "primary_count_store")
    fsm.go("primary_count_store", "pass_out", "s", "primary_pass_start")

    _add_radix_phase(
        fsm,
        "primary",
        first_buffer="one" if descending else "zero",
        finish_target="output_start",
    )

    fsm.go("output_start", "logic", ONE_KIB + "b", "output_key_drop")
    fsm.go("output_key_drop", "main_in", "r", "output_sum")
    fsm.go("output_sum", "main_in", "r", "output_sum_send")
    fsm.go("output_sum_send", "output", "s", "output_mask")
    fsm.go("output_mask", "main_in", "r", "output_mask_send")
    fsm.go("output_mask_send", "output", "s", "output_decrement")
    fsm.bp(
        "output_decrement",
        "logic",
        "m",
        zero="output_sentinel",
        positive="output_key_drop",
    )
    fsm.go("output_sentinel", "logic", "1N", "output_sentinel_send")
    fsm.go("output_sentinel_send", "output", "s", "halt")
    fsm.go("halt", "logic", "H", "halt")
    return fsm


def build_sorter_base4_fsm(*, descending: bool) -> Fsm:
    fsm = Fsm()
    fsm.go("start", "logic", "@" + ONE_KIB + "b", "load_sum")
    fsm.go("load_sum", "input", "rM", "load_mask")
    fsm.go("load_mask", "input", "r", "load_key_send")
    fsm.go("load_key_send", "main_out", "Ws", "load_sum_send")
    fsm.go("load_sum_send", "main_out", "sW", "load_mask_send")
    fsm.go("load_mask_send", "main_out", "s", "load_decrement")
    fsm.bp(
        "load_decrement",
        "logic",
        "m",
        zero="input_sentinel",
        positive="load_sum",
    )
    fsm.go("input_sentinel", "input", "r", "pass_count")
    fsm.go("pass_count", "logic", TEN, "pass_count_store")
    fsm.go("pass_count_store", "pass_out", "s", "pass_start")

    fsm.go("pass_start", "logic", ONE_KIB + "b", "key_read")
    fsm.go("key_read", "main_in", "rM4W/", "quotient_store")
    fsm.go("quotient_store", "scratch_out", "sW", "dispatch0")
    fsm.sign(
        "dispatch0",
        "logic",
        "",
        negative="bucket0_key",
        zero="bucket0_key",
        positive="dispatch1",
    )
    fsm.sign(
        "dispatch1",
        "logic",
        "M1W-",
        negative="bucket0_key",
        zero="bucket1_key",
        positive="dispatch2",
    )
    fsm.sign(
        "dispatch2",
        "logic",
        "M1W-",
        negative="bucket1_key",
        zero="bucket2_key",
        positive="bucket3_key",
    )

    for bucket in range(4):
        prefix = f"bucket{bucket}"
        fsm.go(f"{prefix}_key", "scratch_in", "r", f"{prefix}_key_send")
        fsm.go(
            f"{prefix}_key_send",
            f"bucket{bucket}_out",
            "s",
            f"{prefix}_sum",
        )
        fsm.go(f"{prefix}_sum", "main_in", "r", f"{prefix}_sum_send")
        fsm.go(
            f"{prefix}_sum_send",
            f"bucket{bucket}_out",
            "s",
            f"{prefix}_mask",
        )
        fsm.go(f"{prefix}_mask", "main_in", "r", f"{prefix}_mask_send")
        fsm.go(
            f"{prefix}_mask_send",
            f"bucket{bucket}_out",
            "s",
            "entry_decrement",
        )

    fsm.bp(
        "entry_decrement",
        "logic",
        "m",
        zero="sentinel0_value",
        positive="key_read",
    )
    for bucket in range(4):
        next_target = (
            f"sentinel{bucket + 1}_value"
            if bucket < 3
            else f"drain{3 if descending else 0}"
        )
        fsm.go(f"sentinel{bucket}_value", "logic", "1N", f"sentinel{bucket}_send")
        fsm.go(
            f"sentinel{bucket}_send",
            f"bucket{bucket}_out",
            "s",
            next_target,
        )

    order = range(3, -1, -1) if descending else range(4)
    ordered_buckets = list(order)
    for order_index, bucket in enumerate(ordered_buckets):
        next_target = (
            f"drain{ordered_buckets[order_index + 1]}"
            if order_index + 1 < len(ordered_buckets)
            else "pass_decrement"
        )
        fsm.sign(
            f"drain{bucket}",
            f"bucket{bucket}_in",
            "r",
            negative=next_target,
            zero=f"drain{bucket}_restore",
            positive=f"drain{bucket}_restore",
        )
        fsm.go(
            f"drain{bucket}_restore",
            "main_out",
            "s",
            f"drain{bucket}",
        )

    fsm.go("pass_decrement", "pass_in", "rM1W-", "pass_check")
    fsm.sign(
        "pass_check",
        "logic",
        "",
        negative="output_start",
        zero="output_start",
        positive="pass_store",
    )
    fsm.go("pass_store", "pass_out", "s", "pass_start")

    fsm.go("output_start", "logic", ONE_KIB + "b", "output_key_drop")
    fsm.go("output_key_drop", "main_in", "r", "output_sum")
    fsm.go("output_sum", "main_in", "r", "output_sum_send")
    fsm.go("output_sum_send", "output", "s", "output_mask")
    fsm.go("output_mask", "main_in", "r", "output_mask_send")
    fsm.go("output_mask_send", "output", "s", "output_decrement")
    fsm.bp(
        "output_decrement",
        "logic",
        "m",
        zero="output_sentinel",
        positive="output_key_drop",
    )
    fsm.go("output_sentinel", "logic", "1N", "output_sentinel_send")
    fsm.go("output_sentinel_send", "output", "s", "halt")
    fsm.go("halt", "logic", "H", "halt")
    return fsm


def _add_reverse_bit(fsm: Fsm, index: int) -> None:
    prefix = f"reverse{index}"
    next_target = f"reverse{index + 1}_work" if index < 19 else "reverse_work_drop"
    fsm.go(f"{prefix}_work", "work_in", "rM2W/", f"{prefix}_work_store")
    fsm.go(f"{prefix}_work_store", "work_out", "s", f"{prefix}_test")
    fsm.sign(
        f"{prefix}_test",
        "logic",
        "W",
        negative=f"{prefix}_zero",
        zero=f"{prefix}_zero",
        positive=f"{prefix}_one",
    )
    fsm.go(f"{prefix}_zero", "reverse_in", "rM2W*", f"{prefix}_store")
    fsm.go(f"{prefix}_one", "reverse_in", "rM2W*M1+", f"{prefix}_store")
    fsm.go(f"{prefix}_store", "reverse_out", "s", next_target)


def _add_selection_bit(fsm: Fsm, index: int) -> None:
    prefix = f"select{index}"
    next_target = f"select{index + 1}_work" if index < 19 else "select_work_drop"
    fsm.go(f"{prefix}_work", "work_in", "rM2W/", f"{prefix}_work_store")
    fsm.go(f"{prefix}_work_store", "work_out", "s", f"{prefix}_test")
    fsm.sign(
        f"{prefix}_test",
        "logic",
        "W",
        negative=f"{prefix}_skip",
        zero=f"{prefix}_skip",
        positive=f"{prefix}_take",
    )
    fsm.go(f"{prefix}_skip", "values_in", "r", next_target)
    fsm.go(f"{prefix}_take", "values_in", "r", f"{prefix}_selected")
    fsm.go(
        f"{prefix}_selected",
        "selected_out",
        "s",
        f"{prefix}_count_read",
    )
    fsm.go(f"{prefix}_count_read", "count_in", "rM1+", f"{prefix}_count_store")
    fsm.go(f"{prefix}_count_store", "count_out", "s", next_target)


def build_merge_fsm() -> Fsm:
    """Two-pointer merge over sorted half-subset streams."""

    fsm = Fsm()
    fsm.go("start", "target_input", "@r", "target_store")
    fsm.go("target_store", "target_out", "s", "a_initial")
    fsm.sign(
        "a_initial",
        "a_input",
        "r",
        negative="finish",
        zero="a_initial_store",
        positive="a_initial_store",
    )
    fsm.go("a_initial_store", "a_sum_out", "s", "a_initial_mask")
    fsm.go("a_initial_mask", "a_input", "r", "a_initial_mask_store")
    fsm.go("a_initial_mask_store", "a_mask_out", "s", "b_initial")
    fsm.sign(
        "b_initial",
        "b_input",
        "r",
        negative="finish",
        zero="b_initial_store",
        positive="b_initial_store",
    )
    fsm.go("b_initial_store", "b_sum_out", "s", "b_initial_mask")
    fsm.go("b_initial_mask", "b_input", "r", "b_initial_mask_store")
    fsm.go("b_initial_mask_store", "b_mask_out", "s", "compare_a")

    fsm.go("compare_a", "a_sum_in", "rsM", "compare_b")
    fsm.go("compare_b", "b_sum_in", "rs+", "compare_total")
    fsm.go("compare_total", "logic", "M", "compare_target")
    fsm.go("compare_target", "target_in", "rsW-", "compare_sign")
    fsm.sign(
        "compare_sign",
        "logic",
        "",
        negative="advance_b_drop_sum",
        zero="candidate_a",
        positive="advance_a_drop_sum",
    )

    fsm.go("advance_a_drop_sum", "a_sum_in", "r", "advance_a_drop_mask")
    fsm.go("advance_a_drop_mask", "a_mask_in", "r", "advance_a")
    fsm.sign(
        "advance_a",
        "a_input",
        "r",
        negative="finish",
        zero="advance_a_store",
        positive="advance_a_store",
    )
    fsm.go("advance_a_store", "a_sum_out", "s", "advance_a_mask")
    fsm.go("advance_a_mask", "a_input", "r", "advance_a_mask_store")
    fsm.go("advance_a_mask_store", "a_mask_out", "s", "compare_a")

    fsm.go("advance_b_drop_sum", "b_sum_in", "r", "advance_b_drop_mask")
    fsm.go("advance_b_drop_mask", "b_mask_in", "r", "advance_b")
    fsm.sign(
        "advance_b",
        "b_input",
        "r",
        negative="finish",
        zero="advance_b_store",
        positive="advance_b_store",
    )
    fsm.go("advance_b_store", "b_sum_out", "s", "advance_b_mask")
    fsm.go("advance_b_mask", "b_input", "r", "advance_b_mask_store")
    fsm.go("advance_b_mask_store", "b_mask_out", "s", "compare_a")

    fsm.go("candidate_a", "a_mask_in", "rs" + "M+" * 10 + "M", "candidate_b")
    fsm.go("candidate_b", "b_mask_in", "rs+", "candidate_send")
    fsm.go(
        "candidate_send",
        "candidate_output",
        "s",
        "advance_a_drop_sum",
    )

    fsm.go("finish", "logic", "1N", "finish_send")
    fsm.go("finish_send", "candidate_output", "s", "halt")
    fsm.go("halt", "logic", "H", "halt")
    return fsm


def build_candidate_reducer_fsm() -> Fsm:
    """Return the largest candidate mask, or -1 when none was produced."""

    fsm = Fsm()
    fsm.go("start", "logic", "@1NM", "read")
    fsm.sign(
        "read",
        "input",
        "r",
        negative="finish",
        zero="compare",
        positive="compare",
    )
    fsm.sign(
        "compare",
        "logic",
        "-",
        negative="read",
        zero="read",
        positive="update",
    )
    fsm.go("update", "logic", "+M", "read")
    fsm.go("finish", "logic", "W", "send")
    fsm.go("send", "output", "s", "halt")
    fsm.go("halt", "logic", "H", "halt")
    return fsm


def build_selector_fsm() -> Fsm:
    """Format the selected values after the merge has chosen a mask."""

    fsm = Fsm()
    fsm.go("start", "logic", "@" + TWENTY + "b", "value_read")
    fsm.go("value_read", "values_input", "r", "value_store")
    fsm.go("value_store", "values_out", "s", "value_decrement")
    fsm.bp(
        "value_decrement",
        "logic",
        "m",
        zero="mask_read",
        positive="value_read",
    )
    fsm.sign(
        "mask_read",
        "mask_input",
        "r",
        negative="no_solution",
        zero="solution_work_store",
        positive="solution_work_store",
    )
    fsm.go("no_solution", "logic", "0", "no_solution_send")
    fsm.go("no_solution_send", "output", "s", "halt")

    fsm.go("solution_work_store", "work_out", "s", "reverse_zero")
    fsm.go("reverse_zero", "logic", "0", "reverse_zero_store")
    fsm.go("reverse_zero_store", "reverse_out", "s", "reverse0_work")
    for index in range(20):
        _add_reverse_bit(fsm, index)
    fsm.go("reverse_work_drop", "work_in", "r", "reverse_read")
    fsm.go("reverse_read", "reverse_in", "r", "selection_work_store")
    fsm.go("selection_work_store", "work_out", "s", "count_zero")
    fsm.go("count_zero", "logic", "0", "count_zero_store")
    fsm.go("count_zero_store", "count_out", "s", "select0_work")
    for index in range(20):
        _add_selection_bit(fsm, index)
    fsm.go("select_work_drop", "work_in", "r", "count_read")
    fsm.go("count_read", "count_in", "rb", "count_send")
    fsm.go("count_send", "output", "s", "selected_check")
    fsm.bp(
        "selected_check",
        "logic",
        "",
        zero="halt",
        positive="selected_read",
    )
    fsm.go("selected_read", "selected_in", "r", "selected_send")
    fsm.go("selected_send", "output", "s", "selected_decrement")
    fsm.go("selected_decrement", "logic", "m", "selected_check")
    fsm.go("halt", "logic", "H", "halt")
    return fsm


def build_search_fsm() -> Fsm:
    fsm = Fsm()
    fsm.go("start", "target_input", "@r", "target_store")
    fsm.go("target_store", "target_out", "s", "values_count")
    fsm.go("values_count", "logic", TWENTY + "b", "value_read")
    fsm.go("value_read", "values_input", "r", "value_store")
    fsm.go("value_store", "values_out", "s", "value_decrement")
    fsm.bp(
        "value_decrement",
        "logic",
        "m",
        zero="best_init",
        positive="value_read",
    )
    fsm.go("best_init", "logic", "1N", "best_init_store")
    fsm.go("best_init_store", "best_out", "s", "a_initial")

    fsm.sign(
        "a_initial",
        "a_input",
        "r",
        negative="finish",
        zero="a_initial_store",
        positive="a_initial_store",
    )
    fsm.go("a_initial_store", "a_sum_out", "s", "a_initial_mask")
    fsm.go("a_initial_mask", "a_input", "r", "a_initial_mask_store")
    fsm.go("a_initial_mask_store", "a_mask_out", "s", "b_initial")
    fsm.sign(
        "b_initial",
        "b_input",
        "r",
        negative="finish",
        zero="b_initial_store",
        positive="b_initial_store",
    )
    fsm.go("b_initial_store", "b_sum_out", "s", "b_initial_mask")
    fsm.go("b_initial_mask", "b_input", "r", "b_initial_mask_store")
    fsm.go("b_initial_mask_store", "b_mask_out", "s", "compare_a")

    fsm.go("compare_a", "a_sum_in", "rsM", "compare_b")
    fsm.go("compare_b", "b_sum_in", "rs+", "compare_total")
    fsm.go("compare_total", "logic", "M", "compare_target")
    fsm.go("compare_target", "target_in", "rsW-", "compare_sign")
    fsm.sign(
        "compare_sign",
        "logic",
        "",
        negative="advance_b",
        zero="candidate_a",
        positive="advance_a",
    )

    fsm.sign(
        "advance_a",
        "a_input",
        "r",
        negative="finish",
        zero="advance_a_store",
        positive="advance_a_store",
    )
    fsm.go("advance_a_store", "a_sum_out", "s", "advance_a_mask")
    fsm.go("advance_a_mask", "a_input", "r", "advance_a_mask_store")
    fsm.go("advance_a_mask_store", "a_mask_out", "s", "compare_a")

    fsm.sign(
        "advance_b",
        "b_input",
        "r",
        negative="finish",
        zero="advance_b_store",
        positive="advance_b_store",
    )
    fsm.go("advance_b_store", "b_sum_out", "s", "advance_b_mask")
    fsm.go("advance_b_mask", "b_input", "r", "advance_b_mask_store")
    fsm.go("advance_b_mask_store", "b_mask_out", "s", "compare_a")

    fsm.go("candidate_a", "a_mask_in", "rs" + "M+" * 10, "candidate_b")
    fsm.go("candidate_b", "b_mask_in", "rs+", "candidate_copy_one")
    fsm.go("candidate_copy_one", "work_out", "s", "candidate_copy_two")
    fsm.go("candidate_copy_two", "work_out", "s", "candidate_best")
    fsm.go("candidate_best", "best_in", "rM", "candidate_compare")
    fsm.go("candidate_compare", "work_in", "r-", "candidate_sign")
    fsm.sign(
        "candidate_sign",
        "logic",
        "",
        negative="candidate_keep_drop",
        zero="candidate_keep_drop",
        positive="candidate_update",
    )
    fsm.go("candidate_keep_drop", "work_in", "rW", "candidate_keep")
    fsm.go("candidate_keep", "best_out", "s", "advance_a")
    fsm.go("candidate_update", "work_in", "r", "candidate_update_store")
    fsm.go("candidate_update_store", "best_out", "s", "advance_a")

    fsm.go("finish", "best_in", "r", "finish_check")
    fsm.sign(
        "finish_check",
        "logic",
        "",
        negative="no_solution",
        zero="solution_work_store",
        positive="solution_work_store",
    )
    fsm.go("no_solution", "logic", "0", "no_solution_send")
    fsm.go("no_solution_send", "output", "s", "halt")

    fsm.go("solution_work_store", "work_out", "s", "reverse_zero")
    fsm.go("reverse_zero", "logic", "0", "reverse_zero_store")
    fsm.go("reverse_zero_store", "reverse_out", "s", "reverse0_work")
    for index in range(20):
        _add_reverse_bit(fsm, index)
    fsm.go("reverse_work_drop", "work_in", "r", "reverse_read")
    fsm.go("reverse_read", "reverse_in", "r", "selection_work_store")
    fsm.go("selection_work_store", "work_out", "s", "count_zero")
    fsm.go("count_zero", "logic", "0", "count_zero_store")
    fsm.go("count_zero_store", "count_out", "s", "select0_work")
    for index in range(20):
        _add_selection_bit(fsm, index)
    fsm.go("select_work_drop", "work_in", "r", "count_read")
    fsm.go("count_read", "count_in", "rb", "count_send")
    fsm.go("count_send", "output", "s", "selected_check")
    fsm.bp(
        "selected_check",
        "logic",
        "",
        zero="halt",
        positive="selected_read",
    )
    fsm.go("selected_read", "selected_in", "r", "selected_send")
    fsm.go("selected_send", "output", "s", "selected_decrement")
    fsm.go("selected_decrement", "logic", "m", "selected_check")
    fsm.go("halt", "logic", "H", "halt")
    return fsm


@dataclass(frozen=True)
class PlacedRoom:
    top: int
    left: int
    room: CompiledRoom
    next_top: int


@dataclass(frozen=True)
class GroupPipeline:
    first_stage: PlacedRoom
    last_stage: PlacedRoom
    next_top: int


@dataclass(frozen=True)
class PlacedSystolicSorter:
    input_top: int
    input_x: int
    output_bottom: int
    output_x: int
    next_top: int


def _place_with_rings(
    canvas: Canvas,
    *,
    top: int,
    left: int,
    room: CompiledRoom,
    rings: list[tuple[str, str]],
    extension: int,
) -> PlacedRoom:
    canvas.put(top, left, room.rows)
    room_bottom = top + room.height + 1
    relay_left = left + room.width + extension
    ordered = sorted(
        rings,
        key=lambda pair: room.zones[pair[1]],
        reverse=True,
    )
    for index, (in_zone, out_zone) in enumerate(ordered):
        relay_top = room_bottom + 7 + index * 8
        canvas.put(relay_top, relay_left, RELAY)
        out_x = left + room.zones[out_zone]
        in_x = left + room.zones[in_zone]
        canvas.pipe(
            [
                (room_bottom + 1, out_x),
                (relay_top + 3, out_x),
                (relay_top + 3, relay_left - 1),
            ]
        )
        canvas.pipe(
            [
                (relay_top + 2, relay_left - 1),
                (relay_top + 2, in_x),
                (room_bottom + 1, in_x),
            ]
        )
    next_top = room_bottom + 12 if not rings else room_bottom + 7 + len(rings) * 8 + 10
    return PlacedRoom(top=top, left=left, room=room, next_top=next_top)


def _place_systolic_sorter(
    canvas: Canvas,
    *,
    top: int,
    left: int,
    descending: bool,
    count: int = 1024,
) -> PlacedSystolicSorter:
    """Place a square serpentine insertion pipeline for encoded scalar keys."""

    side = isqrt(count)
    if side * side != count or side % 2:
        raise ValueError("sorter count must be an even perfect square")

    encoder = compile_fsm(
        build_systolic_encoder_fsm(descending=descending, count=count),
        ENCODER_ZONES,
    )
    decoder = compile_fsm(
        build_systolic_decoder_fsm(descending=descending, count=count),
        DECODER_ZONES,
    )
    encoder_rings = [("constant_in", "constant_out")]
    if not descending:
        encoder_rings.append(("high_in", "high_out"))
    encoder_placed = _place_with_rings(
        canvas,
        top=top,
        left=left,
        room=encoder,
        rings=encoder_rings,
        extension=80,
    )

    decoder_left = left + 360
    decoder_placed = _place_with_rings(
        canvas,
        top=top,
        left=decoder_left,
        room=decoder,
        rings=[
            ("constant_in", "constant_out"),
            ("aux_in", "aux_out"),
        ],
        extension=80,
    )

    stage_rows = build_sort_stage()
    stage_height = len(stage_rows)
    stage_width = max(map(len, stage_rows))
    row_pitch = stage_height + 2
    col_pitch = stage_width + 2
    array_top = max(encoder_placed.next_top, decoder_placed.next_top) + 16

    origins: list[tuple[int, int]] = []
    for index in range(count):
        column, offset = divmod(index, side)
        row = offset if column % 2 == 0 else side - 1 - offset
        origin = (
            array_top + row * row_pitch,
            left + column * col_pitch,
        )
        origins.append(origin)
        canvas.put(*origin, stage_rows)

    encoder_bottom = encoder_placed.top + encoder.height + 1
    encoder_output_x = left + encoder.zones["output"]
    first_top, first_left = origins[0]
    canvas.pipe(
        [
            (encoder_bottom + 1, encoder_output_x),
            (first_top - 3, encoder_output_x),
            (first_top - 3, first_left + 6),
            (first_top - 1, first_left + 6),
        ]
    )

    for (source_top, source_left), (dest_top, dest_left) in pairwise(origins):
        if source_left == dest_left and dest_top > source_top:
            canvas.pipe(
                [
                    (source_top + stage_height, source_left + 4),
                    (dest_top - 1, dest_left + 4),
                ]
            )
        elif source_left == dest_left:
            canvas.pipe(
                [
                    (source_top - 1, source_left + 4),
                    (dest_top + stage_height, dest_left + 4),
                ]
            )
        else:
            canvas.pipe(
                [
                    (source_top + 4, source_left + stage_width),
                    (dest_top + 4, dest_left - 1),
                ]
            )

    final_top, final_left = origins[-1]
    decoder_bottom = decoder_placed.top + decoder.height + 1
    decoder_input_x = decoder_left + decoder.zones["input"]
    transfer_x = decoder_input_x - 20
    canvas.pipe(
        [
            (final_top - 1, final_left + 4),
            (final_top - 3, final_left + 4),
            (final_top - 3, transfer_x),
            (decoder_bottom + 3, transfer_x),
            (decoder_bottom + 3, decoder_input_x),
            (decoder_bottom + 1, decoder_input_x),
        ]
    )

    array_bottom = array_top + (side - 1) * row_pitch + stage_height - 1
    return PlacedSystolicSorter(
        input_top=top,
        input_x=left + encoder.zones["input"],
        output_bottom=decoder_bottom,
        output_x=decoder_left + decoder.zones["output"],
        next_top=array_bottom + 20,
    )


def _place_group_pipeline(
    canvas: Canvas,
    *,
    top: int,
    left: int,
    counter_left: int,
    counter: CompiledRoom,
    stages: list[CompiledRoom],
) -> GroupPipeline:
    counter_placed = _place_with_rings(
        canvas,
        top=top,
        left=counter_left,
        room=counter,
        rings=[("counter_in", "counter_out")],
        extension=100,
    )
    stage_top = counter_placed.next_top + 16
    placed_stages = []
    for stage in stages:
        placed = _place_with_rings(
            canvas,
            top=stage_top,
            left=left,
            room=stage,
            rings=[("value_in", "value_out")],
            extension=100,
        )
        placed_stages.append(placed)
        stage_top = placed.next_top + 12

    first_stage = placed_stages[0]
    _route_top(
        canvas,
        source_bottom=counter_placed.top + counter.height + 1,
        source_x=counter_left + counter.zones["output"],
        destination_top=first_stage.top,
        destination_x=left + first_stage.room.zones["stream_in"],
        lane=6,
    )
    for source, destination in pairwise(placed_stages):
        _route_top(
            canvas,
            source_bottom=source.top + source.room.height + 1,
            source_x=left + source.room.zones["stream_out"],
            destination_top=destination.top,
            destination_x=left + destination.room.zones["stream_in"],
            lane=6,
        )
    return GroupPipeline(
        first_stage=first_stage,
        last_stage=placed_stages[-1],
        next_top=stage_top,
    )


def _route_top(
    canvas: Canvas,
    *,
    source_bottom: int,
    source_x: int,
    destination_top: int,
    destination_x: int,
    lane: int,
) -> None:
    row = destination_top - lane
    canvas.pipe(
        [
            (source_bottom + 1, source_x),
            (row, source_x),
            (row, destination_x),
            (destination_top - 1, destination_x),
        ]
    )


def build_subset_sum() -> str:
    parser = compile_fsm(build_parser_fsm(), PARSER_ZONES)
    counter = compile_fsm(build_counter_fsm(), COUNTER_ZONES)
    stages = [
        compile_fsm(
            build_bit_stage_fsm(index, first=index == 0, last=index == 9),
            STAGE_ZONES,
        )
        for index in range(10)
    ]
    merge = compile_fsm(build_merge_fsm(), MERGE_ZONES)
    reducer = compile_fsm(build_candidate_reducer_fsm(), REDUCER_ZONES)
    selector = compile_fsm(build_selector_fsm(), SELECTOR_ZONES)

    canvas = Canvas()
    parser_left = 3500
    parser_placed = _place_with_rings(
        canvas,
        top=7,
        left=parser_left,
        room=parser,
        rings=[("rem_in", "rem_out"), ("pad_in", "pad_out")],
        extension=100,
    )
    input_x = parser_left + parser.zones["input"]
    canvas.put(0, input_x - 1, ["+-+", "|I|", "+-+"])
    canvas.pipe([(3, input_x), (6, input_x)])

    generators_top = parser_placed.next_top + 24
    a_left = 500
    b_left = 3200
    group_a = _place_group_pipeline(
        canvas,
        top=generators_top,
        left=a_left,
        counter_left=600,
        counter=counter,
        stages=stages,
    )
    group_b = _place_group_pipeline(
        canvas,
        top=generators_top,
        left=b_left,
        counter_left=3400,
        counter=counter,
        stages=stages,
    )

    parser_bottom = parser_placed.top + parser.height + 1
    gen_a_source_x = parser_left + parser.zones["gen_a"]
    gen_a_destination_x = a_left + group_a.first_stage.room.zones["init"]
    canvas.pipe(
        [
            (parser_bottom + 1, gen_a_source_x),
            (generators_top - 24, gen_a_source_x),
            (generators_top - 24, gen_a_destination_x),
            (group_a.first_stage.top - 1, gen_a_destination_x),
        ]
    )
    gen_b_source_x = parser_left + parser.zones["gen_b"]
    gen_b_destination_x = b_left + group_b.first_stage.room.zones["init"]
    canvas.pipe(
        [
            (parser_bottom + 1, gen_b_source_x),
            (generators_top - 14, gen_b_source_x),
            (generators_top - 14, gen_b_destination_x),
            (group_b.first_stage.top - 1, gen_b_destination_x),
        ]
    )

    sorters_top = max(group_a.next_top, group_b.next_top) + 24
    sort_a = _place_systolic_sorter(
        canvas,
        top=sorters_top,
        left=a_left,
        descending=True,
    )
    sort_b = _place_systolic_sorter(
        canvas,
        top=sorters_top,
        left=b_left,
        descending=False,
    )
    _route_top(
        canvas,
        source_bottom=group_a.last_stage.top + group_a.last_stage.room.height + 1,
        source_x=a_left + group_a.last_stage.room.zones["stream_out"],
        destination_top=sort_a.input_top,
        destination_x=sort_a.input_x,
        lane=10,
    )
    _route_top(
        canvas,
        source_bottom=group_b.last_stage.top + group_b.last_stage.room.height + 1,
        source_x=b_left + group_b.last_stage.room.zones["stream_out"],
        destination_top=sort_b.input_top,
        destination_x=sort_b.input_x,
        lane=10,
    )

    merge_top = max(sort_a.next_top, sort_b.next_top) + 30
    merge_left = 2800
    merge_placed = _place_with_rings(
        canvas,
        top=merge_top,
        left=merge_left,
        room=merge,
        rings=[
            ("target_in", "target_out"),
            ("a_sum_in", "a_sum_out"),
            ("a_mask_in", "a_mask_out"),
            ("b_sum_in", "b_sum_out"),
            ("b_mask_in", "b_mask_out"),
        ],
        extension=120,
    )

    _route_top(
        canvas,
        source_bottom=sort_a.output_bottom,
        source_x=sort_a.output_x,
        destination_top=merge_top,
        destination_x=merge_left + merge.zones["a_input"],
        lane=18,
    )
    target_source_x = parser_left + parser.zones["target"]
    canvas.pipe(
        [
            (parser_bottom + 1, target_source_x),
            (generators_top - 17, target_source_x),
            (generators_top - 17, 3000),
            (merge_top - 14, 3000),
            (merge_top - 14, merge_left + merge.zones["target_input"]),
            (merge_top - 1, merge_left + merge.zones["target_input"]),
        ]
    )

    _route_top(
        canvas,
        source_bottom=sort_b.output_bottom,
        source_x=sort_b.output_x,
        destination_top=merge_top,
        destination_x=merge_left + merge.zones["b_input"],
        lane=10,
    )

    reducer_top = merge_placed.next_top + 24
    reducer_left = 3000
    reducer_placed = _place_with_rings(
        canvas,
        top=reducer_top,
        left=reducer_left,
        room=reducer,
        rings=[],
        extension=0,
    )
    _route_top(
        canvas,
        source_bottom=merge_placed.top + merge.height + 1,
        source_x=merge_left + merge.zones["candidate_output"],
        destination_top=reducer_top,
        destination_x=reducer_left + reducer.zones["input"],
        lane=10,
    )

    selector_top = reducer_placed.next_top + 30
    selector_left = 1000
    selector_placed = _place_with_rings(
        canvas,
        top=selector_top,
        left=selector_left,
        room=selector,
        rings=[
            ("values_in", "values_out"),
            ("work_in", "work_out"),
            ("reverse_in", "reverse_out"),
            ("count_in", "count_out"),
            ("selected_in", "selected_out"),
        ],
        extension=100,
    )
    values_source_x = parser_left + parser.zones["values"]
    values_destination_x = selector_left + selector.zones["values_input"]
    canvas.pipe(
        [
            (parser_bottom + 1, values_source_x),
            (generators_top - 27, values_source_x),
            (generators_top - 27, 400),
            (merge_placed.next_top + 5, 400),
            (merge_placed.next_top + 5, values_destination_x),
            (selector_top - 1, values_destination_x),
        ]
    )
    _route_top(
        canvas,
        source_bottom=reducer_placed.top + reducer.height + 1,
        source_x=reducer_left + reducer.zones["output"],
        destination_top=selector_top,
        destination_x=selector_left + selector.zones["mask_input"],
        lane=10,
    )

    output_x = selector_left + selector.zones["output"]
    output_top = selector_placed.next_top + 8
    canvas.put(output_top, output_x - 1, ["+-+", "|O|", "+-+"])
    canvas.pipe(
        [
            (selector_placed.top + selector.height + 2, output_x),
            (output_top - 1, output_x),
        ]
    )
    return canvas.render()
