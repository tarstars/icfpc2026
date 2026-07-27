"""Physical position-first room discovery for LLM."""

from __future__ import annotations

from .lllm_scan import _Fsm, _compile
from .llm_geom import discover_rooms
from .llm_rawfetch import (
    CMD_ROW as FETCH_CMD_ROW,
    RESP_ROW as FETCH_RESP_ROW,
    build_raw_fetch,
    unpack_raw_world,
)
from .lllm_fetch import build_relay

WORLD_WORDS = 64
SETUP_END = -1000


def roomfind_reference(tokens: list[int]) -> list[int]:
    """Relay the world, then emit ``event,left,right,top,bottom`` per man."""
    world = tokens[:WORLD_WORDS]
    end = tokens.index(SETUP_END, WORLD_WORDS)
    events = tokens[WORLD_WORDS:end]
    men = [-(event + 1) for event in events]
    rooms = discover_rooms(unpack_raw_world(world), men)
    out = list(world)
    for event, (top, left, bottom, right) in zip(events, rooms, strict=True):
        man = -(event + 1)
        man_row = man // 16
        out.extend(
            (
                event,
                man_row * 16 + left,
                man_row * 16 + right,
                top * 16 + left,
                bottom * 16 + left,
            )
        )
    return [*out, SETUP_END, *tokens[end + 1 :]]


def _literal(value: int) -> str:
    if value < 0:
        return f" `{-value:04d}`N"
    return f" `{value:04d}`"


def _compare_request(fsm: _Fsm, name: str, neg, zero, pos) -> None:
    fsm.sign(
        name,
        "lit_r",
        "M`0256`+sr",
        neg=neg,
        zero=zero,
        pos=pos,
    )


def _step(fsm: _Fsm, name: str, delta: int, target: str) -> None:
    if delta == -1:
        code = "M1W-"
    elif delta == 1:
        code = "M1+"
    elif delta == -16:
        code = "M`0016`W-"
    elif delta == 16:
        code = "M`0016`+"
    else:
        raise ValueError(delta)
    zone = "lit_r" if "`" in code else "right"
    fsm.go(name, zone, code, target)


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "load_r_0")
    for index in range(WORLD_WORDS):
        next_name = f"load_r_{index + 1}" if index + 1 < WORLD_WORDS else "event_r"
        fsm.go(f"load_r_{index}", "left", "r", f"load_raw_{index}")
        fsm.go(f"load_raw_{index}", "right", "s", f"load_out_{index}")
        fsm.go(f"load_out_{index}", "left", "s", next_name)

    fsm.go("event_r", "left", "r", "event_cmp")
    fsm.sign(
        "event_cmp",
        "lit_l",
        "M`1000`+",
        neg="bad_event",
        zero="setup_end",
        pos="man_decode",
    )
    fsm.go("bad_event", "left", "H", "bad_event")
    # Restore event from B, decode addr, re-encode/emit the event, restore addr.
    fsm.go("man_decode", "left", "WNM1W-M1+NsW", "left_seed")
    _step(fsm, "left_seed", -1, "left_query")
    _compare_request(fsm, "left_query", "left_more", "left_found", "left_more")
    fsm.go("left_more", "right", "W", "left_more_step")
    _step(fsm, "left_more_step", -1, "left_query")

    fsm.go("left_found", "left", "Ws", "right_seed")
    _step(fsm, "right_seed", 1, "right_query")
    _compare_request(fsm, "right_query", "right_more", "right_found", "right_more")
    fsm.go("right_more", "right", "W", "right_more_step")
    _step(fsm, "right_more_step", 1, "right_query")

    fsm.go("right_found", "left", "Ws", "left_again_seed")
    _step(fsm, "left_again_seed", -1, "left_again_query")
    _compare_request(
        fsm,
        "left_again_query",
        "left_again_more",
        "top_seed",
        "left_again_more",
    )
    fsm.go("left_again_more", "right", "W", "left_again_more_step")
    _step(fsm, "left_again_more_step", -1, "left_again_query")

    # At left border, zero response and B=left. Walk upward while cells are '|'.
    fsm.go("top_seed", "right", "W", "top_query")
    _compare_request(fsm, "top_query", "top_found", "top_more", "top_found")
    fsm.go("top_more", "right", "W", "top_more_step")
    _step(fsm, "top_more_step", -16, "top_query")
    fsm.go("top_found", "left", "Ws", "bottom_seed")
    _step(fsm, "bottom_seed", 16, "bottom_query")
    _compare_request(
        fsm, "bottom_query", "bottom_found", "bottom_more", "bottom_found"
    )
    fsm.go("bottom_more", "right", "W", "bottom_more_step")
    _step(fsm, "bottom_more_step", 16, "bottom_query")
    fsm.go("bottom_found", "left", "Ws", "event_r")

    fsm.go("setup_end", "left", "Ws", "relay_r")
    fsm.go("relay_r", "left", "r", "relay_s")
    fsm.go("relay_s", "left", "s", "relay_r")
    return fsm


def build_roomfind_room() -> list[str]:
    return _compile(_build_fsm())


CTRL_LEFT = 5
CTRL_CMD_ROW, CTRL_RESP_ROW = 2, 9


def build_roomfind_rig() -> str:
    from .canvas import Canvas

    ctrl = build_roomfind_room()
    ctrl_right = CTRL_LEFT + len(ctrl[0]) - 1
    fetch_left = ctrl_right + 10
    fetch = build_raw_fetch().render()
    relay_left = fetch_left + len(fetch[0]) + 4
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
    fetch_right = fetch_left + len(fetch[0]) - 1
    cv.pipe([(2, fetch_right + 1), (2, far), (21, far), (21, relay_left + 6)])
    cv.pipe(
        [
            (21, relay_left - 1),
            (21, fetch_right + 2),
            (5, fetch_right + 2),
            (5, fetch_right + 1),
        ]
    )
    return cv.render()
