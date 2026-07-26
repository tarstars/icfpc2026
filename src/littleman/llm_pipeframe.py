"""Render one normalized LLM pipe record as address/color pairs."""

from __future__ import annotations

from .lllm_scan import _compile, _Fsm
from .llm import COLOR_PIPE, COLOR_PIPE_FULL
from .llm_pipetrace import PIPE_END
from .llm_statebuild import PIPE_DEST_STATE, PIPE_MASK, PIPE_VALUES

PIPE_FRAME_END = -3700
SCRATCH_END = -1


def pipeframe_reference(tokens: list[int]) -> list[int]:
    """Consume concatenated pipe records and delimit every rendered result."""
    out = []
    index = 0
    while index < len(tokens):
        index += 1  # start descriptor
        pairs = []
        while tokens[index] != PIPE_DEST_STATE:
            pairs.append(tuple(tokens[index : index + 2]))
            index += 2
        index += 2  # destination marker and wall address
        if tokens[index] != PIPE_MASK:
            raise ValueError(f"missing pipe mask: {tokens[index]}")
        mask = tokens[index + 1]
        index += 2
        if tokens[index] != PIPE_VALUES:
            raise ValueError(f"missing pipe values: {tokens[index]}")
        count = tokens[index + 1]
        index += 2 + count
        if tokens[index] != PIPE_END:
            raise ValueError(f"missing pipe end: {tokens[index]}")
        index += 1
        for cell, bit in pairs:
            out.extend((cell, COLOR_PIPE_FULL if mask & bit else COLOR_PIPE))
        out.append(PIPE_FRAME_END)
    return out


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "start_r")
    fsm.go("start_r", "left", "r", "cell_r")
    fsm.go("cell_r", "left", "r", "cell_cmp")
    fsm.sign(
        "cell_cmp",
        "lit_l",
        f"M`{PIPE_DEST_STATE:04d}`-",
        neg="cell_restore",
        zero="scratch_end",
        pos="cell_restore",
    )
    fsm.go("cell_restore", "right", "Ws", "bit_r")
    fsm.go("bit_r", "left", "r", "bit_store")
    fsm.go("bit_store", "right", "s", "cell_r")
    fsm.go("scratch_end", "right", "1Ns", "dest_value_r")
    fsm.go("dest_value_r", "left", "r", "mask_marker_r")
    fsm.go("mask_marker_r", "left", "r", "mask_r")
    fsm.go("mask_r", "left", "rM", "values_marker_r")
    fsm.go("values_marker_r", "left", "r", "values_count_r")
    fsm.go("values_count_r", "left", "rb", "values_count")
    fsm.bp(
        "values_count",
        "mid",
        "",
        zero="pipe_end_r",
        pos="value_r",
    )
    fsm.go("value_r", "left", "r", "value_dec")
    fsm.bp(
        "value_dec",
        "mid",
        "m",
        zero="pipe_end_r",
        pos="value_r",
    )
    fsm.go("pipe_end_r", "left", "r", "pair_r")

    # B keeps the mask throughout this loop; r/s, &, signs, and digits do
    # not clobber it.
    fsm.sign(
        "pair_r",
        "right",
        "r",
        neg="frame_end",
        zero="cell_out",
        pos="cell_out",
    )
    fsm.go("cell_out", "left", "s", "stored_bit_r")
    fsm.go("stored_bit_r", "right", "r&", "occupied")
    fsm.sign(
        "occupied",
        "right",
        "",
        neg="full_out",
        zero="empty_out",
        pos="full_out",
    )
    fsm.go("empty_out", "left", f"{COLOR_PIPE}s", "pair_r")
    fsm.go("full_out", "lit_l", f" `{COLOR_PIPE_FULL:04d}`s", "pair_r")
    fsm.go(
        "frame_end",
        "lit_l",
        f"M`{-PIPE_FRAME_END:04d}`Ns",
        "start_r",
    )
    return fsm


def build_pipeframe_room() -> list[str]:
    return _compile(_build_fsm())


CTRL_LEFT = 5
INPUT_ROW, OUTPUT_ROW = 2, 6
RING_OUT_ROW, RING_IN_ROW = 2, 9


def build_pipeframe_rig() -> str:
    from .canvas import Canvas
    from .lllm_fetch import build_relay

    room = build_pipeframe_room()
    right = CTRL_LEFT + len(room[0]) - 1
    relay_left = right + 5
    far = relay_left + 17
    cv = Canvas()
    cv.put(0, CTRL_LEFT, room)
    cv.put(INPUT_ROW - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(OUTPUT_ROW - 1, 0, ["+-+", "|O|", "+-+"])
    cv.put(20, relay_left, build_relay().render())
    cv.pipe([(INPUT_ROW, 3), (INPUT_ROW, CTRL_LEFT - 1)])
    cv.pipe([(OUTPUT_ROW, CTRL_LEFT - 1), (OUTPUT_ROW, 3)])
    cv.pipe(
        [
            (RING_OUT_ROW, right + 1),
            (RING_OUT_ROW, far),
            (21, far),
            (21, relay_left + 6),
        ]
    )
    cv.pipe(
        [
            (21, relay_left - 1),
            (21, right + 2),
            (RING_IN_ROW, right + 2),
            (RING_IN_ROW, right + 1),
        ]
    )
    return cv.render()
