"""Execute LLM directly from the physical rich-geometry stream."""

from __future__ import annotations

from dataclasses import dataclass

from .llm import (
    COLOR_MAN,
    COLOR_PIPE,
    COLOR_PIPE_FULL,
    COLOR_WALL,
    HEADINGS,
    op_color,
)
from .llm_perimeter import ROOM_END, unpack_candidate
from .llm_pipetrace import DIRECTION_DELTA, PIPE_END
from .llm_rawfetch import unpack_raw_world
from .llm_roomfind import SETUP_END, WORLD_WORDS
from .sim import wrap64

DISPLAY = 16
CW = [(-1, 0), (0, 1), (1, 0), (0, -1)]


@dataclass
class RichRoom:
    top: int
    left: int
    bottom: int
    right: int
    man_addr: int

    def on_border(self, addr: int) -> bool:
        row, col = divmod(addr, DISPLAY)
        return (
            self.top <= row <= self.bottom
            and self.left <= col <= self.right
            and (row in (self.top, self.bottom) or col in (self.left, self.right))
        )


@dataclass
class RichPipe:
    source: int
    dest: int
    cells: list[int]
    values: list[int | None]


@dataclass
class RichMan:
    room: int
    addr: int
    heading: int = 1
    A: int = 0
    B: int = 0
    halted: bool = False


def parse_rich_stream(tokens: list[int]):
    raw = unpack_raw_world(tokens[:WORLD_WORDS])
    index = WORLD_WORDS
    rooms = []
    grouped_pipes = []
    while tokens[index] != SETUP_END:
        event, left_addr, right_addr, top_addr, bottom_addr = tokens[index : index + 5]
        index += 5
        man_addr = -(event + 1)
        rooms.append(
            RichRoom(
                top_addr // DISPLAY,
                left_addr % DISPLAY,
                bottom_addr // DISPLAY,
                right_addr % DISPLAY,
                man_addr,
            )
        )
        pipes = []
        while tokens[index] != ROOM_END:
            start = tokens[index]
            index += 1
            cells = []
            while tokens[index] != PIPE_END:
                cells.append(tokens[index])
                index += 1
            index += 1
            pipes.append((start, cells))
        index += 1
        grouped_pipes.append(pipes)

    pipes = []
    for source, entries in enumerate(grouped_pipes):
        for start, cells in entries:
            direction, _ = unpack_candidate(start)
            tail = cells[-1]
            code = raw[tail] & 0xFF
            for arrow_kind, arrow in ((2, "^"), (3, "v"), (4, "<"), (5, ">")):
                if code == ord(arrow):
                    direction = arrow_kind
                    break
            forward = tail + DIRECTION_DELTA[direction]
            dest = next(
                room_no
                for room_no, room in enumerate(rooms)
                if room_no != source and room.on_border(forward)
            )
            pipes.append(RichPipe(source, dest, cells, [None] * len(cells)))
    return raw, rooms, pipes, tokens[index + 1 :]


class RichExecutor:
    """Reference executor whose storage fields map directly to physical rings."""

    def __init__(self, tokens: list[int]):
        self.raw, self.rooms, self.pipes, self.tail = parse_rich_stream(tokens)
        self.men = [
            RichMan(index, room.man_addr) for index, room in enumerate(self.rooms)
        ]
        self.over = False

    def halted(self) -> bool:
        return self.over or all(man.halted for man in self.men)

    def run(self, ticks: int) -> None:
        for _ in range(ticks):
            if self.halted():
                break
            self.step()

    def step(self) -> None:
        for pipe in self.pipes:
            for index in range(len(pipe.values) - 1, 0, -1):
                if pipe.values[index] is None and pipe.values[index - 1] is not None:
                    pipe.values[index] = pipe.values[index - 1]
                    pipe.values[index - 1] = None

        moving = []
        for man in self.men:
            if man.halted:
                continue
            code = chr(self.raw[man.addr] & 0xFF)
            if code == "H":
                man.halted = True
                continue
            if code in HEADINGS:
                man.heading = CW.index(HEADINGS[code])
            elif code.isdigit():
                man.A = int(code)
            elif code == "M":
                man.B = man.A
            elif code == "+":
                man.A = wrap64(man.A + man.B)
            elif code == "-":
                man.A = wrap64(man.A - man.B)
            elif code == "X" and man.A:
                man.heading = (man.heading + (1 if man.A > 0 else -1)) % 4
            elif code == "s":
                pipe = self._nearest(man, outgoing=True)
                if pipe.values[0] is not None:
                    continue
                pipe.values[0] = man.A
            elif code == "r":
                pipe = self._nearest(man, outgoing=False)
                if pipe.values[-1] is None:
                    continue
                man.A = pipe.values[-1]
                pipe.values[-1] = None
            moving.append(man)

        for man in moving:
            dr, dc = CW[man.heading]
            man.addr += dr * DISPLAY + dc
        if any(
            self.rooms[man.room].on_border(man.addr)
            for man in self.men
            if not man.halted
        ):
            self.over = True

    def _nearest(self, man: RichMan, *, outgoing: bool) -> RichPipe:
        row, col = divmod(man.addr, DISPLAY)
        candidates = []
        for index, pipe in enumerate(self.pipes):
            room = pipe.source if outgoing else pipe.dest
            if room != man.room:
                continue
            target = pipe.cells[0] if outgoing else pipe.cells[-1]
            tr, tc = divmod(target, DISPLAY)
            candidates.append((abs(tr - row) + abs(tc - col), tr, tc, index))
        return self.pipes[min(candidates)[3]]

    def frame(self) -> list[str]:
        colors = [
            op_color(" " if (token & 0xFF) == ord("@") else chr(token & 0xFF))
            for token in self.raw
        ]
        for room in self.rooms:
            for row in range(room.top, room.bottom + 1):
                for col in range(room.left, room.right + 1):
                    addr = row * DISPLAY + col
                    if room.on_border(addr):
                        colors[addr] = COLOR_WALL
        for pipe in self.pipes:
            for addr, value in zip(pipe.cells, pipe.values, strict=True):
                colors[addr] = COLOR_PIPE_FULL if value is not None else COLOR_PIPE
        for man in self.men:
            colors[man.addr] = COLOR_MAN
        return [
            "".join(f"{colors[row * DISPLAY + col]:x}" for col in range(DISPLAY))
            for row in range(DISPLAY)
        ]


def run_rich_case(tokens: list[int]) -> list[list[str]]:
    executor = RichExecutor(tokens)
    frames = [executor.frame()]
    for ticks in executor.tail:
        executor.run(ticks)
        frames.append(executor.frame())
    return frames
