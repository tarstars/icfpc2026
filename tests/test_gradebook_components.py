"""Component contracts and isolated rigs for Grade Book room optimization."""

from __future__ import annotations

import json
from collections import Counter, deque
from itertools import pairwise
from pathlib import Path

import pytest

from littleman.gradebook import RELAY
from littleman.gradebook_components import (
    COMPACT_RESULT_ARBITER,
    FLAT_FIFO_CIRCULATOR,
    GRADEBOOK_04_ROOM_ORDER,
    GRADEBOOK_COMPONENT_FOLD_PREFIXES,
    build_fifo_circulator_rig,
    build_frontend_rig,
    build_gradebook_component_optimized,
    build_result_arbiter_rig,
    compact_live_frontend,
    frontend_reference,
)
from littleman.judge import footprint, judge_case, judge_problem
from littleman.server_compat import validate_layout
from littleman.sim import Machine, RunResult

ROOT = Path(__file__).resolve().parent.parent
LIVE = ROOT / "submissions" / "gradebook" / "gradebook_04.man"
PROBLEM = ROOT / "data" / "small" / "problems" / "gradebook.json"


def _trace_frontend(text, rounds):
    """Run only the parser man, replacing workers with lossless trace sinks."""

    parsed = Machine.parse(text)
    frontend = next(
        room
        for room in parsed.rooms
        if len(parsed.in_pipes.get(id(room), ())) == 2
        and len(parsed.out_pipes.get(id(room), ())) == 4
    )
    man = next(man for man in parsed.men if man.room is frontend)
    machine = Machine(parsed.grid, parsed.rooms, [man], parsed.pipes)
    machine._build_literals()
    command_pipes = machine.out_pipes[id(frontend)]
    ack_pipe = next(
        pipe for pipe in machine.in_pipes[id(frontend)] if pipe.source.kind != "input"
    )
    traces = {id(pipe): [] for pipe in command_pipes}
    original_put = machine._pipe_put

    def capture_put(pipe, index, value):
        if id(pipe) in traces:
            assert index == 0
            traces[id(pipe)].append(value)
        else:
            original_put(pipe, index, value)

    machine._pipe_put = capture_put
    machine._input_queue = [int(value) for round_ in rounds for value in round_["in"]]
    machine._controller = None
    result = RunResult(status="tick-cap")
    expected_barriers = len(frontend_reference(rounds))
    boundaries = [0]
    for _ in range(2_000_000):
        result.ticks += 1
        assert machine._tick(result) is None
        if man.blocked and id(ack_pipe) in man.wait_pipes:
            lengths = {len(trace) for trace in traces.values()}
            assert len(lengths) == 1
            boundaries.append(lengths.pop())
            original_put(ack_pipe, -1, 0)
            if len(boundaries) == expected_barriers + 1:
                break
    else:
        pytest.fail("frontend did not reach every acknowledgement barrier")

    return [
        tuple(tuple(trace[start:end]) for start, end in pairwise(boundaries))
        for trace in traces.values()
    ]


def _trace_subject_engine(subject, bursts):
    """Run one live worker with software-backed record and scratch rings."""

    parsed = Machine.parse(LIVE.read_text())
    engine = parsed.rooms[1 + subject]
    scratch = parsed.rooms[5 + subject]
    record = parsed.rooms[9 + subject]
    collector = parsed.rooms[14]
    frontend = parsed.rooms[1]
    command_in = next(p for p in parsed.in_pipes[id(engine)] if p.source is frontend)
    scratch_in = next(p for p in parsed.in_pipes[id(engine)] if p.source is scratch)
    record_in = next(p for p in parsed.in_pipes[id(engine)] if p.source is record)
    ack_in = next(
        (
            p
            for p in parsed.in_pipes[id(engine)]
            if all(p is not known for known in (command_in, scratch_in, record_in))
        ),
        None,
    )
    scratch_out = next(p for p in parsed.out_pipes[id(engine)] if p.dest is scratch)
    record_out = next(p for p in parsed.out_pipes[id(engine)] if p.dest is record)
    result_out = next(p for p in parsed.out_pipes[id(engine)] if p.dest is collector)
    ack_out = next(
        p
        for p in parsed.out_pipes[id(engine)]
        if all(p is not known for known in (scratch_out, record_out, result_out))
    )

    man = next(man for man in parsed.men if man.room is engine)
    machine = Machine(parsed.grid, parsed.rooms, [man], parsed.pipes)
    machine._build_literals()
    queues = {
        id(command_in): deque(value for burst in bursts for value in burst),
        id(scratch_in): deque(),
        id(record_in): deque(),
    }
    if ack_in is not None:
        queues[id(ack_in)] = deque([0] * len(bursts))
    incoming = {
        id(pipe): pipe
        for pipe in (command_in, scratch_in, record_in, ack_in)
        if pipe is not None
    }
    results, acknowledgements = [], []
    original_put = machine._pipe_put

    def capture_put(pipe, index, value):
        assert index == 0
        if pipe is scratch_out:
            queues[id(scratch_in)].append(value)
        elif pipe is record_out:
            queues[id(record_in)].append(value)
        elif pipe is result_out:
            results.append(value)
        elif pipe is ack_out:
            acknowledgements.append(value)
        else:
            original_put(pipe, index, value)

    machine._pipe_put = capture_put
    machine._input_queue = []
    machine._controller = None
    run = RunResult(status="tick-cap")
    for _ in range(2_000_000):
        for pipe_id, queue in queues.items():
            pipe = incoming[pipe_id]
            if queue and pipe.values[-1] is None:
                original_put(pipe, -1, queue.popleft())
        run.ticks += 1
        assert machine._tick(run) is None
        if len(acknowledgements) == len(bursts):
            break
    else:
        pytest.fail(f"subject {subject} did not acknowledge every burst")
    return results, acknowledgements


def test_frontend_reference_normalizes_roster_and_every_operation():
    rounds = [
        {"in": ["2", "2", "1001", "10", "20", "1002", "30", "40"]},
        {
            "in": [
                "4",
                "1",
                "1001",
                "2",
                "2",
                "1002",
                "1",
                "99",
                "3",
                "2",
                "4",
                "1",
            ]
        },
    ]
    bursts = frontend_reference(rounds)
    assert [burst.kind for burst in bursts] == [
        "roster",
        "operation[1]",
        "operation[2]",
        "operation[3]",
        "operation[4]",
    ]
    assert [burst.tokens for burst in bursts] == [
        (2, 1001, 10, 20, 0, 0, 1002, 30, 40, 0, 0),
        (1, 1001, 2, 0),
        (2, 1002, 1, 99),
        (3, 0, 2, 0),
        (4, 0, 1, 0),
    ]


def test_frontend_reference_covers_every_public_case_and_padding_width():
    problem = json.loads(PROBLEM.read_text())
    for case in problem["publicTestData"]:
        bursts = frontend_reference(case["rounds"])
        operation_count = sum(int(round_["in"][0]) for round_ in case["rounds"][1:])
        assert len(bursts) == 1 + operation_count
        assert (len(bursts[0].tokens) - 1) % 5 == 0
        assert all(len(burst.tokens) == 4 for burst in bursts[1:])


def test_live_frontend_matches_reference_at_every_ack_barrier():
    problem = json.loads(PROBLEM.read_text())
    live = LIVE.read_text()
    compact_rig = build_frontend_rig(compact_live_frontend(live))
    for case in problem["publicTestData"]:
        expected = tuple(burst.tokens for burst in frontend_reference(case["rounds"]))
        for text in (live, compact_rig):
            traces = _trace_frontend(text, case["rounds"])
            assert len(traces) == 4
            assert all(trace == expected for trace in traces)


def test_compact_frontend_crops_only_the_blank_bank_suffix():
    live = LIVE.read_text()
    parsed = Machine.parse(live)
    room = parsed.rooms[1]
    compact = compact_live_frontend(live)
    assert room.bottom - room.top + 1 == len(compact) == 115
    assert (len(compact[0]), len(compact)) == (37, 115)
    assert sum(char != " " for row in compact[1:-1] for char in row[1:-1]) == 351
    rig = build_frontend_rig(compact)
    validate_layout(rig)
    assert build_frontend_rig(compact_live_frontend(live)) == rig


@pytest.mark.parametrize(
    ("subject", "initial", "average", "top"),
    [
        (1, 10, 43, 1001),
        (2, 20, 71, 1001),
        (3, 30, 58, 1001),
        (4, 40, 61, 1004),
    ],
)
def test_each_subject_engine_isolated_protocol(subject, initial, average, top):
    roster = (
        4,
        1001,
        10,
        20,
        30,
        40,
        1002,
        30,
        20,
        50,
        40,
        1003,
        20,
        90,
        50,
        10,
        1004,
        30,
        80,
        40,
        99,
    )
    mismatch = subject % 4 + 1
    bursts = (
        roster,
        (1, 1001, subject, 0),
        (2, 1001, subject, 95),
        (1, 1001, subject, 0),
        (3, 0, subject, 0),
        (4, 0, subject, 0),
        (1, 1002, mismatch, 0),
    )
    results, acknowledgements = _trace_subject_engine(subject, bursts)
    assert results == [initial, 95, average, top]
    assert acknowledgements == [0] * len(bursts)


def test_component_optimized_gradebook_is_deterministic_and_better():
    problem = json.loads(PROBLEM.read_text())
    candidate = build_gradebook_component_optimized()
    assert build_gradebook_component_optimized() == candidate
    assert GRADEBOOK_COMPONENT_FOLD_PREFIXES == (
        (2, 24),
        (3, 25),
        (4, 25),
        (5, 26),
        (1, 34),
    )
    assert (max(map(len, candidate.splitlines())), len(candidate.splitlines())) == (
        382,
        307,
    )
    assert footprint(candidate) == 145_924
    report = judge_problem(candidate, problem)
    assert report.cases_passed == report.cases_total == 7
    assert report.case_ticks == [
        25_260,
        78_696,
        82_755,
        66_059,
        91_777,
        42_257,
        281_648,
    ]
    validate_layout(candidate)


@pytest.mark.parametrize(
    "rounds",
    [
        [],
        [{"in": ["2"]}],
        [{"in": ["1", "5", "1001"]}],
        [{"in": ["1", "1", "1001", "10"]}, {"in": ["1", "5"]}],
        [{"in": ["1", "1", "1001", "10"]}, {"in": ["1", "2", "1001"]}],
        [{"in": ["1", "1", "1001", "10"]}, {"in": ["0", "99"]}],
    ],
)
def test_frontend_reference_rejects_malformed_streams(rounds):
    with pytest.raises(ValueError):
        frontend_reference(rounds)


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
