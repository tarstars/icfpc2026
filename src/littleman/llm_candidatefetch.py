"""Validate robust perimeter candidates against the packed raw world."""

from __future__ import annotations

from .lllm_fetch import build_relay
from .lllm_scan import _Fsm, _compile
from .llm_cmpfetch import EXPECTED
from .llm_perimeter import unpack_candidate
from .llm_rawfetch import unpack_raw_world

WORLD_TOKENS = 64
MAX_KIND = 6


def candidate_fetch_reference(world: list[int], candidates: list[int]) -> list[int]:
    cells = unpack_raw_world(world)
    out = []
    for candidate in candidates:
        kind, neighbor = unpack_candidate(candidate)
        if kind < 1 or kind > MAX_KIND or not 0 <= neighbor < 256:
            out.append(1)
        else:
            out.append(cells[neighbor] - EXPECTED[kind])
    return out


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "lit_l", "@`0064`b", "load_r")
    fsm.go("load_r", "left", "r", "load_s")
    fsm.go("load_s", "right", "s", "load_count")
    fsm.bp("load_count", "mid", "m", zero="marker", pos="load_r")
    fsm.go("marker", "lit_r", " `0001`Ns", "request")

    fsm.go("request", "left", "r", "decode")
    fsm.go("decode", "lit_l", "M`1024`W/b", "kind_0")
    for kind in range(MAX_KIND + 1):
        if kind < MAX_KIND:
            fsm.bp(
                f"kind_{kind}",
                "mid",
                "",
                zero=f"arm_{kind}",
                pos=f"kind_dec_{kind}",
            )
            fsm.go(f"kind_dec_{kind}", "mid", "m", f"kind_{kind + 1}")
        else:
            fsm.go(f"kind_{kind}", "mid", "", f"arm_{kind}")

        if kind < 1:
            fsm.go(f"arm_{kind}", "mid", "", "invalid")
            continue
        fsm.go(f"arm_{kind}", "right", "W", f"shift_{kind}")
        fsm.go(
            f"shift_{kind}",
            "lit_r",
            "M`0256`W-",
            f"low_{kind}",
        )
        fsm.sign(
            f"low_{kind}",
            "mid",
            "",
            neg="invalid",
            zero=f"upper_{kind}",
            pos=f"upper_{kind}",
        )
        fsm.sign(
            f"upper_{kind}",
            "lit_r",
            "M`0256`W-",
            neg=f"valid_{kind}",
            zero="invalid",
            pos="invalid",
        )
        fsm.go(f"valid_{kind}", "right", "+", f"chain_a_{kind}")
        fsm.go(
            f"chain_a_{kind}",
            "right",
            "M8W+M4W/bWM",
            f"chain_b_{kind}",
        )
        fsm.go(
            f"chain_b_{kind}",
            "lit_r",
            " `0010`*M1{M",
            f"align_{kind}",
        )
        fsm.sign(
            f"align_{kind}",
            "right",
            "r",
            neg=f"align_marker_{kind}",
            zero=f"align_word_{kind}",
            pos=f"align_word_{kind}",
        )
        fsm.go(f"align_word_{kind}", "right", "s", f"align_{kind}")
        fsm.go(f"align_marker_{kind}", "right", "s", f"rotate_{kind}")
        fsm.bp(
            f"rotate_{kind}",
            "mid",
            "m",
            zero=f"peel_a_{kind}",
            pos=f"rotate_token_{kind}",
        )
        fsm.go(f"rotate_token_{kind}", "right", "rs", f"rotate_{kind}")
        fsm.go(f"peel_a_{kind}", "right", "/M", f"peel_b_{kind}")
        fsm.go(
            f"peel_b_{kind}",
            "lit_r",
            " `1023`&",
            f"subtract_a_{kind}",
        )
        fsm.go(f"subtract_a_{kind}", "right", "M", f"subtract_b_{kind}")
        fsm.go(
            f"subtract_b_{kind}",
            "lit_r",
            f" `{EXPECTED[kind]:04d}`W-",
            "output",
        )

    fsm.go("invalid", "lit_l", " `0001`s", "request")
    fsm.go("output", "left", "s", "restore")
    fsm.sign(
        "restore",
        "right",
        "r",
        neg="restore_marker",
        zero="restore_word",
        pos="restore_word",
    )
    fsm.go("restore_word", "right", "s", "restore")
    fsm.go("restore_marker", "right", "s", "request")
    return fsm


def build_candidate_fetch_room() -> list[str]:
    return _compile(_build_fsm())


FETCH_LEFT = 5
CMD_ROW, RESP_ROW = 2, 6
RING_OUT_ROW, RING_IN_ROW = 2, 9


def build_candidate_fetch_rig() -> str:
    from .canvas import Canvas

    room = build_candidate_fetch_room()
    right = FETCH_LEFT + len(room[0]) - 1
    relay_left = right + 5
    far = relay_left + 17
    cv = Canvas()
    cv.put(0, FETCH_LEFT, room)
    cv.put(20, relay_left, build_relay().render())
    cv.put(CMD_ROW - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(RESP_ROW - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(CMD_ROW, 3), (CMD_ROW, FETCH_LEFT - 1)])
    cv.pipe([(RESP_ROW, FETCH_LEFT - 1), (RESP_ROW, 3)])
    cv.pipe([(RING_OUT_ROW, right + 1), (RING_OUT_ROW, far), (21, far), (21, relay_left + 6)])
    cv.pipe([(21, relay_left - 1), (21, right + 2), (RING_IN_ROW, right + 2), (RING_IN_ROW, right + 1)])
    return cv.render()
