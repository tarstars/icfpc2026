"""LLM raw-grid SCAN: 256 cells, setup sentinel, then round relay."""

from __future__ import annotations

from .lllm_scan import (
    FETCH_W,
    LAP,
    _Fsm,
    _cell_bump,
    _compile,
    _prologue,
    build_relay,
)

DISPLAY = 16
CELLS = DISPLAY * DISPLAY
SPACE = 32
PADDING_BIT = 512
SETUP_END = -1


def scan_reference(tokens: list[int]) -> list[int]:
    """Preserve real chars (including every ``@``), pad, then relay."""
    width, height = tokens[:2]
    chars = iter(tokens[2 : 2 + width * height])
    cells = []
    for addr in range(CELLS):
        y, x = divmod(addr, DISPLAY)
        cells.append(
            SPACE + PADDING_BIT if x >= width or y >= height else next(chars)
        )
    return cells + [SETUP_END] + list(tokens[2 + width * height :])


def _raw_cell(fsm: _Fsm, tag: str, after: str) -> None:
    fsm.go(f"{tag}_r", "left", "rs", f"{tag}_a")
    _cell_bump(fsm, tag, after)


def _raw_row(fsm: _Fsm, tag: str, after: str) -> None:
    """Read W real cells, then emit ``544`` through column 15."""
    fsm.go(f"{tag}_w", "right", FETCH_W, f"{tag}_bp")
    fsm.go(f"{tag}_bp", "mid", "0+bmm", f"{tag}_x0_r")
    _raw_cell(fsm, f"{tag}_x0", f"{tag}_c_r")
    _raw_cell(fsm, f"{tag}_c", f"{tag}_lp")
    fsm.bp(f"{tag}_lp", "mid", "m", zero=f"{tag}_xw_r", pos=f"{tag}_c_r")
    _raw_cell(fsm, f"{tag}_xw", f"{tag}_w2")
    fsm.go(f"{tag}_w2", "right", FETCH_W, f"{tag}_lw")
    fsm.go(f"{tag}_lw", "mid", "0+", f"{tag}_bp4")
    fsm.go(f"{tag}_bp4", "lit_l", "M`0016`W-N", f"{tag}_seed4")
    fsm.go(f"{tag}_seed4", "mid", "Mb", f"{tag}_p4")
    fsm.bp(f"{tag}_p4", "mid", "", zero=f"{tag}_end", pos=f"{tag}_tail")
    fsm.go(f"{tag}_tail", "lit_l", " `0544`s", f"{tag}_step")
    fsm.go(f"{tag}_step", "mid", "m", f"{tag}_p4")
    fsm.go(f"{tag}_end", "right", "r+s" + "rs" * 4, after)


def _pad_row(fsm: _Fsm, tag: str, after: str) -> None:
    """Emit sixteen padding cells without consuming program input."""
    fsm.go(f"{tag}_w", "right", FETCH_W, f"{tag}_bp")
    fsm.go(f"{tag}_bp", "mid", "0+bmm", f"{tag}_x0")
    fsm.go(f"{tag}_x0", "lit_l", " `0544`s", f"{tag}_mid")
    fsm.go(f"{tag}_mid", "lit_l", " `0544`s", f"{tag}_lp")
    fsm.bp(f"{tag}_lp", "mid", "m", zero=f"{tag}_xw", pos=f"{tag}_mid")
    fsm.go(f"{tag}_xw", "lit_l", " `0544`s", f"{tag}_w2")
    fsm.go(f"{tag}_w2", "right", FETCH_W, f"{tag}_lw")
    fsm.go(f"{tag}_lw", "mid", "0+", f"{tag}_bp4")
    fsm.go(f"{tag}_bp4", "lit_l", "M`0016`W-N", f"{tag}_seed4")
    fsm.go(f"{tag}_seed4", "mid", "Mb", f"{tag}_p4")
    fsm.bp(f"{tag}_p4", "mid", "", zero=f"{tag}_end", pos=f"{tag}_tail")
    fsm.go(f"{tag}_tail", "lit_l", " `0544`s", f"{tag}_step")
    fsm.go(f"{tag}_step", "mid", "m", f"{tag}_p4")
    fsm.go(f"{tag}_end", "right", "rM", f"{tag}_bump")
    fsm.go(f"{tag}_bump", "lit_r", " `0016`+s" + "rs" * 4, after)


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    _prologue(fsm, "top_w")
    _raw_row(fsm, "top", "ilp_a")
    fsm.go("ilp_a", "right", LAP[:-1] + "M", "ilp_b")
    fsm.go("ilp_b", "lit_r", " `0001`W-s", "ilp_c")
    fsm.sign("ilp_c", "mid", "", neg="bot_w", zero="mid_w", pos="mid_w")
    _raw_row(fsm, "mid", "ilp_a")
    _raw_row(fsm, "bot", "plp_a")
    fsm.go("plp_a", "right", "rsrsrsrM", "plp_b")
    fsm.go("plp_b", "lit_r", " `0001`W-sMrs", "plp_c")
    fsm.sign("plp_c", "mid", "0+", neg="tail_a", zero="pad_w", pos="pad_w")
    _pad_row(fsm, "pad", "plp_a")
    fsm.go("tail_a", "right", "rsr", "tail_b")
    fsm.go("tail_b", "lit_l", " `0001`Ns", "relay")
    fsm.go("relay", "left", "rs", "relay")
    return fsm


def build_scan_room() -> list[str]:
    return _compile(_build_fsm())


SCAN_LEFT = 5
CMD_ROW, RESP_ROW = 2, 6
RING_OUT_ROW, RING_IN_ROW = 2, 9


def build_scan_rig() -> str:
    """I -> SCAN -> O plus the private five-token scratch ring."""
    from .canvas import Canvas

    room = build_scan_room()
    right = SCAN_LEFT + len(room[0]) - 1
    relay_left = right + 5
    far = relay_left + 8
    cv = Canvas()
    cv.put(0, SCAN_LEFT, room)
    cv.put(CMD_ROW - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(RESP_ROW - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(CMD_ROW, 3), (CMD_ROW, SCAN_LEFT - 1)])
    cv.pipe([(RESP_ROW, SCAN_LEFT - 1), (RESP_ROW, 3)])
    cv.put(1, relay_left, build_relay())
    cv.pipe([(RING_OUT_ROW, right + 1), (RING_OUT_ROW, relay_left - 1)])
    cv.pipe(
        [
            (3, relay_left + 6),
            (3, far),
            (RING_IN_ROW, far),
            (RING_IN_ROW, right + 1),
        ]
    )
    return cv.render()
