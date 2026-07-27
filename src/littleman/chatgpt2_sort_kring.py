"""chatgpt_2 two-pump Sort experiment.

This module preserves a complete, deterministic end-to-end implementation of
the repository's unfinished two-pump K-ring idea.  It is deliberately isolated
from :mod:`littleman.sort_kring`: the historical component sketch is read-only
and the exact component bytes used by this experiment live here.

The resulting machine is correct but not score-positive.  It is kept as a
reproducible architectural experiment and as evidence for the measured lower
bound in ``reports/2026-07-27-chatgpt2-sort-kring.md``.
"""
from __future__ import annotations

from collections import deque

from .canvas import Canvas
from .gradebook import CompiledRoom, Fsm, compile_fsm

PUMP_INTERIOR = [
    " @vs{{1M7<",
    "  >rMbmX ^",
    "    vsr<  ",
    "    am ^  ",
    "vMbW<     ",
    ">1W-    v ",
    " v  Mrsm< ",
    "v amsW<   ",
    "Wa v  +   ",
    "v<>>r-Xv  ",
    "s     ++  ",
    "vsWdms<<  ",
    ">rbM1W- a^",
]

RELAY = [
    "@>rv",
    " ^s<",
]

MERGER = [
    ">@rbrM       rWv",
    "      >Ws+MrW> v",
    "     vX-      md",
    " vrs+<<         ",
    " >           ^  ",
    "^              <",
]


def _room(interior: list[str]) -> list[str]:
    width = len(interior[0])
    if not all(len(row) == width for row in interior):
        raise ValueError("ragged room interior")
    edge = "+" + "-" * width + "+"
    return [edge] + ["|" + row + "|" for row in interior] + [edge]


def _io(ch: str) -> list[str]:
    return ["+-+", f"|{ch}|", "+-+"]


def build_splitter_fsm() -> Fsm:
    fsm = Fsm()
    fsm.go("start", "input", "@r", "send_n")
    fsm.go("send_n", "n_out", "sbM2W/", "send_b_count")
    fsm.go("send_b_count", "b_out", "s+", "send_a_count")
    fsm.go("send_a_count", "a_out", "s", "read_a")
    fsm.bp("read_a", "a_out", "rsm", zero="start", positive="read_b")
    fsm.bp("read_b", "b_out", "rsm", zero="start", positive="read_a")
    return fsm


SPLITTER_ZONES = {"input": -10, "a_out": -8, "n_out": -6, "b_out": -4}


def build_splitter_room() -> CompiledRoom:
    return compile_fsm(build_splitter_fsm(), SPLITTER_ZONES, right_padding=2)


def build_prefixer_fsm() -> Fsm:
    fsm = Fsm()
    fsm.go("init", "logic", "@7M1{{M", "read_n")
    fsm.go("read_n", "n_in", "r", "send_n")
    fsm.go("send_n", "out", "s", "read_pump")
    fsm.go("read_pump", "pump_in", "r", "send_and_test")
    fsm.sign(
        "send_and_test",
        "out",
        "s-",
        negative="read_pump",
        zero="read_n",
        positive="read_n",
    )
    return fsm


PREFIXER_ZONES = {"pump_in": -10, "logic": -8, "n_in": -6, "out": -4}


def build_prefixer_room() -> CompiledRoom:
    return compile_fsm(build_prefixer_fsm(), PREFIXER_ZONES, right_padding=2)


UP = (-1, 0)
DOWN = (1, 0)
LEFT = (0, -1)
RIGHT = (0, 1)
DIRECTIONS = (UP, DOWN, LEFT, RIGHT)
ARROW = {UP: "^", DOWN: "v", LEFT: "<", RIGHT: ">"}
BODY = {UP: "|", DOWN: "|", LEFT: "-", RIGHT: "-"}


def build_chatgpt2_sort_00() -> str:
    """Render the exact 9-room, 12-pipe two-pump prototype."""
    splitter = build_splitter_room()
    prefixer = build_prefixer_room()
    art = {
        "I": _io("I"),
        "O": _io("O"),
        "S": splitter.rows,
        "PA": _room(PUMP_INTERIOR),
        "PB": _room(PUMP_INTERIOR),
        "RA": _room(RELAY),
        "RB": _room(RELAY),
        "X": prefixer.rows,
        "M": _room(MERGER),
    }
    placement = {
        "I": (0, 60),
        "S": (10, 60),
        "PA": (50, 10),
        "RA": (70, 15),
        "PB": (50, 150),
        "RB": (70, 155),
        "X": (100, 60),
        "M": (130, 130),
        "O": (150, 137),
    }
    pipes = [
        ("I", "S"),
        ("S_N", "X_N"),
        ("S_A", "PA_F"),
        ("S_B", "PB_F"),
        ("PA_R", "RA_I"),
        ("RA_O", "PA_I"),
        ("PB_R", "RB_I"),
        ("RB_O", "PB_I"),
        ("PA_O", "X_P"),
        ("X_O", "M_L"),
        ("PB_O", "M_R"),
        ("M_O", "O"),
    ]

    def bounds(name: str) -> tuple[int, int, int, int]:
        row, column = placement[name]
        rows = art[name]
        return (
            row,
            column,
            row + len(rows) - 1,
            column + max(map(len, rows)) - 1,
        )

    boxes = {name: bounds(name) for name in placement}

    def endpoint(tag: str):
        if tag == "I":
            top, left, bottom, right = boxes["I"]
            return (top + 1, right + 1), RIGHT
        if tag == "S":
            top, left, bottom, right = boxes["S"]
            return (top - 1, left + splitter.zones["input"]), DOWN
        if tag == "S_N":
            top, left, bottom, right = boxes["S"]
            return (bottom + 1, left + splitter.zones["n_out"]), DOWN
        if tag == "S_A":
            top, left, bottom, right = boxes["S"]
            return (bottom + 1, left + splitter.zones["a_out"]), DOWN
        if tag == "S_B":
            top, left, bottom, right = boxes["S"]
            return (bottom + 1, left + splitter.zones["b_out"]), DOWN
        if tag in ("PA_F", "PB_F"):
            name = tag[:2]
            top, left, bottom, right = boxes[name]
            return (top - 1, left + 5), DOWN
        if tag in ("PA_R", "PB_R"):
            name = tag[:2]
            top, left, bottom, right = boxes[name]
            return (bottom + 1, left + 7), DOWN
        if tag in ("PA_I", "PB_I"):
            name = tag[:2]
            top, left, bottom, right = boxes[name]
            return (bottom + 1, left + 6), UP
        if tag in ("PA_O", "PB_O"):
            name = tag[:2]
            top, left, bottom, right = boxes[name]
            return (top + 12, left - 1), LEFT
        if tag in ("RA_I", "RB_I"):
            name = tag[:2]
            top, left, bottom, right = boxes[name]
            return (top + 1, left - 1), RIGHT
        if tag in ("RA_O", "RB_O"):
            name = tag[:2]
            top, left, bottom, right = boxes[name]
            return (top + 2, left - 1), LEFT
        if tag == "X_N":
            top, left, bottom, right = boxes["X"]
            return (top - 1, left + prefixer.zones["n_in"]), DOWN
        if tag == "X_P":
            top, left, bottom, right = boxes["X"]
            return (top - 1, left + prefixer.zones["pump_in"]), DOWN
        if tag == "X_O":
            top, left, bottom, right = boxes["X"]
            return (bottom + 1, left + prefixer.zones["out"]), DOWN
        if tag == "M_L":
            top, left, bottom, right = boxes["M"]
            return (top + 2, left - 1), RIGHT
        if tag == "M_R":
            top, left, bottom, right = boxes["M"]
            return (top + 2, right + 1), LEFT
        if tag == "M_O":
            top, left, bottom, right = boxes["M"]
            return (bottom + 1, left + 7), DOWN
        if tag == "O":
            top, left, bottom, right = boxes["O"]
            return (top - 1, left + 1), DOWN
        raise KeyError(tag)

    canvas = Canvas()
    room_cells: set[tuple[int, int]] = set()
    moat: set[tuple[int, int]] = set()
    for name, (row, column) in placement.items():
        canvas.put(row, column, art[name])
        top, left, bottom, right = boxes[name]
        for y in range(top, bottom + 1):
            for x in range(left, right + 1):
                room_cells.add((y, x))
    for name in placement:
        top, left, bottom, right = boxes[name]
        for y in range(top - 1, bottom + 2):
            for x in range(left - 1, right + 2):
                if (y, x) not in room_cells:
                    moat.add((y, x))

    used: set[tuple[int, int]] = set()

    def route(source_tag: str, destination_tag: str) -> None:
        start, start_direction = endpoint(source_tag)
        goal, goal_direction = endpoint(destination_tag)
        second = (
            start[0] + start_direction[0],
            start[1] + start_direction[1],
        )
        before = (goal[0] - goal_direction[0], goal[1] - goal_direction[1])
        allowed = {start, second, before, goal}
        blocked = (room_cells | moat | used) - allowed
        queue = deque([second])
        previous = {second: start}
        while queue:
            point = queue.popleft()
            if point == before:
                break
            for direction in DIRECTIONS:
                nxt = (point[0] + direction[0], point[1] + direction[1])
                if not (0 <= nxt[0] <= 180 and 0 <= nxt[1] <= 180):
                    continue
                if nxt in blocked or nxt in previous or nxt == goal:
                    continue
                previous[nxt] = point
                queue.append(nxt)
        else:
            raise RuntimeError(("no route", source_tag, destination_tag))
        path = [before]
        while path[-1] != start:
            path.append(previous[path[-1]])
        path.reverse()
        path.append(goal)
        used.update(path)
        for index, point in enumerate(path):
            direction = (
                goal_direction
                if index == len(path) - 1
                else (
                    path[index + 1][0] - point[0],
                    path[index + 1][1] - point[1],
                )
            )
            previous_direction = (
                None
                if index == 0
                else (
                    point[0] - path[index - 1][0],
                    point[1] - path[index - 1][1],
                )
            )
            canvas.cells[point] = (
                ARROW[direction]
                if index in (0, len(path) - 1) or direction != previous_direction
                else BODY[direction]
            )

    for source, destination in pipes:
        route(source, destination)
    return canvas.render()


if __name__ == "__main__":
    print(build_chatgpt2_sort_00(), end="")
