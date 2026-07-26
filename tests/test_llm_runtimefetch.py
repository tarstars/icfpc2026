"""Physical parity for the combined runtime-world fetch encoding."""

from __future__ import annotations

import json
from pathlib import Path

from littleman import alexey_pipecheck, server_compat
from littleman.llm import program_grid
from littleman.llm_packraw import pack_reference
from littleman.llm_runtimefetch import (
    build_runtimefetch_rig,
    runtimefetch_reference,
)
from littleman.llm_scan import scan_reference
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/small/problems/little-little-man.json").read_text())[
    "publicTestData"
]
REQUESTS = list(range(256))


def world_of(case):
    rows = program_grid([int(value) for value in case["rounds"][0]["in"]])
    source = [len(rows[0]), len(rows), *map(ord, "".join(rows))]
    return pack_reference(scan_reference(source))[:64]


class Script:
    def __init__(self, world):
        self.input = [*world, *REQUESTS]
        self.expected = runtimefetch_reference(world, REQUESTS)
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


def test_runtimefetch_public_parity_and_layout():
    text = build_runtimefetch_rig()
    assert build_runtimefetch_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)
    for case in CASES:
        world = world_of(case)
        script = Script(world)
        result = Machine.parse(text).run(max_ticks=8_000_000, controller=script)
        assert result.error is None
        assert result.status == "passed", case["name"]
        assert script.output == script.expected
