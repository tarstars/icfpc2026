"""Filter expanded room perimeters to actual outgoing pipe starts."""

from __future__ import annotations

from .lllm_fetch import build_relay
from .lllm_scan import _Fsm, _compile
from .llm_candidatefetch import (
    CMD_ROW as FETCH_CMD_ROW,
    RESP_ROW as FETCH_RESP_ROW,
    build_candidate_fetch_room,
    candidate_fetch_reference,
)
from .llm_perimeter import ROOM_END
from .llm_roomfind import SETUP_END, WORLD_WORDS


def pipestarts_reference(tokens: list[int]) -> list[int]:
    world = tokens[:WORLD_WORDS]
    out = list(world)
    index = WORLD_WORDS
    while tokens[index] != SETUP_END:
        out.extend(tokens[index : index + 5])
        index += 5
        candidates = []
        while tokens[index] != ROOM_END:
            candidates.append(tokens[index])
            index += 1
        verdicts = candidate_fetch_reference(world, candidates)
        out.extend(
            candidate
            for candidate, verdict in zip(candidates, verdicts, strict=True)
            if verdict == 0
        )
        out.append(ROOM_END)
        index += 1
    return [*out, SETUP_END, *tokens[index + 1 :]]


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "load_r_0")
    for index in range(WORLD_WORDS):
        next_name = f"load_r_{index + 1}" if index + 1 < WORLD_WORDS else "item_r"
        fsm.go(f"load_r_{index}", "left", "r", f"load_fetch_{index}")
        fsm.go(f"load_fetch_{index}", "right", "s", f"load_out_{index}")
        fsm.go(f"load_out_{index}", "left", "s", next_name)

    fsm.go("item_r", "left", "r", "item_cmp")
    fsm.sign(
        "item_cmp",
        "lit_l",
        "M`1000`+",
        neg="bad_item",
        zero="setup_end",
        pos="event_out",
    )
    fsm.go("bad_item", "left", "H", "bad_item")
    fsm.go("event_out", "left", "Ws", "tuple_r_0")
    for index in range(4):
        next_name = f"tuple_r_{index + 1}" if index < 3 else "candidate_r"
        fsm.go(f"tuple_r_{index}", "left", "r", f"tuple_s_{index}")
        fsm.go(f"tuple_s_{index}", "left", "s", next_name)

    fsm.sign(
        "candidate_r",
        "left",
        "r",
        neg="room_end",
        zero="bad_candidate",
        pos="candidate_send",
    )
    fsm.go("bad_candidate", "left", "H", "bad_candidate")
    fsm.go("candidate_send", "right", "Msr", "candidate_cmp")
    fsm.sign(
        "candidate_cmp",
        "mid",
        "",
        neg="candidate_skip",
        zero="candidate_match",
        pos="candidate_skip",
    )
    fsm.go("candidate_skip", "left", "", "candidate_r")
    fsm.go("candidate_match", "left", "Ws", "candidate_r")
    fsm.go("room_end", "left", "s", "item_r")

    fsm.go("setup_end", "left", "Ws", "relay_r")
    fsm.go("relay_r", "left", "r", "relay_s")
    fsm.go("relay_s", "left", "s", "relay_r")
    return fsm


def build_pipestarts_room() -> list[str]:
    return _compile(_build_fsm())


CTRL_LEFT = 5
CTRL_CMD_ROW, CTRL_RESP_ROW = 2, 9


def build_pipestarts_rig() -> str:
    from .canvas import Canvas

    ctrl = build_pipestarts_room()
    ctrl_right = CTRL_LEFT + len(ctrl[0]) - 1
    fetch_left = ctrl_right + 10
    fetch = build_candidate_fetch_room()
    fetch_right = fetch_left + len(fetch[0]) - 1
    relay_left = fetch_right + 5
    far = relay_left + 17
    cv = Canvas()
    cv.put(0, CTRL_LEFT, ctrl)
    cv.put(0, fetch_left, fetch)
    cv.put(20, relay_left, build_relay().render())
    cv.put(1, 0, ["+-+", "|I|", "+-+"])
    cv.put(5, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(2, 3), (2, CTRL_LEFT - 1)])
    cv.pipe([(6, CTRL_LEFT - 1), (6, 3)])
    cv.pipe([(CTRL_CMD_ROW, ctrl_right + 1), (CTRL_CMD_ROW, fetch_left - 1)])
    cv.pipe(
        [
            (FETCH_RESP_ROW, fetch_left - 1),
            (FETCH_RESP_ROW, ctrl_right + 4),
            (CTRL_RESP_ROW, ctrl_right + 4),
            (CTRL_RESP_ROW, ctrl_right + 1),
        ]
    )
    cv.pipe([(2, fetch_right + 1), (2, far), (21, far), (21, relay_left + 6)])
    cv.pipe([(21, relay_left - 1), (21, fetch_right + 2), (9, fetch_right + 2), (9, fetch_right + 1)])
    return cv.render()
