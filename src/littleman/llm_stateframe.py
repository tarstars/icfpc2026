"""Render a normalized LLM state as color/address update pairs."""

from __future__ import annotations

from .canvas import Canvas
from .lllm_scan import _compile, _Fsm, _layout
from .llm import COLOR_MAN, COLOR_PIPE, COLOR_PIPE_FULL, op_color
from .llm_colorfetch import build_colorfetch_room
from .llm_perimeter import ROOM_END
from .llm_pipeframe import build_pipeframe_room
from .llm_pipetrace import PIPE_END
from .llm_rawfetch import unpack_raw_world
from .llm_roomfind import SETUP_END, WORLD_WORDS
from .llm_statebuild import PIPE_MASK, PIPE_VALUES
from .llm_wallgen import build_wallgen_room, wallgen_reference

FRAME_END = -1


def stateframe_reference(
    tokens: list[int],
    *,
    include_static: bool = True,
) -> list[int]:
    """Emit repeated ``color, address`` pairs followed by :data:`FRAME_END`."""
    raw = unpack_raw_world(tokens[:WORLD_WORDS])
    out = []
    if include_static:
        for addr, value in enumerate(raw):
            char = " " if value & 0xFF == ord("@") else chr(value & 0xFF)
            out.extend((op_color(char), addr))

    index = WORLD_WORDS
    while tokens[index] != SETUP_END:
        fields = tokens[index : index + 10]
        index += 10
        if include_static:
            for packed in wallgen_reference(fields[1:5])[:-1]:
                addr, color = divmod(packed, 16)
                out.extend((color, addr))
        out.extend((COLOR_MAN, fields[6]))
        if fields[9] != fields[6]:
            value = raw[fields[9]]
            char = " " if value & 0xFF == ord("@") else chr(value & 0xFF)
            out.extend((op_color(char), fields[9]))
        while tokens[index] != ROOM_END:
            index += 1
            pairs = []
            while tokens[index] != PIPE_MASK:
                pairs.append(tuple(tokens[index : index + 2]))
                index += 2
            mask = tokens[index + 1]
            index += 2
            assert tokens[index] == PIPE_VALUES
            count = tokens[index + 1]
            index += 2 + count
            assert tokens[index] == PIPE_END
            index += 1
            for cell, bit in pairs[:-1]:  # final pair is destination marker/address
                out.extend((COLOR_PIPE_FULL if mask & bit else COLOR_PIPE, cell))
        index += 1
    return [*out, FRAME_END]


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "lit_l", "@`0064`b", "load_r")
    fsm.go("load_r", "left", "r", "load_s")
    fsm.go("load_s", "right", "s", "load_count")
    fsm.bp("load_count", "mid", "m", zero="base_seed", pos="load_r")

    # COLORFETCH requests are packed addresses (addr*16). Return one
    # color/address pair and reconstruct the next packed address.
    fsm.go("base_seed", "lit_r", " `0256`b0M", "base_request")
    fsm.go("base_request", "right", "sr", "base_color_out")

    # Keep the later-frame restore lookup physically beside base_request.
    # Both paths are sequential, so they can safely share COLORFETCH's single
    # command/response pipe pair.  Defining these blocks near the service
    # port is essential: their logical targets do not constrain placement.
    fsm.go("old_restore", "right", "+M", "old_pack")
    fsm.go("old_pack", "lit_r", " `0016`W*M", "old_request")
    fsm.go("old_request", "right", "sr", "old_color_out")
    fsm.go("old_color_out", "left", "sW", "old_addr_prepare")
    fsm.go("old_addr_prepare", "right", "M", "old_addr_div")
    fsm.go("old_addr_div", "lit_r", " `0016`W/", "old_addr_out")
    fsm.go("old_addr_out", "left", "s", "start_r")

    fsm.go("base_color_out", "left", "sW", "base_addr_prepare")
    fsm.go("base_addr_prepare", "right", "M", "base_addr_div")
    fsm.go("base_addr_div", "lit_r", " `0016`W/", "base_addr_out")
    fsm.go("base_addr_out", "left", "sM1+M", "base_next_mul")
    fsm.go("base_next_mul", "lit_r", " `0016`*M", "base_count")
    fsm.bp("base_count", "mid", "m", zero="item_r", pos="base_request")

    fsm.go("item_r", "left", "r", "item_cmp")
    fsm.sign(
        "item_cmp",
        "lit_l",
        "M`1000`+",
        neg="bad_item",
        zero="frame_end",
        pos="bound_r_0",
    )
    fsm.go("bad_item", "left", "H", "bad_item")
    fsm.go("frame_end", "left", "1Ns1b", "item_r")
    for index in range(4):
        target = f"bound_r_{index + 1}" if index < 3 else "phase_branch"
        fsm.go(f"bound_r_{index}", "left", "r", f"bound_s_{index}")
        fsm.go(f"bound_s_{index}", "right", "s", target)

    fsm.bp(
        "phase_branch",
        "mid",
        "",
        zero="wall_r",
        pos="ctrl_drop",
    )
    fsm.sign(
        "wall_r",
        "right",
        "r",
        neg="ctrl_drop",
        zero="wall_unpack",
        pos="wall_unpack",
    )
    fsm.go("wall_unpack", "right", "M", "wall_div")
    fsm.go("wall_div", "lit_r", " `0016`W/", "wall_color_out")
    fsm.go("wall_color_out", "left", "WsW", "wall_addr_out")
    fsm.go("wall_addr_out", "left", "s", "wall_r")

    fsm.go("ctrl_drop", "left", "r", "addr_r")
    fsm.go("addr_r", "left", "rM", "man_color")
    fsm.go("man_color", "left", f"{COLOR_MAN}sW", "man_addr_out")
    fsm.go("man_addr_out", "left", "sWrr", "old_r")
    fsm.sign(
        "old_r",
        "left",
        "r-",
        neg="old_restore",
        zero="start_r",
        pos="old_restore",
    )

    # These two output blocks also stay high enough to bind the external
    # output rather than PIPEFRAME's bottom-wall command pipe.
    fsm.go("pipe_color_out", "left", "sW", "pipe_addr_out")
    fsm.go("pipe_addr_out", "left", "s", "pipe_pair_r")

    # Keep the main-stream read above the low PIPEFRAME response endpoint;
    # its successor blocks live lower/right and bind the service instead.
    fsm.go("pipe_body_r", "left", "r", "pipe_body_cmp")
    fsm.sign(
        "pipe_body_cmp",
        "lit_l",
        f"M`{-PIPE_END:04d}`+",
        neg="pipe_body_restore",
        zero="pipe_end_restore",
        pos="pipe_body_restore",
    )

    fsm.sign(
        "start_r",
        "left",
        "r",
        neg="room_end",
        zero="bad_start",
        pos="pipe_start_s",
    )
    fsm.go("bad_start", "left", "H", "bad_start")
    fsm.go("pipe_start_s", "right", "s", "pipe_body_r")
    fsm.go("pipe_body_restore", "right", "Ws", "pipe_body_r")
    fsm.go("pipe_end_restore", "right", "Ws", "pipe_pair_r")

    fsm.sign(
        "pipe_pair_r",
        "right",
        "r",
        neg="start_r",
        zero="pipe_addr_store",
        pos="pipe_addr_store",
    )
    fsm.go("pipe_addr_store", "right", "M", "pipe_color_r")
    fsm.go("pipe_color_r", "right", "r", "pipe_color_out")

    fsm.go("room_end", "left", "", "item_r")
    return fsm


def build_stateframe_room() -> list[str]:
    return _compile(_build_fsm())


def _phase_rows() -> tuple[int, int, int]:
    _routes, blocks, _height = _layout(_build_fsm())
    color = max(
        row for name, row in blocks.items() if name in {"load_s", "base_request"}
    )
    wall = min(row for name, row in blocks.items() if name.startswith("bound_s_"))
    pipe = min(
        row for name, row in blocks.items() if name in {"pipe_start_s", "pipe_pair_r"}
    )
    return color, wall, pipe


def _route_service(
    cv,
    ctrl_right: int,
    service_left: int,
    service_top: int,
    service: list[str],
    phase_row: int,
) -> None:
    from .lllm_fetch import build_relay

    service_right = service_left + len(service[0]) - 1
    relay_left = service_right + 5
    far = relay_left + 17
    cmd, resp = phase_row, phase_row + 4
    below = service_top + 2 > cmd
    cmd_track = ctrl_right + (4 if below else 2)
    resp_track = ctrl_right + (2 if below else 4)
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


CTRL_LEFT = 20
INPUT_ROW, OUTPUT_ROW = 2, 70
CONTROLLER_INPUT_ROW = 64


def build_stateframe_rig() -> str:
    from .lllm_fetch import build_relay

    ctrl = build_stateframe_room()
    ctrl_right = CTRL_LEFT + len(ctrl[0]) - 1
    service_left = ctrl_right + 12
    color, wall, pipe = (
        build_colorfetch_room(),
        build_wallgen_room(),
        build_pipeframe_room(),
    )
    color_phase, wall_phase, _pipe_phase = _phase_rows()
    wall_top = len(color) + 15
    cv = Canvas()
    cv.put(0, CTRL_LEFT, ctrl)
    cv.put(INPUT_ROW - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(OUTPUT_ROW - 1, 0, ["+-+", "|O|", "+-+"])
    # Preserve the component's conventional row-2 ingress while presenting
    # the controller with a mid-wall endpoint.  Without this relay, the
    # lower main-stream reads bind PIPEFRAME's nearer response pipe.
    relay_left = 5
    relay = build_relay().render()
    relay_right = relay_left + len(relay[0]) - 1
    input_track = CTRL_LEFT - 5
    cv.put(0, relay_left, relay)
    cv.pipe([(INPUT_ROW, 3), (INPUT_ROW, relay_left - 1)])
    cv.pipe(
        [
            (INPUT_ROW, relay_right + 1),
            (INPUT_ROW, input_track),
            (CONTROLLER_INPUT_ROW, input_track),
            (CONTROLLER_INPUT_ROW, CTRL_LEFT - 1),
        ]
    )
    cv.pipe([(OUTPUT_ROW, CTRL_LEFT - 1), (OUTPUT_ROW, 3)])
    for service, phase, top in (
        (color, color_phase, 0),
        (wall, wall_phase, wall_top),
    ):
        cv.put(top, service_left, service)
        _route_service(cv, ctrl_right, service_left, top, service, phase)

    # PIPEFRAME lives below/right of the controller. Its two pipes attach to
    # the controller's bottom wall, avoiding the pair of long vertical
    # COLORFETCH/WALLGEN routes in the controller/service gap.
    pipe_top = len(ctrl) + 12
    pipe_left = service_left + max(len(color[0]), len(wall[0])) + 70
    pipe_right = pipe_left + len(pipe[0]) - 1
    relay_left = pipe_right + 5
    far = relay_left + 17
    ctrl_bottom = len(ctrl) - 1
    command_col = CTRL_LEFT + len(ctrl[0]) - 16
    response_row = ctrl_bottom - 2
    command_detour = wall_top + len(wall) + 5
    response_detour = command_detour - 5
    top_approach = pipe_right + 32
    terminal_col = pipe_left + 8
    top_turn = pipe_top - 10
    response_drop = pipe_left - 5
    cv.put(pipe_top, pipe_left, pipe)
    cv.put(pipe_top + 20, relay_left, build_relay().render())
    cv.pipe(
        [
            (ctrl_bottom + 1, command_col),
            (command_detour, command_col),
            (command_detour, top_approach),
            (top_turn, top_approach),
            (top_turn, terminal_col),
            (pipe_top - 1, terminal_col),
        ]
    )
    cv.pipe(
        [
            (pipe_top + 6, pipe_left - 1),
            (pipe_top + 6, response_drop),
            (response_detour, response_drop),
            (response_detour, ctrl_right + 1),
            (response_row, ctrl_right + 1),
        ]
    )
    cv.cells[(response_row, ctrl_right + 1)] = "<"
    cv.pipe(
        [
            (pipe_top + 2, pipe_right + 1),
            (pipe_top + 2, far),
            (pipe_top + 21, far),
            (pipe_top + 21, relay_left + 6),
        ]
    )
    cv.pipe(
        [
            (pipe_top + 21, relay_left - 1),
            (pipe_top + 21, pipe_right + 2),
            (pipe_top + 9, pipe_right + 2),
            (pipe_top + 9, pipe_right + 1),
        ]
    )
    return cv.render()
