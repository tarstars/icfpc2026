"""Executable contract for composing the physical LLM action services."""

from __future__ import annotations

from dataclasses import dataclass

from .llm_components import CLASS_RECV, CLASS_SEND
from .llm_manstep import STEP_DELTA
from .llm_pipeaction import (
    ActionPipe,
    ActionRoom,
    parse_fetched_state,
    serialize_fetched_state,
)
from .llm_pipeapply import (
    OP_RECV,
    OP_SEND,
    STATUS_BLOCKED,
    pipeapply_reference,
)
from .llm_pipecandidate import pipecandidate_reference
from .llm_pipetrace import PIPE_END
from .llm_selecteligible import selecteligible_reference
from .llm_statebuild import PIPE_DEST_STATE, PIPE_MASK, PIPE_VALUES


@dataclass(frozen=True)
class ActionTrace:
    room_no: int
    op: int
    pipe_no: int
    status: int
    result: int


def _pipe_record(pipe: ActionPipe) -> list[int]:
    body = [item for pair in zip(pipe.cells, pipe.bits, strict=True) for item in pair]
    return [
        pipe.start,
        *body,
        PIPE_DEST_STATE,
        pipe.dest_addr,
        PIPE_MASK,
        pipe.mask,
        PIPE_VALUES,
        len(pipe.values),
        *pipe.values,
        PIPE_END,
    ]


def _apply_record(pipe: ActionPipe, record: list[int]) -> None:
    mask_index = record.index(PIPE_MASK)
    pipe.mask = record[mask_index + 1]
    values_index = record.index(PIPE_VALUES, mask_index + 2)
    count = record[values_index + 1]
    pipe.values = list(record[values_index + 2 : values_index + 2 + count])


def _select(
    rooms: list[ActionRoom],
    pipes: list[ActionPipe],
    room_no: int,
    op: int,
) -> int:
    room = rooms[room_no]
    targets = [0, 0]
    eligible = [0, 0]
    for pipe_no, pipe in enumerate(pipes):
        target = pipe.cells[0] if op == OP_SEND else pipe.cells[-1]
        request = [
            op,
            room_no,
            pipe.source,
            *room.fields[1:5],
            pipe.dest_addr,
            target,
        ]
        targets[pipe_no], eligible[pipe_no] = pipecandidate_reference(request)
    return selecteligible_reference(
        [room.addr, eligible[0], eligible[1], targets[0], targets[1]]
    )[0]


def actionprotocol_reference(
    tokens: list[int],
) -> tuple[list[int], list[ActionTrace]]:
    """Apply actions through the exact PIPECANDIDATE/SELECT/PIPEAPPLY APIs."""
    rooms, pipes = parse_fetched_state(tokens)
    trace = []
    for room_no, room in enumerate(rooms):
        if room.ctrl & 4:
            continue
        cls = (room.record & 255) >> 4
        if cls == CLASS_SEND:
            op = OP_SEND
        elif cls == CLASS_RECV:
            op = OP_RECV
        else:
            continue
        pipe_no = _select(rooms, pipes, room_no, op)
        response = pipeapply_reference([op, room.ai, *_pipe_record(pipes[pipe_no])])
        status, result = response[-2:]
        _apply_record(pipes[pipe_no], response[:-2])
        if status != STATUS_BLOCKED:
            room.addr += STEP_DELTA[room.ctrl & 3]
            if op == OP_RECV:
                room.ai = result
        trace.append(ActionTrace(room_no, op, pipe_no, status, result))
    return serialize_fetched_state(rooms, pipes), trace
