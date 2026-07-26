"""Physical parity for raw-world static-color fetch."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm import program_grid
from littleman.llm_colorfetch import build_colorfetch_rig, colorfetch_reference
from littleman.llm_packraw import pack_reference
from littleman.llm_scan import scan_reference
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/small/problems/little-little-man.json").read_text())[
    "publicTestData"
]
REQUESTS = [addr * 16 for addr in range(256)]


def world_of(case):
    rows = program_grid([int(value) for value in case["rounds"][0]["in"]])
    source = [len(rows[0]), len(rows), *map(ord, "".join(rows))]
    return pack_reference(scan_reference(source))[:64]


class Script:
    def __init__(self, world):
        self.input = [*world, *REQUESTS]
        self.expected = colorfetch_reference(world, REQUESTS)
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_colorfetch_rig()


def test_generator_is_deterministic_and_server_safe(text):
    assert build_colorfetch_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_public_all_addresses(text, case):
    world = world_of(case)
    script = Script(world)
    result = Machine.parse(text).run(max_ticks=8_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected
