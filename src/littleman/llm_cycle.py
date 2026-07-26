"""Recirculate normalized LLM state through the physical tick pipeline."""

from __future__ import annotations

from .canvas import Canvas
from .lllm_scan import _compile, _Fsm
from .llm_roomfind import WORLD_WORDS
from .llm_tick_assemble import place_tick_pipeline, statecycle_reference


def cycle_reference(tokens: list[int], ticks: int) -> list[int]:
    world = tokens[:WORLD_WORDS]
    state = tokens[WORLD_WORDS:]
    for _ in range(ticks):
        state = statecycle_reference(world, state)
    return state


def _build_gate_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "source_r")
    fsm.go("source_r", "left", "r", "source_cmp")
    fsm.sign(
        "source_cmp",
        "lit_l",
        "M`1000`+",
        neg="source_restore",
        zero="source_end",
        pos="source_restore",
    )
    fsm.go("source_restore", "left", "W", "source_send")
    fsm.go("source_send", "right", "s", "source_r")
    fsm.go("source_end", "right", "Ws", "ticks_r")
    fsm.go("ticks_r", "left", "rb", "cycle_count")
    fsm.bp(
        "cycle_count",
        "mid",
        "m",
        zero="final_r",
        pos="recycle_r",
    )

    fsm.go("recycle_r", "right", "r", "recycle_cmp")
    fsm.sign(
        "recycle_cmp",
        "lit_r",
        "M`1000`+",
        neg="recycle_restore",
        zero="recycle_end",
        pos="recycle_restore",
    )
    fsm.go("recycle_restore", "right", "Ws", "recycle_r")
    fsm.go("recycle_end", "right", "Ws", "cycle_count")

    fsm.go("final_r", "right", "r", "final_cmp")
    fsm.sign(
        "final_cmp",
        "lit_r",
        "M`1000`+",
        neg="final_restore",
        zero="final_end",
        pos="final_restore",
    )
    fsm.go("final_restore", "left", "Ws", "final_r")
    fsm.go("final_end", "left", "WsH", "final_end")
    return fsm


def build_cycle_gate_room() -> list[str]:
    return _compile(_build_gate_fsm())


GATE_LEFT = 5
GATE_REQ_ROW, GATE_RESP_ROW = 2, 9
PIPELINE_TOP = 60


def build_cycle_rig() -> str:
    gate = build_cycle_gate_room()
    gate_right = GATE_LEFT + len(gate[0]) - 1
    cv = Canvas()
    cv.put(0, GATE_LEFT, gate)
    pipeline_in, pipeline_out, _bottom = place_tick_pipeline(cv, PIPELINE_TOP)
    cv.put(1, 0, ["+-+", "|I|", "+-+"])
    cv.put(5, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(2, 3), (2, GATE_LEFT - 1)])
    cv.pipe([(6, GATE_LEFT - 1), (6, 3)])

    request_track = 92
    cv.pipe(
        [
            (GATE_REQ_ROW, gate_right + 1),
            (GATE_REQ_ROW, request_track),
            (pipeline_in[0], request_track),
            pipeline_in,
        ]
    )
    cv.pipe(
        [
            pipeline_out,
            (pipeline_out[0], 50),
            (50, 50),
            (50, 90),
            (GATE_RESP_ROW, 90),
            (GATE_RESP_ROW, gate_right + 1),
        ]
    )
    return cv.render()
