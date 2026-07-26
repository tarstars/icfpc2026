"""Select the nearest of two LLM pipe slots after eligibility filtering."""

from __future__ import annotations

from .canvas import Canvas
from .lllm_fetch import build_relay
from .lllm_scan import _compile, _Fsm
from .llm_bindscore import bindscore_reference, build_bindscore_room

REQUEST_WORDS = 5


def selecteligible_reference(tokens: list[int]) -> list[int]:
    """Consume ``man, eligible0, eligible1, target0, target1`` records."""
    if len(tokens) % REQUEST_WORDS:
        raise ValueError("truncated eligible-selection request")
    out = []
    for index in range(0, len(tokens), REQUEST_WORDS):
        man, eligible0, eligible1, target0, target1 = tokens[
            index : index + REQUEST_WORDS
        ]
        eligible = [bool(eligible0), bool(eligible1)]
        if not any(eligible):
            raise ValueError("selection request has no eligible pipe")
        scores = bindscore_reference([man, target0, man, target1])
        out.append(
            min(
                (slot for slot in range(2) if eligible[slot]),
                key=lambda slot: (scores[slot], slot),
            )
        )
    return out


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "man_r")
    fsm.go("man_r", "left", "rM", "eligible0_r")
    fsm.sign(
        "eligible0_r",
        "left",
        "r",
        neg="bad_request",
        zero="eligible1_without0",
        pos="eligible1_with0",
    )
    fsm.sign(
        "eligible1_without0",
        "left",
        "r",
        neg="bad_request",
        zero="bad_request",
        pos="only1",
    )
    fsm.sign(
        "eligible1_with0",
        "left",
        "r",
        neg="bad_request",
        zero="only0",
        pos="both_target0",
    )
    fsm.go("bad_request", "left", "H", "bad_request")
    fsm.go("only0", "left", "rr0s", "man_r")
    fsm.go("only1", "left", "rr1s", "man_r")

    fsm.go("both_target0", "left", "r", "request0")
    fsm.go("request0", "right", "WsWs", "both_target1")
    fsm.go("both_target1", "left", "r", "request1")
    fsm.go("request1", "right", "WsWs", "score0_r")
    fsm.go("score0_r", "right", "rM", "score1_r")
    fsm.go("score1_r", "right", "r-", "score_cmp")
    fsm.sign(
        "score_cmp",
        "right",
        "",
        neg="select1",
        zero="select0",
        pos="select0",
    )
    fsm.go("select0", "left", "0s", "man_r")
    fsm.go("select1", "left", "1s", "man_r")
    return fsm


def build_selecteligible_room() -> list[str]:
    return _compile(_build_fsm())


CTRL_LEFT = 5
INPUT_ROW, OUTPUT_ROW = 2, 6
CTRL_CMD_ROW, CTRL_RESP_ROW = 2, 9


def build_selecteligible_rig() -> str:
    ctrl = build_selecteligible_room()
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
