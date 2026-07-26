"""Compose the physical one-tick normalized-state map pipeline."""

from __future__ import annotations

from .canvas import Canvas
from .lllm_fetch import build_relay
from .llm_fetchjoin import build_fetchjoin_room, fetchjoin_reference
from .llm_manmap import build_manmap_room, manmap_reference
from .llm_manstep import build_manstep_room
from .llm_maskmap import (
    build_maskprefix_room,
    maskprefix_reference,
)
from .llm_pipemask import build_pipemask_room
from .llm_recordstrip import build_recordstrip_room, recordstrip_reference
from .llm_runtimefetch import build_runtimefetch_room

MAIN_LEFT = 100
INPUT_ROW, OUTPUT_ROW = 2, 6
CMD_ROW, RESP_ROW = 2, 9


def tickcycle_reference(tokens: list[int]) -> list[int]:
    stream = maskprefix_reference(tokens)
    stream = fetchjoin_reference(stream)
    stream = manmap_reference(stream)
    return recordstrip_reference(stream)


def statecycle_reference(world: list[int], state: list[int]) -> list[int]:
    """One later cycle after RUNTIMEFETCH has already loaded the world."""
    from .llm_maskmap import maskmap_reference

    stream = maskmap_reference(state)
    stream = fetchjoin_reference([*world, *stream])
    stream = manmap_reference(stream)
    return recordstrip_reference(stream)


def _place_service_stage(
    cv: Canvas,
    top: int,
    controller: list[str],
    service: list[str],
) -> tuple[tuple[int, int], tuple[int, int], int]:
    left = MAIN_LEFT
    ctrl_right = left + len(controller[0]) - 1
    service_left = ctrl_right + 10
    service_right = service_left + len(service[0]) - 1
    relay_left = service_right + 5
    far = relay_left + 17
    cv.put(top, left, controller)
    cv.put(top, service_left, service)
    cv.put(top + 20, relay_left, build_relay().render())
    cv.pipe([(top + CMD_ROW, ctrl_right + 1), (top + CMD_ROW, service_left - 1)])
    cv.pipe(
        [
            (top + 6, service_left - 1),
            (top + 6, ctrl_right + 4),
            (top + RESP_ROW, ctrl_right + 4),
            (top + RESP_ROW, ctrl_right + 1),
        ]
    )
    cv.pipe(
        [
            (top + 2, service_right + 1),
            (top + 2, far),
            (top + 21, far),
            (top + 21, relay_left + 6),
        ]
    )
    cv.pipe(
        [
            (top + 21, relay_left - 1),
            (top + 21, service_right + 2),
            (top + 9, service_right + 2),
            (top + 9, service_right + 1),
        ]
    )
    bottom = top + max(len(controller), len(service), 25)
    return (top + INPUT_ROW, left - 1), (top + OUTPUT_ROW, left - 1), bottom


def place_tick_pipeline(
    cv: Canvas, top: int = 0
) -> tuple[tuple[int, int], tuple[int, int], int]:
    stages = [
        (build_maskprefix_room(), build_pipemask_room()),
        (build_fetchjoin_room(), build_runtimefetch_room()),
        (build_manmap_room(), build_manstep_room()),
    ]
    ports = []
    for controller, service in stages:
        source, target, bottom = _place_service_stage(cv, top, controller, service)
        ports.append((source, target))
        top = bottom + 10

    strip = build_recordstrip_room()
    cv.put(top, MAIN_LEFT, strip)
    ports.append(
        (
            (top + INPUT_ROW, MAIN_LEFT - 1),
            (top + OUTPUT_ROW, MAIN_LEFT - 1),
        )
    )

    for index, (source, target) in enumerate(
        zip(
            (port[1] for port in ports),
            (port[0] for port in ports[1:]),
        )
    ):
        spine = 80 - index * 10
        cv.pipe([source, (source[0], spine), (target[0], spine), target])
    return ports[0][0], ports[-1][1], top + len(strip)


def build_tick_pipeline() -> str:
    cv = Canvas()
    input_port, output_port, _bottom = place_tick_pipeline(cv)
    cv.put(1, 0, ["+-+", "|I|", "+-+"])
    cv.pipe([(2, 3), input_port])
    final_row = output_port[0]
    cv.put(final_row - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([output_port, (final_row, 3)])
    return cv.render()
