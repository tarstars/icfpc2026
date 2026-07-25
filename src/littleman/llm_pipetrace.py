"""Trace filtered LLM pipe starts into source-to-destination cell lists."""

from __future__ import annotations

from .lllm_fetch import build_relay
from .lllm_scan import _Fsm, _compile
from .llm_candidatefetch import (
    CMD_ROW as FETCH_CMD_ROW,
    RESP_ROW as FETCH_RESP_ROW,
    build_candidate_fetch_room,
)
from .llm_cmpfetch import EXPECTED
from .llm_perimeter import ROOM_END, pack_candidate, unpack_candidate
from .llm_roomfind import SETUP_END, WORLD_WORDS
from .llm_rawfetch import unpack_raw_world

PIPE_END = -3000
DIRECTION_DELTA = {2: -16, 3: 16, 4: -1, 5: 1}


def pipetrace_reference(tokens: list[int]) -> list[int]:
    raw = unpack_raw_world(tokens[:WORLD_WORDS])
    out = list(tokens[:WORLD_WORDS])
    index = WORLD_WORDS
    while tokens[index] != SETUP_END:
        out.extend(tokens[index : index + 5])
        index += 5
        while tokens[index] != ROOM_END:
            start = tokens[index]
            index += 1
            direction, addr = unpack_candidate(start)
            out.append(start)
            while 0 <= addr < 256:
                code = raw[addr] & 0xFF
                arrow = next(
                    (kind for kind in range(2, 6) if code == EXPECTED[kind]),
                    None,
                )
                body = 1 if direction in (2, 3) else 6
                if arrow is not None:
                    direction = arrow
                elif code != EXPECTED[body]:
                    break
                out.append(addr)
                addr += DIRECTION_DELTA[direction]
            out.append(PIPE_END)
        out.append(ROOM_END)
        index += 1
    return [*out, SETUP_END, *tokens[index + 1 :]]


def _literal(value: int) -> str:
    return f" `{-value:04d}`N" if value < 0 else f" `{value:04d}`"


def _step(fsm: _Fsm, name: str, delta: int, target: str) -> None:
    if abs(delta) == 1:
        code = "M1+" if delta > 0 else "M1W-"
        zone = "right"
    else:
        code = f"M`{abs(delta):04d}`" + ("+" if delta > 0 else "W-")
        zone = "lit_r"
    fsm.go(name, zone, code, target)


def _probe(fsm: _Fsm, direction: int, kind: int, next_kind: int | None) -> None:
    name = f"probe_{direction}_{kind}"
    match = f"match_{direction}_{kind}"
    miss = (
        f"probe_restore_{direction}_{next_kind}"
        if next_kind is not None
        else "pipe_end"
    )
    fsm.sign(
        name,
        "lit_r",
        f"M`{kind * 1024 + 256:04d}`+sr",
        neg=miss,
        zero=match,
        pos=miss,
    )
    new_direction = kind if 2 <= kind <= 5 else direction
    fsm.go(match, "left", "Ws", f"step_{new_direction}")
    if next_kind is not None:
        fsm.go(miss, "right", "W", f"probe_{direction}_{next_kind}")


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
        next_name = f"tuple_r_{index + 1}" if index < 3 else "start_r"
        fsm.go(f"tuple_r_{index}", "left", "r", f"tuple_s_{index}")
        fsm.go(f"tuple_s_{index}", "left", "s", next_name)

    fsm.sign(
        "start_r",
        "left",
        "r",
        neg="room_end",
        zero="bad_start",
        pos="start_out",
    )
    fsm.go("bad_start", "left", "H", "bad_start")
    fsm.go("start_out", "left", "s", "start_decode")
    fsm.go("start_decode", "lit_l", "M`1024`W/b", "start_kind_0")
    for kind in range(6):
        if kind < 5:
            fsm.bp(
                f"start_kind_{kind}",
                "mid",
                "",
                zero=f"start_arm_{kind}",
                pos=f"start_kind_dec_{kind}",
            )
            fsm.go(
                f"start_kind_dec_{kind}", "mid", "m", f"start_kind_{kind + 1}"
            )
        else:
            fsm.go(f"start_kind_{kind}", "mid", "", f"start_arm_{kind}")
        if kind < 2:
            fsm.go(f"start_arm_{kind}", "mid", "", "bad_start")
        else:
            fsm.go(
                f"start_arm_{kind}", "right", "W", f"start_shift_{kind}"
            )
            fsm.go(
                f"start_shift_{kind}",
                "lit_r",
                "M`0256`W-",
                f"probe_{kind}_2",
            )

    for direction in range(2, 6):
        body = 1 if direction in (2, 3) else 6
        order = [2, 3, 4, 5, body]
        for offset, kind in enumerate(order):
            next_kind = order[offset + 1] if offset + 1 < len(order) else None
            _probe(fsm, direction, kind, next_kind)

    for direction, delta in DIRECTION_DELTA.items():
        _step(fsm, f"step_{direction}", delta, f"probe_{direction}_2")

    fsm.go("pipe_end", "lit_l", _literal(PIPE_END) + "s", "start_r")
    fsm.go("room_end", "left", "s", "item_r")
    fsm.go("setup_end", "left", "Ws", "relay_r")
    fsm.go("relay_r", "left", "r", "relay_s")
    fsm.go("relay_s", "left", "s", "relay_r")
    return fsm


def build_pipetrace_room() -> list[str]:
    return _compile(_build_fsm())


CTRL_LEFT = 5
CTRL_CMD_ROW, CTRL_RESP_ROW = 2, 9


def build_pipetrace_rig() -> str:
    from .canvas import Canvas

    ctrl = build_pipetrace_room()
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
