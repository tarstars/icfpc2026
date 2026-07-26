"""Exact pipe-operation pass over one fetched normalized LLM state."""

from __future__ import annotations

from dataclasses import dataclass

from .llm_components import CLASS_RECV, CLASS_SEND
from .llm_manstep import STEP_DELTA
from .llm_perimeter import ROOM_END
from .llm_pipetrace import PIPE_END
from .llm_roomfind import SETUP_END
from .llm_statebuild import PIPE_DEST_STATE, PIPE_MASK, PIPE_VALUES


@dataclass
class ActionRoom:
    fields: list[int]
    record: int

    @property
    def event(self) -> int:
        return self.fields[0]

    @property
    def ctrl(self) -> int:
        return self.fields[5]

    @property
    def addr(self) -> int:
        return self.fields[6]

    @addr.setter
    def addr(self, value: int) -> None:
        self.fields[6] = value

    @property
    def ai(self) -> int:
        return self.fields[8]

    @ai.setter
    def ai(self, value: int) -> None:
        self.fields[8] = value

    def on_border(self, addr: int) -> bool:
        row, col = divmod(addr, 16)
        left, right = self.fields[1] % 16, self.fields[2] % 16
        top, bottom = self.fields[3] // 16, self.fields[4] // 16
        return (
            top <= row <= bottom
            and left <= col <= right
            and (row in (top, bottom) or col in (left, right))
        )


@dataclass
class ActionPipe:
    source: int
    start: int
    cells: list[int]
    bits: list[int]
    dest_addr: int
    mask: int
    values: list[int]
    dest: int = -1

    @property
    def head_bit(self) -> int:
        return self.bits[0]

    @property
    def tail_bit(self) -> int:
        return self.bits[-1]


def parse_fetched_state(tokens: list[int]) -> tuple[list[ActionRoom], list[ActionPipe]]:
    """Parse the stream after FETCHJOIN and before MANMAP."""
    rooms = []
    pipes = []
    index = 0
    while tokens[index] != SETUP_END:
        room = ActionRoom(list(tokens[index : index + 10]), tokens[index + 10])
        source = len(rooms)
        rooms.append(room)
        index += 11
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
            values = list(tokens[index + 2 : index + 2 + count])
            index += 2 + count
            if tokens[index] != PIPE_END:
                raise ValueError(f"missing pipe-end marker: {tokens[index]}")
            index += 1
            if body[-2] != PIPE_DEST_STATE:
                raise ValueError(f"missing destination marker: {body[-2]}")
            pipes.append(
                ActionPipe(
                    source,
                    start,
                    body[:-2:2],
                    body[1:-2:2],
                    body[-1],
                    mask,
                    values,
                )
            )
        index += 1
    if index + 1 != len(tokens):
        raise ValueError("unexpected fetched-state tail")
    for pipe in pipes:
        pipe.dest = next(
            room_no
            for room_no, room in enumerate(rooms)
            if room_no != pipe.source and room.on_border(pipe.dest_addr)
        )
    return rooms, pipes


def serialize_fetched_state(
    rooms: list[ActionRoom],
    pipes: list[ActionPipe],
) -> list[int]:
    out = []
    for room_no, room in enumerate(rooms):
        out.extend((*room.fields, room.record))
        for pipe in pipes:
            if pipe.source != room_no:
                continue
            out.append(pipe.start)
            for cell, bit in zip(pipe.cells, pipe.bits, strict=True):
                out.extend((cell, bit))
            out.extend(
                (
                    PIPE_DEST_STATE,
                    pipe.dest_addr,
                    PIPE_MASK,
                    pipe.mask,
                    PIPE_VALUES,
                    len(pipe.values),
                    *pipe.values,
                    PIPE_END,
                )
            )
        out.append(ROOM_END)
    return [*out, SETUP_END]


def _nearest(
    rooms: list[ActionRoom],
    pipes: list[ActionPipe],
    room_no: int,
    *,
    outgoing: bool,
) -> ActionPipe | None:
    row, col = divmod(rooms[room_no].addr, 16)
    candidates = []
    for pipe_no, pipe in enumerate(pipes):
        if (pipe.source if outgoing else pipe.dest) != room_no:
            continue
        target = pipe.cells[0] if outgoing else pipe.cells[-1]
        target_row, target_col = divmod(target, 16)
        candidates.append(
            (
                abs(target_row - row) + abs(target_col - col),
                target_row,
                target_col,
                pipe_no,
            )
        )
    return pipes[min(candidates)[3]] if candidates else None


def pipeaction_reference(tokens: list[int]) -> list[int]:
    """Apply `s`/`r` in man order; masks have already shifted this tick."""
    rooms, pipes = parse_fetched_state(tokens)
    for room_no, room in enumerate(rooms):
        if room.ctrl & 4:
            continue
        cls = (room.record & 255) >> 4
        if cls == CLASS_SEND:
            pipe = _nearest(rooms, pipes, room_no, outgoing=True)
            if pipe is None or pipe.mask & pipe.head_bit:
                continue
            pipe.mask |= pipe.head_bit
            pipe.values.append(room.ai)
        elif cls == CLASS_RECV:
            pipe = _nearest(rooms, pipes, room_no, outgoing=False)
            if pipe is None or not pipe.mask & pipe.tail_bit:
                continue
            pipe.mask &= ~pipe.tail_bit
            room.ai = pipe.values.pop(0)
        else:
            continue
        room.addr += STEP_DELTA[room.ctrl & 3]
    return serialize_fetched_state(rooms, pipes)
