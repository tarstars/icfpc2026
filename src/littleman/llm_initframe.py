"""Stream the rich LLM setup into a complete initial DRAW frame."""

from __future__ import annotations

from .lllm_scan import _compile, _Fsm, _layout
from .llm import COLOR_MAN, COLOR_PIPE, op_color
from .llm_perimeter import ROOM_END
from .llm_pipetrace import PIPE_END
from .llm_rawfetch import unpack_raw_world
from .llm_roomfind import SETUP_END, WORLD_WORDS
from .llm_wallgen import wallgen_reference

FRAME_END = -1


def initframe_reference(tokens: list[int]) -> list[int]:
    raw = unpack_raw_world(tokens[:WORLD_WORDS])
    out = [
        addr * 16 + op_color(" " if (value & 0xFF) == ord("@") else chr(value & 0xFF))
        for addr, value in enumerate(raw)
    ]
    index = WORLD_WORDS
    while tokens[index] != SETUP_END:
        event, left, right, top, bottom = tokens[index : index + 5]
        index += 5
        out.append(-(event + 1) * 16 + COLOR_MAN)
        out.extend(wallgen_reference([left, right, top, bottom])[:-1])
        while tokens[index] != ROOM_END:
            index += 1  # pipe-start descriptor is not a display cell
            while tokens[index] != PIPE_END:
                out.append(tokens[index] * 16 + COLOR_PIPE)
                index += 1
            index += 1
        index += 1
    return [*out, FRAME_END]


def _pack_delta(fsm: _Fsm, name: str, color: int, target: str) -> None:
    fsm.go(name, "right", "M", f"{name}_mul")
    fsm.go(f"{name}_mul", "lit_r", " `0016`W*M", f"{name}_color")
    fsm.go(f"{name}_color", "left", f"{color}+", target)


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "lit_l", "@`0064`b", "load_r")
    fsm.go("load_r", "left", "r", "load_fetch")
    fsm.go("load_fetch", "right", "s", "load_count")
    fsm.bp("load_count", "mid", "m", zero="base_seed", pos="load_r")

    fsm.go("base_seed", "lit_r", " `0256`b0M", "base_request")
    fsm.go("base_request", "right", "sr", "base_output")
    fsm.go("base_output", "left", "+sM", "base_mask")
    fsm.go("base_mask", "lit_r", " `0016`N", "base_align")
    fsm.go("base_align", "right", "W&M", "base_step")
    fsm.go("base_step", "lit_r", " `0016`+M", "base_count")
    fsm.bp("base_count", "mid", "m", zero="item_r", pos="base_request")

    fsm.go("item_r", "left", "r", "item_cmp")
    fsm.sign(
        "item_cmp",
        "lit_l",
        "M`1000`+",
        neg="bad_item",
        zero="setup_end",
        pos="man_restore",
    )
    fsm.go("bad_item", "left", "H", "bad_item")
    fsm.go("man_restore", "left", "WM1+N", "man_pack")
    _pack_delta(fsm, "man_pack", COLOR_MAN, "man_output")
    fsm.go("man_output", "left", "s", "tuple_r_0")

    for index in range(4):
        target = f"tuple_r_{index + 1}" if index < 3 else "wall_r"
        fsm.go(f"tuple_r_{index}", "left", "r", f"tuple_s_{index}")
        fsm.go(f"tuple_s_{index}", "right", "s", target)

    fsm.sign(
        "wall_r",
        "right",
        "r",
        neg="start_r",
        zero="wall_output",
        pos="wall_output",
    )
    fsm.go("wall_output", "left", "s", "wall_r")

    fsm.sign(
        "start_r",
        "left",
        "r",
        neg="room_end",
        zero="bad_start",
        pos="cell_r",
    )
    fsm.go("bad_start", "left", "H", "bad_start")
    fsm.sign(
        "cell_r",
        "left",
        "r",
        neg="start_r",
        zero="cell_pack",
        pos="cell_pack",
    )
    _pack_delta(fsm, "cell_pack", COLOR_PIPE, "cell_output")
    fsm.go("cell_output", "left", "s", "cell_r")
    fsm.go("room_end", "left", "", "item_r")
    fsm.go("setup_end", "left", "1NsH", "setup_end")
    return fsm


def build_initframe_room() -> list[str]:
    return _compile(_build_fsm())


def _phase_rows() -> tuple[int, int]:
    """Representative right-wall rows for COLORFETCH and WALLGEN."""
    fsm = _build_fsm()
    _routes, blocks, _height = _layout(fsm)
    color = [
        row
        for name, row in blocks.items()
        if name.startswith(("load_fetch", "base_request"))
    ]
    wall = [
        row for name, row in blocks.items() if name.startswith(("tuple_s_", "wall_r"))
    ]
    return (max(color), min(wall))


def _route_service(
    cv,
    ctrl_right: int,
    service_left: int,
    service_top: int,
    service: list[str],
    phase_row: int,
) -> None:
    """Connect one phased request/response service and its private ring."""
    from .lllm_fetch import build_relay

    service_right = service_left + len(service[0]) - 1
    relay_left = service_right + 5
    far = relay_left + 17
    cmd = phase_row
    resp = phase_row + 4
    service_below = service_top + 2 > cmd
    cmd_track = ctrl_right + (4 if service_below else 2)
    resp_track = ctrl_right + (2 if service_below else 4)
    cv.put(service_top + 20, relay_left, build_relay().render())
    cv.pipe(
        [
            (cmd, ctrl_right + 1),
            (cmd, cmd_track),
            (service_top + 2, cmd_track),
            (service_top + 2, service_left - 1),
        ]
    )
    cv.pipe(
        [
            (service_top + 6, service_left - 1),
            (service_top + 6, resp_track),
            (resp, resp_track),
            (resp, ctrl_right + 1),
        ]
    )
    cv.pipe(
        [
            (service_top + 2, service_right + 1),
            (service_top + 2, far),
            (service_top + 21, far),
            (service_top + 21, relay_left + 6),
        ]
    )
    cv.pipe(
        [
            (service_top + 21, relay_left - 1),
            (service_top + 21, service_right + 2),
            (service_top + 9, service_right + 2),
            (service_top + 9, service_right + 1),
        ]
    )


CTRL_LEFT = 5
INPUT_ROW, OUTPUT_ROW = 2, 6


def build_initframe_rig() -> str:
    """Rich setup at I -> packed initial-frame deltas at O."""
    from .canvas import Canvas
    from .llm_colorfetch import build_colorfetch_room
    from .llm_wallgen import build_wallgen_room

    ctrl = build_initframe_room()
    ctrl_right = CTRL_LEFT + len(ctrl[0]) - 1
    service_left = ctrl_right + 10
    color = build_colorfetch_room()
    wall = build_wallgen_room()
    color_row, wall_row = _phase_rows()
    color_top = 0
    wall_top = max(len(color) + 10, wall_row - 2)
    cv = Canvas()
    cv.put(0, CTRL_LEFT, ctrl)
    cv.put(color_top, service_left, color)
    cv.put(wall_top, service_left, wall)
    cv.put(INPUT_ROW - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(OUTPUT_ROW - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(INPUT_ROW, 3), (INPUT_ROW, CTRL_LEFT - 1)])
    cv.pipe([(OUTPUT_ROW, CTRL_LEFT - 1), (OUTPUT_ROW, 3)])

    _route_service(cv, ctrl_right, service_left, color_top, color, color_row)
    _route_service(cv, ctrl_right, service_left, wall_top, wall, wall_row)
    return cv.render()
