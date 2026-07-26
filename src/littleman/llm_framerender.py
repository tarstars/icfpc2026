"""Render repeated normalized LLM states on the proven 16x16 display."""

from __future__ import annotations

from .canvas import Canvas
from .lllm_draw import place_display_block
from .llm_pairpack import build_pairpack_rig
from .llm_roomstage import _strip_io
from .llm_stateframe import build_stateframe_rig


def build_framerender_rig() -> str:
    cv = Canvas()
    left = 20
    frame_rows, frame_in, frame_out = _strip_io(build_stateframe_rig())
    pair_rows, pair_in, pair_out = _strip_io(build_pairpack_rig())
    pair_top = len(frame_rows) + 20
    cv.put(0, left, frame_rows)
    cv.put(pair_top, left, pair_rows)

    frame_in = (frame_in[0], left + frame_in[1])
    frame_out = (frame_out[0], left + frame_out[1])
    pair_in = (pair_top + pair_in[0], left + pair_in[1])
    pair_out = (pair_top + pair_out[0], left + pair_out[1])
    track = 10
    cv.pipe(
        [
            frame_out,
            (frame_out[0], track),
            (pair_in[0], track),
            pair_in,
        ]
    )

    draw_row = pair_top + len(pair_rows) + 30
    draw_col = 20
    place_display_block(cv, draw_row, draw_col)
    draw_in = (draw_row + 2, draw_col - 1)
    cv.pipe(
        [
            pair_out,
            (pair_out[0], track),
            (draw_in[0], track),
            draw_in,
        ]
    )
    cv.put(frame_in[0] - 1, 0, ["+-+", "|I|", "+-+"])
    cv.pipe([(frame_in[0], 3), frame_in])
    return cv.render()
