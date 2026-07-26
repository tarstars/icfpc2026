"""Component contracts and isolated rigs for Grade Book room optimization."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from littleman.gradebook import RELAY
from littleman.gradebook_components import (
    COMPACT_RESULT_ARBITER,
    FLAT_FIFO_CIRCULATOR,
    GRADEBOOK_04_ROOM_ORDER,
    build_fifo_circulator_rig,
    build_result_arbiter_rig,
)
from littleman.judge import judge_case
from littleman.server_compat import validate_layout
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parent.parent
LIVE = ROOT / "submissions" / "gradebook" / "gradebook_04.man"


def test_gradebook_04_room_names_and_metrics_are_frozen():
    machine = Machine.parse(LIVE.read_text())
    assert len(machine.rooms) == len(GRADEBOOK_04_ROOM_ORDER) == 16
    assert len({contract.name for contract in GRADEBOOK_04_ROOM_ORDER}) == 16
    assert Counter(contract.component for contract in GRADEBOOK_04_ROOM_ORDER) == {
        "input_port": 1,
        "command_frontend": 1,
        "subject_engine": 4,
        "fifo_circulator": 8,
        "result_arbiter": 1,
        "output_port": 1,
    }
    metrics = [
        (
            room.right - room.left + 1,
            room.bottom - room.top + 1,
            len(machine.in_pipes.get(id(room), [])),
            len(machine.out_pipes.get(id(room), [])),
        )
        for room in machine.rooms
    ]
    assert metrics == [
        (3, 3, 0, 1),
        (385, 115, 2, 4),
        (96, 154, 3, 4),
        (94, 157, 4, 4),
        (94, 157, 4, 4),
        (94, 157, 4, 4),
        *((5, 5, 1, 1) for _ in range(8)),
        (384, 5, 4, 1),
        (3, 3, 1, 0),
    ]


def test_gradebook_04_named_topology_matches_the_protocol():
    machine = Machine.parse(LIVE.read_text())
    names = {
        id(room): contract.name
        for room, contract in zip(machine.rooms, GRADEBOOK_04_ROOM_ORDER, strict=True)
    }
    edges = {(names[id(pipe.source)], names[id(pipe.dest)]) for pipe in machine.pipes}
    expected = {("input_port", "command_frontend")}
    for subject in range(1, 5):
        engine = f"subject_engine[{subject}]"
        scratch = f"scratch_circulator[{subject}]"
        record = f"record_circulator[{subject}]"
        expected |= {
            ("command_frontend", engine),
            (engine, scratch),
            (scratch, engine),
            (engine, record),
            (record, engine),
            (engine, "result_arbiter"),
            (
                engine,
                f"subject_engine[{subject + 1}]" if subject < 4 else "command_frontend",
            ),
        }
    expected.add(("result_arbiter", "output_port"))
    assert len(expected) == len(machine.pipes) == 30
    assert edges == expected


@pytest.mark.parametrize("room", [RELAY, FLAT_FIFO_CIRCULATOR])
def test_fifo_circulator_relays_every_value(room):
    rig = build_fifo_circulator_rig(room)
    rounds = [
        {"in": [str(value)], "out": [str(value)]}
        for value in (0, -1, 7, 1_000_000, -1_000_000)
    ]
    result = judge_case(rig, rounds, max_ticks=10_000)
    assert result.passed, result.reason
    validate_layout(rig)


def test_flat_fifo_is_an_area_trade_not_a_selected_replacement():
    assert (len(RELAY[0]), len(RELAY)) == (5, 5)
    assert (len(FLAT_FIFO_CIRCULATOR[0]), len(FLAT_FIFO_CIRCULATOR)) == (6, 4)
    assert len(FLAT_FIFO_CIRCULATOR[0]) * len(FLAT_FIFO_CIRCULATOR) < 25
    assert max(len(FLAT_FIFO_CIRCULATOR[0]), len(FLAT_FIFO_CIRCULATOR)) > 5


@pytest.mark.parametrize("active", [(1,), (2,), (3,), (4,)])
def test_result_arbiter_accepts_each_input_independently(active):
    rig = build_result_arbiter_rig(active)
    result = judge_case(
        rig,
        [{"in": [], "out": [str(active[0])]}],
        max_ticks=10_000,
    )
    assert result.passed, result.reason


def test_result_arbiter_uses_ready_pipe_reading_order_without_loss():
    rig = build_result_arbiter_rig()
    result = judge_case(
        rig,
        [{"in": [], "out": ["1", "3", "4", "2"]}],
        max_ticks=10_000,
    )
    assert result.passed, result.reason
    assert build_result_arbiter_rig() == rig
    validate_layout(rig)
    assert (len(COMPACT_RESULT_ARBITER[0]), len(COMPACT_RESULT_ARBITER)) == (6, 4)
