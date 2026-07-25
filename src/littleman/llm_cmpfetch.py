"""Raw-world FETCH with six fixed comparison request kinds."""

from __future__ import annotations

from .lllm_fetch import build_relay
from .lllm_scan import _Fsm, _compile
from .llm_rawfetch import CELLS, WORLD_TOKENS, unpack_raw_world

EXPECTED = (None, ord("|"), ord("^"), ord("v"), ord("<"), ord(">"), ord("-"))
KINDS = len(EXPECTED)


def compare_fetch_reference(world: list[int], requests: list[int]) -> list[int]:
    cells = unpack_raw_world(world)
    out = []
    for request in requests:
        kind, addr = divmod(request, CELLS)
        if not 0 <= kind < KINDS:
            raise ValueError(f"unknown compare kind {kind}")
        value = cells[addr]
        out.append(value if kind == 0 else value - EXPECTED[kind])
    return out


def _literal(value: int) -> str:
    return f" `{value:04d}`"


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "lit_l", "@`0064`b", "load_r")
    fsm.go("load_r", "left", "r", "load_s")
    fsm.go("load_s", "right", "s", "load_count")
    fsm.bp("load_count", "mid", "m", zero="marker", pos="load_r")
    fsm.go("marker", "lit_r", " `0001`Ns", "request")

    fsm.go("request", "left", "r", "decode")
    fsm.go("decode", "lit_l", "M`0256`W/b", "kind_0")
    for kind in range(KINDS):
        if kind + 1 < KINDS:
            fsm.bp(
                f"kind_{kind}",
                "mid",
                "",
                zero=f"chain_a_{kind}",
                pos=f"kind_dec_{kind}",
            )
            fsm.go(f"kind_dec_{kind}", "mid", "m", f"kind_{kind + 1}")
        else:
            fsm.go(f"kind_{kind}", "mid", "", f"chain_a_{kind}")
        fsm.go(
            f"chain_a_{kind}",
            "right",
            "WM8W+M4W/bWM",
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
        fsm.go(
            f"align_word_{kind}", "right", "s", f"align_{kind}"
        )
        fsm.go(
            f"align_marker_{kind}", "right", "s", f"rotate_{kind}"
        )
        fsm.bp(
            f"rotate_{kind}",
            "mid",
            "m",
            zero=f"peel_a_{kind}",
            pos=f"rotate_token_{kind}",
        )
        fsm.go(
            f"rotate_token_{kind}", "right", "rs", f"rotate_{kind}"
        )
        fsm.go(f"peel_a_{kind}", "right", "/M", f"peel_b_{kind}")
        target = "output" if kind == 0 else f"subtract_a_{kind}"
        fsm.go(f"peel_b_{kind}", "lit_r", " `1023`&", target)
        if kind:
            fsm.go(
                f"subtract_a_{kind}",
                "right",
                "M",
                f"subtract_b_{kind}",
            )
            fsm.go(
                f"subtract_b_{kind}",
                "lit_r",
                _literal(EXPECTED[kind]) + "W-",
                "output",
            )

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


def build_compare_fetch_room() -> list[str]:
    return _compile(_build_fsm())


FETCH_LEFT = 5
CMD_ROW, RESP_ROW = 2, 6
RING_OUT_ROW, RING_IN_ROW = 2, 9


def build_compare_fetch_rig() -> str:
    from .canvas import Canvas

    room = build_compare_fetch_room()
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
