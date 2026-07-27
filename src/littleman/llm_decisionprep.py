"""Reorder indexed decision metadata into a selector request."""

from __future__ import annotations

from .canvas import Canvas
from .lllm_fetch import build_relay
from .lllm_scan import _compile, _Fsm, _layout
from .llm_indexdecision import _indexed_end, _relay_indexed, META_WORDS

PREP_WORDS = 8


def decisionprep_reference(tokens: list[int]) -> list[int]:
    """Emit ``active, op, ctrl, A, context, p0, context, p1, state``."""
    out = []
    index = 0
    while index < len(tokens):
        active, context, ctrl, ai, pipe0, pipe1 = tokens[index : index + META_WORDS]
        index += META_WORDS
        end = _indexed_end(tokens, index)
        state = tokens[index:end]
        index = end
        if active:
            out.extend((1, context & 1, ctrl, ai, context, pipe0, context, pipe1))
        else:
            out.extend((0,) * PREP_WORDS)
        out.extend(state)
    return out


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "active_r")
    fsm.go("active_r", "left", "r", "active_s")
    fsm.go("active_s", "right", "s", "context_r")
    fsm.go("context_r", "left", "r", "context_s")
    fsm.go("context_s", "right", "sss", "ctrl_r")
    for name, target in (
        ("ctrl", "ai_r"),
        ("ai", "pipe0_r"),
        ("pipe0", "pipe1_r"),
        ("pipe1", "active_get"),
    ):
        fsm.go(f"{name}_r", "left", "r", f"{name}_s")
        fsm.go(f"{name}_s", "right", "s", target)

    fsm.go("active_get", "right", "r", "active_branch")
    fsm.sign(
        "active_branch",
        "mid",
        "",
        neg="bad_meta",
        zero="inactive_drop",
        pos="active_out",
    )
    fsm.go("bad_meta", "left", "H", "bad_meta")
    fsm.go("inactive_drop", "right", "r" * 7, "inactive_out")
    fsm.go("inactive_out", "left", "0s" * PREP_WORDS, "relay_header_r")

    fsm.go("active_out", "left", "1s", "op_context_r")
    fsm.go("op_context_r", "right", "rM", "op_mask")
    fsm.go("op_mask", "lit_r", "M`0001`W&", "op_out")
    fsm.go("op_out", "left", "s", "contexts_rotate")
    fsm.go("contexts_rotate", "right", "rsrs", "ctrl_out_r")
    for name, target in (("ctrl", "ai_out_r"), ("ai", "pipes_rotate")):
        fsm.go(f"{name}_out_r", "right", "r", f"{name}_out")
        fsm.go(f"{name}_out", "left", "s", target)

    # Ring is p0, p1, context0, context1. Emit context0,p0,context1,p1.
    fsm.go("pipes_rotate", "right", "rsrs", "context0_out_r")
    fsm.go("context0_out_r", "right", "r", "context0_out")
    fsm.go("context0_out", "left", "s", "context1_rotate")
    fsm.go("context1_rotate", "right", "rs", "pipe0_out_r")
    fsm.go("pipe0_out_r", "right", "r", "pipe0_out")
    fsm.go("pipe0_out", "left", "s", "pipe1_rotate")
    fsm.go("pipe1_rotate", "right", "rs", "context1_out_r")
    fsm.go("context1_out_r", "right", "r", "context1_out")
    fsm.go("context1_out", "left", "s", "pipe1_out_r")
    fsm.go("pipe1_out_r", "right", "r", "pipe1_out")
    fsm.go("pipe1_out", "left", "s", "relay_header_r")

    _relay_indexed(fsm, "active_r", consume_tail=False)
    fsm.go("bad_stream", "left", "H", "bad_stream")
    return fsm


def build_decisionprep_room() -> list[str]:
    return _compile(_build_fsm(), extra_gap=96)


def _port_rows() -> tuple[int, int, int, int]:
    fsm = _build_fsm()
    _routes, blocks, _height = _layout(fsm)
    scratch_names = {
        name
        for name, zone, _code, _kind, _targets in fsm.blocks
        if zone == "right"
    }
    scratch_out = []
    scratch_in = []
    main_in = []
    main_out = []
    for name, _zone, code, _kind, _targets in fsm.blocks:
        (scratch_in if name in scratch_names else main_in).extend(
            [blocks[name]] * code.count("r")
        )
        (scratch_out if name in scratch_names else main_out).extend(
            [blocks[name]] * code.count("s")
        )

    def middle(rows):
        return (min(rows) + max(rows)) // 2

    return tuple(middle(rows) for rows in (main_in, main_out, scratch_out, scratch_in))


def build_decisionprep_rig() -> str:
    room = build_decisionprep_room()
    left = 5
    right = left + len(room[0]) - 1
    relay_left = right + 5
    far = relay_left + 17
    relay_top = len(room) + 20
    input_row, output_row, scratch_out, scratch_in = _port_rows()
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
    return cv.render()
