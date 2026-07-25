"""Compact re-placement of the LLLM machine: 141x775 -> ~306x312.

Every room is LIFTED byte-identical from lllm_assemble's component calls and
moved RIGIDLY; only the four cluster origins and the inter-cluster pipe
routing change.  Three column bands instead of four row bands:

    band A cols   0..100  I, SCAN, SCAN relay      rows   6..311
    band B cols 110..195  CLASSIFY (rows 6..190), DIST/drivers/display (206..231)
    band C cols 213..305  FETCH + relay, STEP + relay   rows 6..185

Free corridors: row 0 (SCAN->CLASSIFY eastbound), col 1, col 108, col 210
(CLASSIFY->STEP), col 212 + row 200 (STEP->DIST).
"""

from __future__ import annotations

from .canvas import Canvas

SCAN_AT = (6, 6)
I_AT = (2, 96)
CLASSIFY_AT = (6, 110)
STEP_BASE = (6, 204)
DRAW_AT = (250, 110)

COL_REQ_REL = 9        # was absolute 9 with STEP_BASE col 0
COL_W = 1              # SCAN out, northbound
ROW_TOP = 0            # SCAN out, eastbound
COL_CLS_IN = 108       # SCAN out / STEP->DIST, southbound into a west wall
COL_LOAD = 210         # CLASSIFY -> STEP, southbound
COL_DRAW = 212         # STEP -> DIST, northbound (west of the REQ column)
ROW_DRAW_N = 5         # ... then east, north of every room (band C starts at 6)
COL_DRAW_E = 307       # ... then south, east of the whole STEP cluster
ROW_DRAW_S = 230       # ... then west, below CLASSIFY and above DIST
COL_DIST_IN = 108      # ... then south into DIST's west wall


def build_machine() -> str:
    from . import lllm_classify, lllm_draw, lllm_fetch, lllm_scan, lllm_step

    cv = Canvas()
    _place_scan(cv, lllm_scan)
    cv.put(*CLASSIFY_AT, lllm_classify.build_classify_room())
    _place_step_complex(cv, lllm_fetch, lllm_step)
    lllm_draw.place_display_block(cv, *DRAW_AT)
    _route_spine(cv, lllm_step, lllm_classify)
    return cv.render()


def _place_scan(cv: Canvas, mod) -> None:
    """SCAN + its private scratch ring; I moved north-east of the room."""
    r0, c0 = SCAN_AT
    room = mod.build_scan_room()
    right = c0 + len(room[0]) - 1
    cv.put(r0, c0, room)
    ir, ic = I_AT
    cv.put(ir, ic, ["+-+", "|I|", "+-+"])
    cv.pipe([(ir + 1, ic - 1), (ir + 1, 2), (r0 + mod.CMD_ROW, 2),
             (r0 + mod.CMD_ROW, c0 - 1)])
    relay_left = right + 5
    cv.put(r0 + 1, relay_left, mod.build_relay())
    cv.pipe([(r0 + mod.RING_OUT_ROW, right + 1), (r0 + mod.RING_OUT_ROW,
                                                  relay_left - 1)])
    far = relay_left + 8
    cv.pipe([(r0 + 3, relay_left + 6), (r0 + 3, far),
             (r0 + mod.RING_IN_ROW, far), (r0 + mod.RING_IN_ROW, right + 1)])


def _place_step_complex(cv: Canvas, fetch_mod, step_mod) -> None:
    """Rigid copy of lllm_assemble._place_step_complex, base-relative."""
    br, bc = STEP_BASE
    sr, sc = br + step_mod.STEP_AT[0], bc + step_mod.STEP_AT[1]
    fr, fc = br + step_mod.FETCH_AT[0], bc + step_mod.FETCH_AT[1]
    cv.put(fr, fc, fetch_mod.build_fetch().render())
    cv.put(sr, sc, step_mod.build_step_room().render())
    cv.put(fr + 20, fc + 50, fetch_mod.build_relay().render())
    cv.put(sr + step_mod.SCR_OUT_ROW - 1, sc + 80,
           step_mod.build_step_relay().render())
    left, right = sc - 1, sc + step_mod.STEP_COLS + 2
    fleft = fc - 1
    col_req = bc + COL_REQ_REL
    cv.pipe([(sr + step_mod.REQ_ROW, left), (sr + step_mod.REQ_ROW, col_req),
             (fr + 2, col_req), (fr + 2, fleft)])
    cv.pipe([(fr + 13, fleft), (fr + 13, fleft - 1), (sr - 1, fleft - 1),
             (sr - 1, sc + step_mod.RESP_COL)])
    cv.cells[(sr - 1, sc + step_mod.RESP_COL)] = "v"
    cv.pipe([(fr + 2, fc + 47), (fr + 2, fc + 67), (fr + 21, fc + 67),
             (fr + 21, fc + 56)])
    cv.pipe([(fr + 21, fc + 49), (fr + 21, fc + 48), (fr + 5, fc + 48),
             (fr + 5, fc + 47)])
    cv.pipe([(sr + step_mod.SCR_OUT_ROW, right), (sr + step_mod.SCR_OUT_ROW,
                                                  sc + 79)])
    cv.pipe([(sr + step_mod.SCR_OUT_ROW + 1, sc + 86),
             (sr + step_mod.SCR_OUT_ROW + 1, sc + 87),
             (sr + step_mod.SCR_IN_ROW, sc + 87), (sr + step_mod.SCR_IN_ROW,
                                                   right)])


def _route_spine(cv: Canvas, step_mod, cls_mod) -> None:
    sr0, sc0 = SCAN_AT
    cr0, cc0 = CLASSIFY_AT
    br, bc = STEP_BASE
    sr, sc = br + step_mod.STEP_AT[0], bc + step_mod.STEP_AT[1]
    left = sc - 1
    cls_row = cr0 + cls_mod.PIPE_ROW
    cls_right = cc0 + 86
    # SCAN -> CLASSIFY: west, north to row 0, east, south into the west wall
    cv.pipe([(sr0 + 6, sc0 - 1), (sr0 + 6, COL_W), (ROW_TOP, COL_W),
             (ROW_TOP, COL_CLS_IN), (cls_row, COL_CLS_IN), (cls_row, cc0 - 1)])
    # CLASSIFY -> STEP: east, south, east into STEP's LOAD row
    cv.pipe([(cls_row, cls_right), (cls_row, COL_LOAD),
             (sr + step_mod.LOAD_ROW, COL_LOAD), (sr + step_mod.LOAD_ROW, left)])
    # STEP -> DIST: west, north over the machine, east around the STEP cluster,
    # south, west below CLASSIFY, south into DIST's west wall.  The northern
    # detour is what lets it clear the CLASSIFY -> STEP pipe, which lands on
    # STEP's west wall one row below where this one leaves it.
    cv.pipe([(sr + step_mod.DRAW_ROW, left), (sr + step_mod.DRAW_ROW, COL_DRAW),
             (ROW_DRAW_N, COL_DRAW), (ROW_DRAW_N, COL_DRAW_E),
             (ROW_DRAW_S, COL_DRAW_E), (ROW_DRAW_S, COL_DIST_IN),
             (DRAW_AT[0] + 2, COL_DIST_IN), (DRAW_AT[0] + 2, DRAW_AT[1] - 1)])


def room_anchors() -> dict[tuple[int, int], str]:
    from . import lllm_step

    br, bc = STEP_BASE
    sr, sc = br + lllm_step.STEP_AT[0], bc + lllm_step.STEP_AT[1]
    fr, fc = br + lllm_step.FETCH_AT[0], bc + lllm_step.FETCH_AT[1]
    dr, dc = DRAW_AT
    return {
        I_AT: "I",
        SCAN_AT: "SCAN",
        (SCAN_AT[0] + 1, SCAN_AT[1] + 86): "SCANRELAY",
        CLASSIFY_AT: "CLASSIFY",
        (fr, fc): "FETCH",
        (fr + 20, fc + 50): "FETCHRELAY",
        (sr, sc): "STEP",
        (sr + lllm_step.SCR_OUT_ROW - 1, sc + 80): "STEPRELAY",
        (dr, dc): "DIST",
        (dr - 7, dc + 18): "ADDRDRV",
        (dr, dc + 19): "DATADRV",
        (dr + 7, dc + 20): "SWAPDRV",
        (dr - 3, dc + 46): "DISPLAY",
    }


if __name__ == "__main__":  # pragma: no cover
    import pathlib

    out = pathlib.Path("submissions/lllm/lllm_03.man")
    text = build_machine()
    out.write_text(text)
    print(f"wrote {out} ({len(text.encode())} bytes)")
