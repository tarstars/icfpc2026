"""Detect whether one normalized LLM runtime state may execute another tick."""

from __future__ import annotations

from .canvas import Canvas
from .lllm_fetch import build_relay
from .lllm_scan import _compile, _Fsm
from .llm_perimeter import ROOM_END
from .llm_pipetrace import PIPE_END
from .llm_roomfind import SETUP_END, WORLD_WORDS
from .llm_statebuild import PIPE_MASK, PIPE_VALUES
from .llm_wallhit import build_wallhit_room, wallhit_reference

ROUNDSTATUS_END = -5200


def room_statuses_reference(tokens: list[int]) -> list[int]:
    """Return 0=halted, 1=live interior, or 2=live on wall per room."""
    out = []
    index = 0
    while tokens[index] != SETUP_END:
        fields = tokens[index : index + 10]
        index += 10
        live = not fields[5] & 4
        wall = wallhit_reference([*fields[1:5], fields[6]])[0]
        out.append(2 if live and wall else int(live))
        while tokens[index] != ROOM_END:
            index += 1
            while tokens[index] != PIPE_MASK:
                index += 2
            index += 2
            if tokens[index] != PIPE_VALUES:
                raise ValueError("missing pipe values")
            count = tokens[index + 1]
            index += 2 + count
            if tokens[index] != PIPE_END:
                raise ValueError("missing pipe end")
            index += 1
        index += 1
    if index + 1 != len(tokens):
        raise ValueError("unexpected runtime-state tail")
    return out


def roundstatus_reference(tokens: list[int]) -> int:
    """One iff at least one man is live and no live man is on a wall."""
    statuses = room_statuses_reference(tokens)
    return int(1 in statuses and 2 not in statuses)


def _build_scan_fsm(*, prefix_world: bool = False) -> _Fsm:
    fsm = _Fsm()
    if prefix_world:
        fsm.go("boot", "lit_l", f"@`{WORLD_WORDS:04d}`b", "world_r")
        fsm.go("world_r", "left", "r", "world_count")
        fsm.bp("world_count", "mid", "m", zero="item_r", pos="world_r")
    else:
        fsm.go("boot", "left", "@", "item_r")
    fsm.go("item_r", "left", "r", "item_cmp")
    fsm.sign(
        "item_cmp",
        "lit_l",
        "M`1000`+",
        neg="bad_item",
        zero="scan_end",
        pos="bound_r_0",
    )
    fsm.go("bad_item", "left", "H", "bad_item")
    for index in range(4):
        target = f"bound_r_{index + 1}" if index < 3 else "ctrl_r"
        fsm.go(f"bound_r_{index}", "left", "r", f"bound_s_{index}")
        fsm.go(f"bound_s_{index}", "right", "s", target)
    fsm.go("ctrl_r", "left", "r", "ctrl_cmp")
    fsm.sign(
        "ctrl_cmp",
        "lit_l",
        "M`0004`W-",
        neg="live_addr_r",
        zero="halt_addr_r",
        pos="halt_addr_r",
    )
    for state in ("live", "halt"):
        fsm.go(f"{state}_addr_r", "left", "r", f"{state}_addr_s")
        fsm.go(f"{state}_addr_s", "right", "s", f"{state}_tail_drop")
        fsm.go(f"{state}_tail_drop", "left", "rrr", f"{state}_flag_r")
        fsm.go(f"{state}_flag_r", "right", "r", f"{state}_flag")
    fsm.sign(
        "live_flag",
        "mid",
        "",
        neg="bad_item",
        zero="live_out",
        pos="wall_out",
    )
    fsm.go("live_out", "left", "1s", "start_r")
    fsm.go("wall_out", "left", "2s", "start_r")
    fsm.go("halt_flag", "left", "0s", "start_r")
    fsm.sign(
        "start_r",
        "left",
        "r",
        neg="room_end",
        zero="bad_item",
        pos="pipe_body_r",
    )
    fsm.go("pipe_body_r", "left", "r", "pipe_body_cmp")
    fsm.sign(
        "pipe_body_cmp",
        "lit_l",
        f"M`{-PIPE_END:04d}`+",
        neg="pipe_body_r",
        zero="start_r",
        pos="pipe_body_r",
    )
    fsm.go("room_end", "left", "", "item_r")
    fsm.go(
        "scan_end",
        "lit_l",
        f"M`{-ROUNDSTATUS_END:04d}`Ns",
        "item_r",
    )
    return fsm


def build_roundstatus_scan_room(*, prefix_world: bool = False) -> list[str]:
    return _compile(_build_scan_fsm(prefix_world=prefix_world))


def build_roundstatus_scan_rig(*, prefix_world: bool = False) -> str:
    ctrl = build_roundstatus_scan_room(prefix_world=prefix_world)
    ctrl_left = 5
    ctrl_right = ctrl_left + len(ctrl[0]) - 1
    service_left = ctrl_right + 10
    service = build_wallhit_room()
    service_right = service_left + len(service[0]) - 1
    relay_left = service_right + 5
    far = relay_left + 17
    cv = Canvas()
    cv.put(0, ctrl_left, ctrl)
    cv.put(0, service_left, service)
    cv.put(20, relay_left, build_relay().render())
    cv.put(1, 0, ["+-+", "|I|", "+-+"])
    cv.put(5, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(2, 3), (2, ctrl_left - 1)])
    cv.pipe([(6, ctrl_left - 1), (6, 3)])
    cv.pipe([(2, ctrl_right + 1), (2, service_left - 1)])
    cv.pipe(
        [
            (6, service_left - 1),
            (6, ctrl_right + 4),
            (9, ctrl_right + 4),
            (9, ctrl_right + 1),
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


def _build_reduce_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "none_r")
    for state, end in (
        ("none", "none_end"),
        ("live", "live_end"),
        ("stop", "stop_end"),
    ):
        fsm.go(f"{state}_r", "left", "r", f"{state}_cmp")
        fsm.sign(
            f"{state}_cmp",
            "lit_l",
            f"M`{-ROUNDSTATUS_END:04d}`+",
            neg="bad_status",
            zero=end,
            pos=f"{state}_restore",
        )
    fsm.go("none_restore", "left", "W", "none_status")
    fsm.sign(
        "none_status",
        "mid",
        "",
        neg="bad_status",
        zero="none_r",
        pos="none_pos",
    )
    fsm.sign(
        "none_pos",
        "lit_l",
        "M`0001`W-",
        neg="bad_status",
        zero="live_r",
        pos="stop_r",
    )
    fsm.go("live_restore", "left", "W", "live_status")
    fsm.sign(
        "live_status",
        "lit_l",
        "M`0002`W-",
        neg="live_r",
        zero="stop_r",
        pos="bad_status",
    )
    fsm.go("stop_restore", "left", "", "stop_r")
    fsm.go("none_end", "left", "0s", "none_r")
    fsm.go("live_end", "left", "1s", "none_r")
    fsm.go("stop_end", "left", "0s", "none_r")
    fsm.go("bad_status", "left", "H", "bad_status")
    return fsm


def build_roundstatus_reduce_room() -> list[str]:
    return _compile(_build_reduce_fsm())


def build_roundstatus_reduce_rig() -> str:
    room = build_roundstatus_reduce_room()
    cv = Canvas()
    cv.put(0, 5, room)
    cv.put(1, 0, ["+-+", "|I|", "+-+"])
    cv.put(5, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(2, 3), (2, 4)])
    cv.pipe([(6, 4), (6, 3)])
    return cv.render()


def build_roundstatus_rig(*, prefix_world: bool = False) -> str:
    """Compose the destructive room scan with its three-state reducer."""
    from .llm_roomstage import _strip_io

    scan_rows, scan_in, scan_out = _strip_io(
        build_roundstatus_scan_rig(prefix_world=prefix_world)
    )
    reduce_rows, reduce_in, reduce_out = _strip_io(build_roundstatus_reduce_rig())
    left = 20
    reduce_top = len(scan_rows) + 20
    content_width = max(
        max(map(len, scan_rows)),
        max(map(len, reduce_rows)),
    )
    output_row = reduce_top + len(reduce_rows) + 10
    output_box_left = left + content_width + 10
    cv = Canvas()
    cv.put(0, left, scan_rows)
    cv.put(reduce_top, left, reduce_rows)
    scan_in = (scan_in[0], left + scan_in[1])
    scan_out = (scan_out[0], left + scan_out[1])
    reduce_in = (reduce_top + reduce_in[0], left + reduce_in[1])
    reduce_out = (reduce_top + reduce_out[0], left + reduce_out[1])
    cv.pipe(
        [
            scan_out,
            (scan_out[0], 10),
            (reduce_in[0], 10),
            reduce_in,
        ]
    )
    cv.put(scan_in[0] - 1, 0, ["+-+", "|I|", "+-+"])
    cv.pipe([(scan_in[0], 3), scan_in])
    cv.put(output_row - 1, output_box_left, ["+-+", "|O|", "+-+"])
    cv.pipe(
        [
            reduce_out,
            (reduce_out[0], 5),
            (output_row, 5),
            (output_row, output_box_left - 1),
        ]
    )
    return cv.render()


def strip_roundstatus_rig(
    *, prefix_world: bool = False
) -> tuple[list[str], tuple[int, int], tuple[int, int]]:
    """Remove I/O boxes while preserving this rig's opposite-side ports."""
    rows = [
        list(row)
        for row in build_roundstatus_rig(prefix_world=prefix_world).splitlines()
    ]
    width = max(map(len, rows))
    for row in rows:
        row.extend([" "] * (width - len(row)))

    ports = {}
    for label in ("I", "O"):
        matches = [
            (r, c)
            for r, row in enumerate(rows)
            for c, char in enumerate(row)
            if char == label
            and c
            and c + 1 < width
            and row[c - 1 : c + 2] == ["|", label, "|"]
        ]
        if len(matches) != 1:
            raise ValueError(f"expected one {label} box, found {matches}")
        row, center = matches[0]
        left = center - 1
        for rr in range(row - 1, row + 2):
            for cc in range(left, left + 3):
                rows[rr][cc] = " "
        ports[label] = (row, left + 3 if label == "I" else left - 1)
    return ["".join(row) for row in rows], ports["I"], ports["O"]
