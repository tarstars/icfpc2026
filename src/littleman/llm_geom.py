"""Position-first LLM geometry and binding without invoking the parser."""

from __future__ import annotations

from dataclasses import dataclass

from .llm import COLOR_PIPE, COLOR_WALL, op_color
from .llm_components import (
    exec_record,
    pack_cell,
    pack_pipe_desc,
    pack_room,
)

DISPLAY = 16
ARROWS = {ord("^"): (-1, 0), ord("v"): (1, 0), ord("<"): (0, -1), ord(">"): (0, 1)}
DIRECTIONS = ((-1, 0), (1, 0), (0, -1), (0, 1))


@dataclass(frozen=True)
class Geometry:
    rooms: tuple[tuple[int, int, int, int], ...]
    pipes: tuple[tuple[int, int, tuple[int, ...]], ...]


@dataclass(frozen=True)
class Finalized:
    geometry: Geometry
    cells: tuple[int, ...]
    exec_words: tuple[int, ...]
    pipe_descs: tuple[int, ...]
    pipe_cells: tuple[int, ...]
    men: tuple[int, ...]


def _char(raw: list[int], row: int, col: int) -> int:
    if not (0 <= row < DISPLAY and 0 <= col < DISPLAY):
        raise ValueError(f"address outside canvas: {(row, col)}")
    return raw[row * DISPLAY + col] & 0xFF


def discover_rooms(raw: list[int], men: list[int]) -> list[tuple[int, int, int, int]]:
    """Recover each enclosing rectangle by walking from its unique man."""
    rooms = []
    for addr in men:
        row, col = divmod(addr, DISPLAY)
        left = col
        while _char(raw, row, left) != ord("|"):
            left -= 1
        right = col
        while _char(raw, row, right) != ord("|"):
            right += 1
        top = row
        while _char(raw, top, left) == ord("|"):
            top -= 1
        bottom = row
        while _char(raw, bottom, left) == ord("|"):
            bottom += 1
        room = (top, left, bottom, right)
        if _char(raw, top, left) != ord("+") or _char(raw, bottom, right) != ord("+"):
            raise ValueError(f"man {addr} does not lead to a room")
        rooms.append(room)
    return sorted(set(rooms))


def _contains(room, row, col) -> bool:
    top, left, bottom, right = room
    return top <= row <= bottom and left <= col <= right


def _on_border(room, row, col) -> bool:
    top, left, bottom, right = room
    return _contains(room, row, col) and (
        row in (top, bottom) or col in (left, right)
    )


def _trace_pipe(raw, rooms, source_no, row, col, direction):
    cells = []
    while True:
        cells.append(row * DISPLAY + col)
        code = _char(raw, row, col)
        if code in ARROWS:
            new_direction = ARROWS[code]
            if len(cells) > 1 and new_direction == (-direction[0], -direction[1]):
                raise ValueError("pipe reverses")
            direction = new_direction
            nr, nc = row + direction[0], col + direction[1]
            for target_no, room in enumerate(rooms):
                if target_no != source_no and _on_border(room, nr, nc):
                    return target_no, tuple(cells)
        row += direction[0]
        col += direction[1]
        code = _char(raw, row, col)
        body = ord("-") if direction[1] else ord("|")
        if code not in ARROWS and code != body:
            raise ValueError(f"bad pipe glyph {chr(code)!r} at {(row, col)}")


def discover_geometry(raw: list[int], men: list[int]) -> Geometry:
    rooms = discover_rooms(raw, men)
    used = set()
    pipes = []
    for source_no, room in enumerate(rooms):
        top, left, bottom, right = room
        for row in range(top, bottom + 1):
            cols = range(left, right + 1) if row in (top, bottom) else (left, right)
            for col in cols:
                for direction in DIRECTIONS:
                    nr, nc = row + direction[0], col + direction[1]
                    if not (0 <= nr < DISPLAY and 0 <= nc < DISPLAY):
                        continue
                    if _contains(room, nr, nc) or nr * DISPLAY + nc in used:
                        continue
                    if ARROWS.get(_char(raw, nr, nc)) != direction:
                        continue
                    dest_no, cells = _trace_pipe(
                        raw, rooms, source_no, nr, nc, direction
                    )
                    if cells[0] in used:
                        continue
                    used.update(cells)
                    pipes.append((source_no, dest_no, cells))
    return Geometry(tuple(rooms), tuple(pipes))


def finalize(raw: list[int], men: list[int]) -> Finalized:
    """Bake wall, pipe, binding, color, and runtime record fields."""
    geometry = discover_geometry(raw, men)
    wall_addrs = set()
    for top, left, bottom, right in geometry.rooms:
        wall_addrs.update(top * DISPLAY + col for col in range(left, right + 1))
        wall_addrs.update(bottom * DISPLAY + col for col in range(left, right + 1))
        wall_addrs.update(row * DISPLAY + left for row in range(top, bottom + 1))
        wall_addrs.update(row * DISPLAY + right for row in range(top, bottom + 1))
    pipe_addrs = {addr for _, _, cells in geometry.pipes for addr in cells}

    def room_of(addr):
        row, col = divmod(addr, DISPLAY)
        for index, (top, left, bottom, right) in enumerate(geometry.rooms):
            if top < row < bottom and left < col < right:
                return index
        return None

    setup_records = []
    exec_records = []
    for addr, raw_token in enumerate(raw):
        char = raw_token & 0xFF
        if char == ord("@"):
            char = ord(" ")
        wall = int(addr in wall_addrs)
        pipe = int(addr in pipe_addrs)
        color = COLOR_PIPE if pipe else COLOR_WALL if wall else op_color(chr(char))
        bind = 0
        if char in (ord("s"), ord("r")):
            room_no = room_of(addr)
            outgoing = char == ord("s")
            candidates = []
            row, col = divmod(addr, DISPLAY)
            for pno, (source, dest, cells) in enumerate(geometry.pipes):
                if (source if outgoing else dest) != room_no:
                    continue
                target = cells[0] if outgoing else cells[-1]
                tr, tc = divmod(target, DISPLAY)
                candidates.append((abs(tr - row) + abs(tc - col), tr, tc, pno))
            if candidates:
                bind = min(candidates)[3] + 1
        setup_records.append(pack_cell(char, color, wall, pipe, bind))
        exec_records.append(exec_record(char, color, wall, pipe, bind))

    words = tuple(
        sum(exec_records[base + index] << (13 * index) for index in range(4))
        for base in range(0, 256, 4)
    )
    descs = tuple(
        pack_pipe_desc(len(cells), source, dest, cells[0], cells[-1])
        for source, dest, cells in geometry.pipes
    )
    return Finalized(
        geometry,
        tuple(setup_records),
        words,
        descs,
        tuple(addr for _, _, cells in geometry.pipes for addr in cells),
        tuple(men),
    )
