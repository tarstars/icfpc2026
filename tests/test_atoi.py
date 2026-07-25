"""Gates for the atoi machine: public cases, fuzz, determinism, bindings."""

import json
import random
from pathlib import Path

from littleman.atoi import build_atoi
from littleman.judge import footprint, judge_case, judge_problem, normalize_case
from littleman.ir_export import machine_ir
from littleman.room_ports import Op, audit
from littleman.sim import Machine

REPO = Path(__file__).resolve().parent.parent
ARTIFACT = REPO / "submissions" / "atoi" / "atoi_00.man"
PROBLEM = json.loads((REPO / "data" / "small" / "problems" / "atoi.json").read_text())


def _rounds(numbers):
    rounds = []
    for value in numbers:
        text = str(value)
        rounds.append(
            {
                "in": [str(len(text))] + [str(ord(ch)) for ch in text],
                "out": [str(int(text))],
            }
        )
    return rounds


def test_artifact_reproducible_and_deterministic():
    text = build_atoi()
    assert text == build_atoi()  # determinism
    assert ARTIFACT.read_text() == text  # byte-for-byte


def test_public_cases_pass():
    report = judge_problem(build_atoi(), PROBLEM)
    assert report.cases_passed == report.cases_total
    assert report.footprint == footprint(build_atoi())


def test_fuzz_against_python_int():
    rng = random.Random(20260725)
    numbers = ["0", "5", "9", "10", "0000000000", "0000000001", "2147483647",
               "1000000000", "0123456789", "9999999999"[:10]]
    while len(numbers) < 40:
        n = rng.randint(1, 10)
        digits = "".join(rng.choice("0123456789") for _ in range(n))
        if int(digits) <= 2**31 - 1:
            numbers.append(digits)
    assert any(len(x) == 1 for x in numbers) and any(len(x) == 10 for x in numbers)
    text = build_atoi()
    # one long multi-round case exercises round chaining as well
    result = judge_case(text, _rounds(numbers))
    assert result.passed, result.reason
    for value in numbers:  # and each on its own
        single = judge_case(text, _rounds([value]))
        assert single.passed, (value, single.reason)


def test_bindings_and_margins():
    """Every r/s in the pump resolves to its intended pipe, with slack >= 2."""
    text = build_atoi()
    ir = machine_ir(text)
    for room in ir["rooms"]:
        for cell in room.get("resolution", {}).values():
            assert cell.get("pipe") is not None, cell
    machine = Machine.parse(text)
    pump = max(
        (rm for rm in machine.rooms if rm.kind == "room"),
        key=lambda rm: (rm.right - rm.left) * (rm.bottom - rm.top),
    )
    top, left = pump.top, pump.left
    ops = [
        Op((top + 1, left + 3), "in", False),    # header `r` (reads n)
        Op((top + 2, left + 10), "in", False),   # loop-head `r` (reads a byte)
        Op((top + 2, left + 2), "out", True),    # exit-lane `s`
    ]
    report = audit(machine, pump, ops)
    assert report["satisfied"], report["positions"]
    assert report["margin"] >= 2, report["margin"]


def test_single_round_cases_from_spec():
    for case in PROBLEM["publicTestData"]:
        result = judge_case(build_atoi(), normalize_case(case))
        assert result.passed, (case["name"], result.reason)
