"""Packet Reassembly solution tests."""

import json
from pathlib import Path

from littleman.judge import judge_case, judge_problem
from littleman.sim import Machine
from littleman.tcp import build_tcp

PROBLEMS = Path(__file__).resolve().parent.parent / "data" / "small" / "problems"
SUBMISSIONS = Path(__file__).resolve().parent.parent / "submissions" / "tcp"


def test_passes_all_public_cases():
    problem = json.loads((PROBLEMS / "tcp.json").read_text())
    report = judge_problem(build_tcp(), problem)
    assert report.cases_passed == report.cases_total == 6, report.case_results


def test_checked_in_candidate_matches_generator():
    assert (SUBMISSIONS / "tcp_00.man").read_text() == build_tcp()


def test_in_order_two_packets():
    machine = Machine.parse(build_tcp())
    result = machine.run(inputs=[2, 0, 41, 1, 42], max_ticks=20_000)
    assert result.output == [41, 42]


def test_delay_sixteen_emits_loss():
    machine = Machine.parse(build_tcp())
    result = machine.run(inputs=[17, 16, 123], max_ticks=20_000)
    assert result.output == [-1]


def test_three_full_reverse_windows():
    rounds = []
    for block in range(3):
        start = block * 16
        for sequence in range(start + 15, start - 1, -1):
            inputs = [sequence, sequence + 100]
            if not rounds:
                inputs.insert(0, 48)
            outputs = (
                [value + 100 for value in range(start, start + 16)]
                if sequence == start
                else []
            )
            rounds.append({"in": inputs, "out": outputs})
    result = judge_case(build_tcp(), rounds, max_ticks=100_000)
    assert result.passed, result


def test_ring_settling_corridor_is_long_enough():
    machine = Machine.parse(build_tcp())
    ring = [
        pipe
        for pipe in machine.pipes
        if pipe.source.kind == "room" and pipe.dest.kind == "room"
    ]
    round_trip = sum(len(pipe.cells) for pipe in ring) + 8
    insertion_corridor = 5 + 2 + 29 + 2 + 29 + 2 + 29 + 4
    output_corridor = 4 + 31 + 2 + 24 + 4 + 24 + 1
    assert min(insertion_corridor, output_corridor) > round_trip
