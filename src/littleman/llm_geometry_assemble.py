"""Compose the physical LLM geometry stages through complete pipe traces."""

from __future__ import annotations

from .canvas import Canvas
from .lllm_fetch import build_relay
from .llm_candidatefetch import build_candidate_fetch_room
from .llm_cmpfetch import build_compare_fetch_room
from .llm_perimeter import build_perimeter_room
from .llm_pipestarts import build_pipestarts_room
from .llm_pipetrace import build_pipetrace_dest_room, build_pipetrace_room
from .llm_rawfetch import build_raw_fetch
from .llm_roomfind import build_roomfind_room

MAIN_LEFT = 100
CTRL_CMD_ROW, CTRL_RESP_ROW = 2, 9
CTRL_INPUT_ROW, CTRL_OUTPUT_ROW = 2, 6


def _place_stage(
    cv: Canvas,
    top: int,
    ctrl: list[str],
    service: list[str],
    *,
    service_resp_row: int,
    service_ring_in_row: int,
) -> tuple[tuple[int, int], tuple[int, int]]:
    left = MAIN_LEFT
    ctrl_right = left + len(ctrl[0]) - 1
    service_left = ctrl_right + 10
    service_right = service_left + len(service[0]) - 1
    relay_left = service_right + 5
    far = relay_left + 17
    cv.put(top, left, ctrl)
    cv.put(top, service_left, service)
    cv.put(top + 20, relay_left, build_relay().render())
    cv.pipe(
        [
            (top + CTRL_CMD_ROW, ctrl_right + 1),
            (top + CTRL_CMD_ROW, service_left - 1),
        ]
    )
    cv.pipe(
        [
            (top + service_resp_row, service_left - 1),
            (top + service_resp_row, ctrl_right + 4),
            (top + CTRL_RESP_ROW, ctrl_right + 4),
            (top + CTRL_RESP_ROW, ctrl_right + 1),
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
            (top + service_ring_in_row, service_right + 2),
            (top + service_ring_in_row, service_right + 1),
        ]
    )
    return (
        (top + CTRL_INPUT_ROW, left - 1),
        (top + CTRL_OUTPUT_ROW, left - 1),
    )


def build_geometry_pipeline(*, annotate_dest: bool = False) -> str:
    stages = [
        (build_roomfind_room(), build_raw_fetch().render(), 13, 5),
        (build_perimeter_room(), build_compare_fetch_room(), 6, 9),
        (build_pipestarts_room(), build_candidate_fetch_room(), 6, 9),
        (
            (
                build_pipetrace_dest_room()
                if annotate_dest
                else build_pipetrace_room()
            ),
            build_candidate_fetch_room(),
            6,
            9,
        ),
    ]
    cv = Canvas()
    ports = []
    top = 0
    for ctrl, service, response_row, ring_in_row in stages:
        ports.append(
            _place_stage(
                cv,
                top,
                ctrl,
                service,
                service_resp_row=response_row,
                service_ring_in_row=ring_in_row,
            )
        )
        top += len(ctrl) + 10

    cv.put(1, 0, ["+-+", "|I|", "+-+"])
    cv.pipe([(2, 3), ports[0][0]])
    for index, (source, target) in enumerate(
        zip((port[1] for port in ports), (port[0] for port in ports[1:])),
        start=0,
    ):
        spine = 80 - index * 10
        cv.pipe([source, (source[0], spine), (target[0], spine), target])
    final_row = ports[-1][1][0]
    cv.put(final_row - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([ports[-1][1], (final_row, 3)])
    return cv.render()
