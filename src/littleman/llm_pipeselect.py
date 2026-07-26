"""Select the nearest of one or two eligible LLM pipe endpoints."""

from __future__ import annotations

from .canvas import Canvas
from .lllm_fetch import build_relay
from .lllm_scan import _compile, _Fsm
from .llm_bindscore import bindscore_reference, build_bindscore_room


def pipeselect_reference(tokens: list[int]) -> list[int]:
    """Consume repeated ``man_addr, count, endpoint...`` requests."""
    out = []
    index = 0
    while index < len(tokens):
        man, count = tokens[index : index + 2]
        index += 2
        if count not in (1, 2):
            raise ValueError(f"candidate count must be one or two: {count}")
        endpoints = tokens[index : index + count]
        if len(endpoints) != count:
            raise ValueError("truncated pipe-selection request")
        index += count
        scores = bindscore_reference(
            [item for endpoint in endpoints for item in (man, endpoint)]
        )
        out.append(min(range(count), key=lambda slot: (scores[slot], slot)))
    return out


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "addr_r")
    fsm.go("addr_r", "left", "rM", "count_r")
    fsm.go("count_r", "left", "rb", "target0_r")
    fsm.go("target0_r", "left", "r", "request0")
    fsm.go("request0", "right", "WsWsm", "count_branch")
    fsm.bp(
        "count_branch",
        "mid",
        "",
        zero="single_score_drop",
        pos="target1_r",
    )

    fsm.go("single_score_drop", "right", "r", "select0_single")
    fsm.go("select0_single", "left", "0s", "addr_r")

    fsm.go("target1_r", "left", "r", "request1")
    fsm.go("request1", "right", "WsWs", "score0_r")
    fsm.go("score0_r", "right", "rM", "score1_r")
    fsm.go("score1_r", "right", "r-", "score_branch")
    fsm.sign(
        "score_branch",
        "right",
        "",
        neg="select1",
        zero="select0",
        pos="select0",
    )
    fsm.go("select1", "left", "1s", "addr_r")
    fsm.go("select0", "left", "0s", "addr_r")
    return fsm


def build_pipeselect_room() -> list[str]:
    return _compile(_build_fsm())


CTRL_LEFT = 5
INPUT_ROW, OUTPUT_ROW = 2, 6
CTRL_CMD_ROW, CTRL_RESP_ROW = 2, 9


def build_pipeselect_rig() -> str:
    ctrl = build_pipeselect_room()
    ctrl_right = CTRL_LEFT + len(ctrl[0]) - 1
    service_left = ctrl_right + 10
    service = build_bindscore_room()
    service_right = service_left + len(service[0]) - 1
    relay_left = service_right + 5
    far = relay_left + 17
    cv = Canvas()
    cv.put(0, CTRL_LEFT, ctrl)
    cv.put(0, service_left, service)
    cv.put(20, relay_left, build_relay().render())
    cv.put(INPUT_ROW - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(OUTPUT_ROW - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(INPUT_ROW, 3), (INPUT_ROW, CTRL_LEFT - 1)])
    cv.pipe([(OUTPUT_ROW, CTRL_LEFT - 1), (OUTPUT_ROW, 3)])
    cv.pipe([(CTRL_CMD_ROW, ctrl_right + 1), (CTRL_CMD_ROW, service_left - 1)])
    cv.pipe(
        [
            (6, service_left - 1),
            (6, ctrl_right + 4),
            (CTRL_RESP_ROW, ctrl_right + 4),
            (CTRL_RESP_ROW, ctrl_right + 1),
        ]
    )
    cv.pipe(
        [
            (2, service_right + 1),
            (2, far),
            (21, far),
            (21, relay_left + 6),
        ]
    )
    cv.pipe(
        [
            (21, relay_left - 1),
            (21, service_right + 2),
            (9, service_right + 2),
            (9, service_right + 1),
        ]
    )
    return cv.render()
