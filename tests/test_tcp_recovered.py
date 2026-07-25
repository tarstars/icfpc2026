"""Regression tests for the Packet Reassembly platform-source recovery."""

import hashlib
import json
import random
from pathlib import Path

import pytest

from littleman.alexey_tcp_recovered import build_tcp_recovered_best
from littleman.judge import footprint, judge_case, judge_problem
from littleman.server_compat import validate_layout


ROOT = Path(__file__).resolve().parent.parent
PROBLEM = ROOT / "data" / "small" / "problems" / "tcp.json"
SUBMISSIONS = ROOT / "submissions" / "tcp"
RECOVERED = ("tcp_02.man", "tcp_03.man", "tcp_04.man", "tcp_05.man")
HASHES = {
    "tcp_02.man": "61613871dc69a02257008e7c653f801b84d784ca32a0880e1223a409d59467e4",
    "tcp_03.man": "8962e6f2eaa2fecb9e6b64e18fa3302c8d6742d0a723eba2c36caec317c51f86",
    "tcp_04.man": "7868665ea88cb9f888b68f1385efa0a717f915f2b6e93b5ab199d60a83c5b0c2",
    "tcp_05.man": "e5e45693b5949c17c1ef9c70965efb32d2b1f3be273445163aef62da76e06ae1",
}


def _source(name: str) -> str:
    return (SUBMISSIONS / name).read_text()


def _rounds_for_order(order: list[int], n: int) -> list[dict]:
    """Build the exact early-output oracle for one safe arrival order."""

    buffered: dict[int, int] = {}
    expected = 0
    rounds = []
    for round_index, sequence in enumerate(order):
        value = 100 + sequence
        buffered[sequence] = value
        output = []
        while expected in buffered:
            output.append(buffered.pop(expected))
            expected += 1
        inputs = ([n] if round_index == 0 else []) + [sequence, value]
        rounds.append({"in": inputs, "out": output})
    return rounds


def _safe_random_order(n: int, seed: int) -> list[int]:
    rng = random.Random(seed)
    remaining = set(range(n))
    received: set[int] = set()
    expected = 0
    order = []
    while remaining:
        choices = [sequence for sequence in remaining if sequence - expected < 16]
        sequence = rng.choice(choices)
        order.append(sequence)
        remaining.remove(sequence)
        received.add(sequence)
        while expected in received:
            expected += 1
    return order


def _max_delay_sawtooth(n: int) -> list[int]:
    """Alternate the maximum safe lead with the current missing packet."""

    remaining = set(range(n))
    received: set[int] = set()
    expected = 0
    choose_high = True
    order = []
    while remaining:
        high = expected + 15
        sequence = high if choose_high and high in remaining else expected
        if sequence not in remaining:
            sequence = min(remaining)
        order.append(sequence)
        remaining.remove(sequence)
        received.add(sequence)
        while expected in received:
            expected += 1
        choose_high = not choose_high
    return order


def _stress_cases() -> list[list[dict]]:
    fixed = [
        _rounds_for_order(list(range(48)), 48),
        _rounds_for_order(
            [
                *range(15, -1, -1),
                *range(31, 15, -1),
                *range(47, 31, -1),
            ],
            48,
        ),
        [{"in": [17, 16, 116], "out": [-1]}],
        _rounds_for_order([0], 1),
        _rounds_for_order(_max_delay_sawtooth(48), 48),
    ]
    generated = [
        _rounds_for_order(_safe_random_order(48, 20260725 + offset), 48)
        for offset in range(40)
    ]
    return fixed + generated


def test_recovered_hashes_and_duplicate_are_stable():
    for name, expected in HASHES.items():
        digest = hashlib.sha256((SUBMISSIONS / name).read_bytes()).hexdigest()
        assert digest == expected
    assert _source("tcp_05.man") == _source("tcp_01.man")


def test_winning_artifact_matches_structural_generator():
    source = _source("tcp_02.man")
    assert build_tcp_recovered_best() == source
    assert footprint(source) == 38**2


@pytest.mark.parametrize("name", RECOVERED)
def test_recovered_variants_pass_public_and_server_layout(name):
    source = _source(name)
    validate_layout(source)
    problem = json.loads(PROBLEM.read_text())
    report = judge_problem(source, problem)
    assert report.cases_passed == report.cases_total == 6, report.case_results


@pytest.mark.parametrize("name", RECOVERED)
def test_recovered_variants_pass_boundary_stress(name):
    source = _source(name)
    results = [judge_case(source, rounds) for rounds in _stress_cases()]
    assert all(result.passed for result in results), [
        (case_index, result)
        for case_index, result in enumerate(results)
        if not result.passed
    ]
    assert max(result.ticks for result in results) <= {
        "tcp_02.man": 9_720,
        "tcp_03.man": 9_730,
        "tcp_04.man": 10_900,
        "tcp_05.man": 30_306,
    }[name]
