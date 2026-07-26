"""Exact indexed-state contract for the physical LLM action coordinator."""

from __future__ import annotations

from dataclasses import dataclass

from .llm_actionprotocol import (
    ActionTrace,
    _apply_record,
    _pipe_record,
)
from .llm_components import CLASS_RECV, CLASS_SEND
from .llm_manstep import STEP_DELTA
from .llm_pipeaction import parse_fetched_state, serialize_fetched_state
from .llm_pipeapply import (
    OP_RECV,
    OP_SEND,
    STATUS_BLOCKED,
    pipeapply_reference,
)
from .llm_pipecandidate import pipecandidate_reference
from .llm_selecteligible import selecteligible_reference
from .llm_stateindex import stateindex_reference, stateunindex_reference


@dataclass(frozen=True)
class IndexedCandidates:
    """Fixed two-slot decision packet consumed by the future physical shell."""

    active: bool
    room_no: int
    event: int
    op: int
    value: int
    addr: int
    targets: tuple[int, int]
    eligible: tuple[int, int]
    selected: int | None


def _operation(record: int) -> int | None:
    cls = (record & 255) >> 4
    if cls == CLASS_SEND:
        return OP_SEND
    if cls == CLASS_RECV:
        return OP_RECV
    return None


def indexed_candidates_reference(
    tokens: list[int],
    room_no: int,
) -> IndexedCandidates:
    """Produce the two fixed PIPECANDIDATE slots for one indexed room."""
    rooms, pipes = parse_fetched_state(stateunindex_reference(tokens))
    if room_no >= len(rooms):
        return IndexedCandidates(False, room_no, 0, 0, 0, 0, (0, 0), (0, 0), None)
    room = rooms[room_no]
    op = None if room.ctrl & 4 else _operation(room.record)
    if op is None:
        return IndexedCandidates(
            False,
            room_no,
            room.event,
            0,
            room.ai,
            room.addr,
            (0, 0),
            (0, 0),
            None,
        )

    targets = [0, 0]
    eligible = [0, 0]
    for pipe_no, pipe in enumerate(pipes):
        target = pipe.cells[0] if op == OP_SEND else pipe.cells[-1]
        request = [
            op,
            room.event,
            rooms[pipe.source].event,
            *room.fields[1:5],
            pipe.dest_addr,
            target,
        ]
        targets[pipe_no], eligible[pipe_no] = pipecandidate_reference(request)
    selected = selecteligible_reference(
        [room.addr, eligible[0], eligible[1], targets[0], targets[1]]
    )[0]
    return IndexedCandidates(
        True,
        room_no,
        room.event,
        op,
        room.ai,
        room.addr,
        tuple(targets),
        tuple(eligible),
        selected,
    )


def indexed_room_action_reference(
    tokens: list[int],
    room_no: int,
) -> tuple[list[int], ActionTrace | None]:
    """Apply exactly one room's action and return indexed state again."""
    state = stateunindex_reference(tokens)
    rooms, pipes = parse_fetched_state(state)
    decision = indexed_candidates_reference(tokens, room_no)
    if not decision.active:
        return list(tokens), None

    room = rooms[room_no]
    assert decision.selected is not None
    pipe = pipes[decision.selected]
    response = pipeapply_reference([decision.op, room.ai, *_pipe_record(pipe)])
    status, result = response[-2:]
    _apply_record(pipe, response[:-2])
    if status != STATUS_BLOCKED:
        room.addr += STEP_DELTA[room.ctrl & 3]
        if decision.op == OP_RECV:
            room.ai = result
    trace = ActionTrace(room_no, decision.op, decision.selected, status, result)
    updated = serialize_fetched_state(rooms, pipes)
    return stateindex_reference(updated), trace


def indexed_action_reference(
    tokens: list[int],
) -> tuple[list[int], list[ActionTrace]]:
    """Apply all rooms in creation order through the indexed contract."""
    rooms, _pipes = parse_fetched_state(stateunindex_reference(tokens))
    state = list(tokens)
    trace = []
    for room_no in range(len(rooms)):
        state, item = indexed_room_action_reference(state, room_no)
        if item is not None:
            trace.append(item)
    return state, trace
