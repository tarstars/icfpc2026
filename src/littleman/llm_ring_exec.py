"""Reference executor for the normalized mutable-ring LLM architecture."""

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
from .llm_perimeter import ROOM_END
from .llm_pipemask import advance_mask
from .llm_pipetrace import PIPE_END
from .llm_rawfetch import unpack_raw_world
from .llm_roomfind import SETUP_END, WORLD_WORDS
from .llm_statebuild import PIPE_DEST_STATE, PIPE_MASK, PIPE_VALUES
from .sim import wrap64

DISPLAY = 16
CW = [(-1, 0), (0, 1), (1, 0), (0, -1)]


@dataclass
class RingRoom:
    event: int
    left_addr: int
    right_addr: int
    top_addr: int
    bottom_addr: int
    ctrl: int
    addr: int
    B: int
    A: int
    old: int

    def on_border(self, addr: int) -> bool:
        row, col = divmod(addr, DISPLAY)
        top, bottom = self.top_addr // DISPLAY, self.bottom_addr // DISPLAY
        left, right = self.left_addr % DISPLAY, self.right_addr % DISPLAY
        return (
            top <= row <= bottom
            and left <= col <= right
            and (row in (top, bottom) or col in (left, right))
        )


@dataclass
class RingPipe:
    source: int
    start: int
    cells: list[int]
    bits: list[int]
    dest_addr: int
    mask: int
    values: list[int]
    dest: int = -1

    @property
    def tail_bit(self) -> int:
        return self.bits[-1]


def parse_state_stream(tokens: list[int]):
    raw = unpack_raw_world(tokens[:WORLD_WORDS])
    rooms: list[RingRoom] = []
    pipes: list[RingPipe] = []
    index = WORLD_WORDS
    while tokens[index] != SETUP_END:
        room = RingRoom(*tokens[index : index + 10])
        source = len(rooms)
        rooms.append(room)
        index += 10
        while tokens[index] != ROOM_END:
            start = tokens[index]
            index += 1
            body = []
            while tokens[index] != PIPE_MASK:
                body.extend(tokens[index : index + 2])
                index += 2
            mask = tokens[index + 1]
            index += 2
            if tokens[index] != PIPE_VALUES:
                raise ValueError(f"missing pipe-values marker: {tokens[index]}")
            count = tokens[index + 1]
            values = tokens[index + 2 : index + 2 + count]
            index += 2 + count
            if tokens[index] != PIPE_END:
                raise ValueError(f"missing pipe-end marker: {tokens[index]}")
            index += 1
            dest_marker = body[-2]
            dest_addr = body[-1]
            body = body[:-2]
            if dest_marker != PIPE_DEST_STATE:
                raise ValueError(f"missing pipe-destination marker: {dest_marker}")
            pipes.append(
                RingPipe(
                    source,
                    start,
                    body[::2],
                    body[1::2],
                    dest_addr,
                    mask,
                    values,
                )
            )
        index += 1

    for pipe in pipes:
        pipe.dest = next(
            room_no
            for room_no, room in enumerate(rooms)
            if room_no != pipe.source and room.on_border(pipe.dest_addr)
        )
    return raw, rooms, pipes, tokens[index + 1 :]


class RingExecutor:
    """Execute directly against normalized ring records and occupancy masks."""

    def __init__(self, tokens: list[int]):
        self.raw, self.rooms, self.pipes, self.tail = parse_state_stream(tokens)
        self.over = False

    def halted(self) -> bool:
        return self.over or all(room.ctrl & 4 for room in self.rooms)

    def run(self, ticks: int) -> None:
        for _ in range(ticks):
            if self.halted():
                break
            self.step()

    def step(self) -> None:
        for pipe in self.pipes:
            pipe.mask = advance_mask(pipe.mask)

        moving = []
        for room_no, man in enumerate(self.rooms):
            if man.ctrl & 4:
                continue
            code = chr(self.raw[man.addr] & 0xFF)
            if code == "H":
                man.ctrl |= 4
                continue
            if code in HEADINGS:
                man.ctrl = (man.ctrl & 4) | CW.index(HEADINGS[code])
            elif code.isdigit():
                man.A = int(code)
            elif code == "M":
                man.B = man.A
            elif code == "+":
                man.A = wrap64(man.A + man.B)
            elif code == "-":
                man.A = wrap64(man.A - man.B)
            elif code == "X" and man.A:
                man.ctrl = (man.ctrl & 4) | ((man.ctrl + (1 if man.A > 0 else -1)) & 3)
            elif code == "s":
                pipe = self._nearest(room_no, man.addr, outgoing=True)
                if pipe.mask & pipe.bits[0]:
                    continue
                pipe.values.append(man.A)
                pipe.mask |= pipe.bits[0]
            elif code == "r":
                pipe = self._nearest(room_no, man.addr, outgoing=False)
                if not pipe.mask & pipe.tail_bit:
                    continue
                man.A = pipe.values.pop(0)
                pipe.mask &= ~pipe.tail_bit
            moving.append(man)

        for man in moving:
            man.addr += (-16, 1, 16, -1)[man.ctrl & 3]
        if any(man.on_border(man.addr) for man in self.rooms if not man.ctrl & 4):
            self.over = True

    def _nearest(self, room_no: int, addr: int, *, outgoing: bool) -> RingPipe:
        row, col = divmod(addr, DISPLAY)
        candidates = []
        for pipe_no, pipe in enumerate(self.pipes):
            owner = pipe.source if outgoing else pipe.dest
            if owner != room_no:
                continue
            target = pipe.cells[0] if outgoing else pipe.cells[-1]
            target_row, target_col = divmod(target, DISPLAY)
            candidates.append(
                (
                    abs(target_row - row) + abs(target_col - col),
                    target_row,
                    target_col,
                    pipe_no,
                )
            )
        return self.pipes[min(candidates)[3]]

    def frame(self) -> list[str]:
        colors = [
            op_color(" " if (token & 0xFF) == ord("@") else chr(token & 0xFF))
            for token in self.raw
        ]
        for room in self.rooms:
            for addr in range(256):
                if room.on_border(addr):
                    colors[addr] = COLOR_WALL
        for pipe in self.pipes:
            for addr, bit in zip(pipe.cells, pipe.bits, strict=True):
                colors[addr] = COLOR_PIPE_FULL if pipe.mask & bit else COLOR_PIPE
        for man in self.rooms:
            colors[man.addr] = COLOR_MAN
        return [
            "".join(f"{colors[row * DISPLAY + col]:x}" for col in range(DISPLAY))
            for row in range(DISPLAY)
        ]


def run_ring_case(tokens: list[int]) -> list[list[str]]:
    executor = RingExecutor(tokens)
    frames = [executor.frame()]
    for ticks in executor.tail:
        for room in executor.rooms:
            room.old = room.addr
        executor.run(ticks)
        frames.append(executor.frame())
    return frames
