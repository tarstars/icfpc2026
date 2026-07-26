"""Delimiter-safe physical copy of one indexed LLM state stream."""

from __future__ import annotations

from .canvas import Canvas
from .lllm_fetch import build_relay
from .lllm_scan import _compile, _Fsm, _layout
from .llm_roomfind import SETUP_END
from .llm_statebuild import PIPE_MASK
from .llm_stateindex import INDEX_END

INDEX_COPY_SPLIT = -5000
INDEX_COPY_END = -5100


def indexcopy_reference(tokens: list[int]) -> list[int]:
    return indexmulticopy_reference(tokens, 2)


def indexmulticopy_reference(tokens: list[int], copies: int) -> list[int]:
    if copies < 2:
        raise ValueError("indexed copy count must be at least two")
    if not tokens or tokens[-1] != INDEX_END:
        raise ValueError("index copy requires one complete indexed state")
    out = []
    for index in range(copies):
        out.extend(tokens)
        out.append(INDEX_COPY_END if index + 1 == copies else INDEX_COPY_SPLIT)
    return out


def _build_fsm(prefix_words: int = 0, copies: int = 2) -> _Fsm:
    if prefix_words < 0:
        raise ValueError("prefix length must be non-negative")
    if copies < 2:
        raise ValueError("indexed copy count must be at least two")
    fsm = _Fsm()
    first = "prefix_0" if prefix_words else "load_header_r"
    fsm.go("boot", "left", "@", first)
    for index in range(prefix_words):
        target = f"prefix_{index + 1}" if index + 1 < prefix_words else "load_header_r"
        fsm.go(f"prefix_{index}", "left", "rs", target)

    def plain(prefix: str, name: str, source: str, target: str, duplicate: bool):
        fsm.go(f"{prefix}_{name}_r", source, "r", f"{prefix}_{name}_out")
        after = f"{prefix}_{name}_scratch" if duplicate else target
        fsm.go(f"{prefix}_{name}_out", "left", "s", after)
        if duplicate:
            fsm.go(f"{prefix}_{name}_scratch", "right", "s", target)

    def restored(
        prefix: str,
        name: str,
        target: str,
        duplicate: bool,
    ):
        after = f"{prefix}_{name}_scratch" if duplicate else target
        fsm.go(f"{prefix}_{name}_restore", "left", "Ws", after)
        if duplicate:
            fsm.go(f"{prefix}_{name}_scratch", "right", "s", target)

    def indexed_pass(prefix: str, source: str, duplicate: bool, done: str):
        fsm.go(f"{prefix}_header_r", source, "r", f"{prefix}_header_cmp")
        fsm.sign(
            f"{prefix}_header_cmp",
            "lit_l" if source == "left" else "lit_r",
            f"M`{abs(SETUP_END)}`+",
            neg="bad_stream",
            zero=f"{prefix}_setup_restore",
            pos=f"{prefix}_event_restore",
        )
        restored(prefix, "event", f"{prefix}_field_0_r", duplicate)
        for index in range(11):
            target = (
                f"{prefix}_field_{index + 1}_r" if index < 10 else f"{prefix}_header_r"
            )
            plain(prefix, f"field_{index}", source, target, duplicate)
        restored(prefix, "setup", f"{prefix}_split_r", duplicate)
        plain(prefix, "split", source, f"{prefix}_pipe_start_r", duplicate)

        fsm.go(
            f"{prefix}_pipe_start_r",
            source,
            "r",
            f"{prefix}_pipe_start_cmp",
        )
        fsm.sign(
            f"{prefix}_pipe_start_cmp",
            "lit_l" if source == "left" else "lit_r",
            f"M`{abs(INDEX_END)}`+",
            neg="bad_stream",
            zero=f"{prefix}_index_restore",
            pos=f"{prefix}_start_restore",
        )
        restored(prefix, "start", f"{prefix}_source_r", duplicate)
        plain(prefix, "source", source, f"{prefix}_body_r", duplicate)
        fsm.go(f"{prefix}_body_r", source, "r", f"{prefix}_body_cmp")
        fsm.sign(
            f"{prefix}_body_cmp",
            "lit_l" if source == "left" else "lit_r",
            f"M`{abs(PIPE_MASK)}`+",
            neg="bad_stream",
            zero=f"{prefix}_mask_restore",
            pos=f"{prefix}_body_restore",
        )
        restored(prefix, "body", f"{prefix}_bit_r", duplicate)
        plain(prefix, "bit", source, f"{prefix}_body_r", duplicate)
        restored(prefix, "mask", f"{prefix}_mask_value_r", duplicate)
        plain(
            prefix,
            "mask_value",
            source,
            f"{prefix}_values_marker_r",
            duplicate,
        )
        plain(
            prefix,
            "values_marker",
            source,
            f"{prefix}_count_r",
            duplicate,
        )
        fsm.go(f"{prefix}_count_r", source, "rMb", f"{prefix}_count_out")
        after_count = f"{prefix}_count_scratch" if duplicate else f"{prefix}_values"
        fsm.go(f"{prefix}_count_out", "left", "s", after_count)
        if duplicate:
            fsm.go(
                f"{prefix}_count_scratch",
                "right",
                "s",
                f"{prefix}_values",
            )
        fsm.bp(
            f"{prefix}_values",
            "mid",
            "",
            zero=f"{prefix}_pipe_end_r",
            pos=f"{prefix}_value_r",
        )
        plain(prefix, "value", source, f"{prefix}_value_dec", duplicate)
        fsm.bp(
            f"{prefix}_value_dec",
            "mid",
            "m",
            zero=f"{prefix}_pipe_end_r",
            pos=f"{prefix}_value_r",
        )
        plain(
            prefix,
            "pipe_end",
            source,
            f"{prefix}_pipe_start_r",
            duplicate,
        )
        restored(prefix, "index", done, duplicate)

    indexed_pass("load", "left", True, "split_out")
    fsm.go(
        "split_out",
        "lit_l",
        f" `{abs(INDEX_COPY_SPLIT)}`Ns",
        "copy_header_r",
    )
    if copies == 2:
        indexed_pass("copy", "right", False, "copy_end")
    else:
        indexed_pass("copy", "right", True, "copy_split_2")
        for copy_no in range(2, copies):
            prefix = f"copy{copy_no}"
            fsm.go(
                f"copy_split_{copy_no}",
                "lit_l",
                f" `{abs(INDEX_COPY_SPLIT)}`Ns",
                f"{prefix}_header_r",
            )
            indexed_pass(
                prefix,
                "right",
                copy_no + 1 < copies,
                (f"copy_split_{copy_no + 1}" if copy_no + 1 < copies else "copy_end"),
            )
    fsm.go(
        "copy_end",
        "lit_l",
        f" `{abs(INDEX_COPY_END)}`Ns",
        first,
    )
    fsm.go("bad_stream", "left", "H", "bad_stream")
    return fsm


def build_indexcopy_room(prefix_words: int = 0, copies: int = 2) -> list[str]:
    return _compile(_build_fsm(prefix_words, copies), extra_gap=96)


def _port_rows(prefix_words: int = 0, copies: int = 2) -> tuple[int, int, int, int]:
    fsm = _build_fsm(prefix_words, copies)
    _routes, blocks, _height = _layout(fsm)
    groups = ([], [], [], [])
    main_in, main_out, scratch_out, scratch_in = groups
    for name, zone, code, _kind, _targets in fsm.blocks:
        for char in code:
            if char == "r":
                (
                    scratch_in
                    if name.startswith("copy") and zone == "right"
                    else main_in
                ).append(blocks[name])
            elif char == "s":
                (
                    scratch_out
                    if zone == "right" and name.startswith(("load_", "copy"))
                    else main_out
                ).append(blocks[name])

    def middle(rows):
        return (min(rows) + max(rows)) // 2

    return tuple(middle(rows) for rows in groups)


def add_indexcopy_network(
    cv: Canvas,
    *,
    top: int,
    left: int,
    prefix_words: int = 0,
    copies: int = 2,
) -> tuple[tuple[int, int], tuple[int, int]]:
    room = build_indexcopy_room(prefix_words, copies)
    right = left + len(room[0]) - 1
    relay_left = right + 5
    far = relay_left + 17
    relay_top = top + len(room) + 20
    input_row, output_row, scratch_out, scratch_in = _port_rows(prefix_words, copies)
    input_row += top
    output_row += top
    scratch_out += top
    scratch_in += top
    cv.put(top, left, room)
    cv.put(relay_top, relay_left, build_relay().render())
    cv.pipe(
        [
            (scratch_out, right + 1),
            (scratch_out, far),
            (relay_top + 1, far),
            (relay_top + 1, relay_left + 6),
        ]
    )
    cv.pipe(
        [
            (relay_top + 1, relay_left - 1),
            (relay_top + 1, right + 2),
            (scratch_in, right + 2),
            (scratch_in, right + 1),
        ]
    )
    return (input_row, left - 1), (output_row, left - 1)


def build_indexcopy_rig(copies: int = 2) -> str:
    cv = Canvas()
    ingress, egress = add_indexcopy_network(cv, top=0, left=5, copies=copies)
    cv.put(ingress[0] - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(egress[0] - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(ingress[0], 3), ingress])
    cv.pipe([egress, (egress[0], 3)])
    return cv.render()
