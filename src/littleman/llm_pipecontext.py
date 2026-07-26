"""Pack one indexed LLM pipe record for candidate selection."""

from __future__ import annotations

from .canvas import Canvas
from .lllm_fetch import build_relay
from .lllm_scan import _compile, _Fsm
from .llm_packedcandidate import pack_pipe_context
from .llm_pipetrace import PIPE_END
from .llm_statebuild import PIPE_DEST_STATE, PIPE_MASK, PIPE_VALUES


def pipecontext_reference(tokens: list[int]) -> list[int]:
    """Map complete indexed pipe records to one packed word each."""
    out = []
    index = 0
    while index < len(tokens):
        _start, source_event = tokens[index : index + 2]
        index += 2
        cells = []
        while tokens[index] != PIPE_DEST_STATE:
            cells.append(tokens[index])
            index += 2
        dest = tokens[index + 1]
        index += 2
        if tokens[index] != PIPE_MASK:
            raise ValueError(f"missing pipe mask: {tokens[index]}")
        index += 2
        if tokens[index] != PIPE_VALUES:
            raise ValueError(f"missing pipe values: {tokens[index]}")
        count = tokens[index + 1]
        index += 2 + count
        if tokens[index] != PIPE_END:
            raise ValueError(f"missing pipe end: {tokens[index]}")
        index += 1
        if not cells:
            raise ValueError("pipe context requires at least one cell")
        out.append(pack_pipe_context(source_event, cells[0], cells[-1], dest))
    return out


def _scale(fsm: _Fsm, name: str, factor: int, target: str) -> None:
    fsm.go(name, "right", "rM", f"{name}_mul")
    fsm.go(f"{name}_mul", "lit_r", f" `{factor}`W*s", target)


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "start_r")
    fsm.go("start_r", "left", "r", "source_r")
    fsm.go("source_r", "left", "r", "source_s")
    fsm.go("source_s", "right", "s", "head_r")
    fsm.go("head_r", "left", "r", "head_s")
    fsm.go("head_s", "right", "ss", "head_bit_drop")
    fsm.go("head_bit_drop", "left", "r", "cell_r")
    fsm.go("cell_r", "left", "r", "cell_cmp")
    fsm.sign(
        "cell_cmp",
        "lit_l",
        f"M`{PIPE_DEST_STATE}`-",
        neg="bad_record",
        zero="dest_r",
        pos="tail_replace",
    )
    fsm.go("bad_record", "left", "H", "bad_record")
    # B still contains the original cell after the marker comparison.
    fsm.go("tail_replace", "right", "WMrsrsrWs", "bit_drop")
    fsm.go("bit_drop", "left", "r", "cell_r")

    fsm.go("dest_r", "left", "r", "dest_s")
    fsm.go("dest_s", "right", "s", "mask_marker_drop")
    fsm.go("mask_marker_drop", "left", "r", "mask_drop")
    fsm.go("mask_drop", "left", "r", "values_marker_drop")
    fsm.go("values_marker_drop", "left", "r", "count_r")
    fsm.go("count_r", "left", "rb", "values_count")
    fsm.bp("values_count", "mid", "", zero="pipe_end_drop", pos="value_drop")
    fsm.go("value_drop", "left", "r", "values_dec")
    fsm.bp("values_dec", "mid", "m", zero="pipe_end_drop", pos="value_drop")
    fsm.go("pipe_end_drop", "left", "r", "source_scale")

    # Ring is source_event, head, tail, dest.
    fsm.go("source_scale", "right", "rNM1W-M+s", "head_scale")
    _scale(fsm, "head_scale", 1 << 9, "tail_scale")
    _scale(fsm, "tail_scale", 1 << 17, "dest_scale")
    _scale(fsm, "dest_scale", 1 << 25, "sum_source")
    fsm.go("sum_source", "right", "rM", "sum_head")
    fsm.go("sum_head", "right", "r+M", "sum_tail")
    fsm.go("sum_tail", "right", "r+M", "sum_dest")
    fsm.go("sum_dest", "right", "r+M1+", "context_out")
    fsm.go("context_out", "left", "s", "start_r")
    return fsm


def build_pipecontext_room() -> list[str]:
    return _compile(_build_fsm())


CTRL_LEFT = 5
INPUT_ROW, OUTPUT_ROW = 2, 6
RING_OUT_ROW, RING_IN_ROW = 2, 9


def build_pipecontext_rig() -> str:
    room = build_pipecontext_room()
    right = CTRL_LEFT + len(room[0]) - 1
    relay_left = right + 5
    far = relay_left + 17
    cv = Canvas()
    cv.put(0, CTRL_LEFT, room)
    cv.put(20, relay_left, build_relay().render())
    cv.put(INPUT_ROW - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(OUTPUT_ROW - 1, 0, ["+-+", "|O|", "+-+"])
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
