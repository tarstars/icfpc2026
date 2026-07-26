"""Directed and physical parity for one interpreted non-pipe man tick."""

from __future__ import annotations

import random

from littleman import alexey_pipecheck, server_compat
from littleman.llm_components import (
    CLASS_ADD,
    CLASS_BRANCH,
    CLASS_DIGIT,
    CLASS_HALT,
    CLASS_HEADING,
    CLASS_M,
    CLASS_RECV,
    CLASS_SEND,
    CLASS_SPACE,
    CLASS_SUB,
)
from littleman.llm_manstep import (
    build_manstep_rig,
    manstep_reference,
)
from littleman.sim import Machine


def cases():
    rng = random.Random(20260726)
    result = []
    for cls in (
        CLASS_SPACE,
        CLASS_HEADING,
        CLASS_DIGIT,
        CLASS_M,
        CLASS_ADD,
        CLASS_SUB,
        CLASS_BRANCH,
        CLASS_HALT,
        CLASS_SEND,
        CLASS_RECV,
    ):
        values = range(4) if cls == CLASS_HEADING else range(10)
        for value in values:
            for ai in (-9, 0, 11):
                state = [
                    rng.randrange(4),
                    rng.randrange(17, 230),
                    rng.randrange(-20, 21),
                    ai,
                    rng.randrange(256),
                    rng.randrange(101),
                ]
                color = rng.randrange(16)
                record = color * 256 + cls * 16 + value
                result.append((state, record))
    return result


class Script:
    def __init__(self, requests):
        self.input = [value for state, record in requests for value in [*state, record]]
        self.expected = [
            value
            for state, record in requests
            for value in manstep_reference(state, record)
        ]
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


def test_physical_directed_parity_and_layout():
    text = build_manstep_rig()
    assert build_manstep_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)
    requests = cases()
    script = Script(requests)
    result = Machine.parse(text).run(max_ticks=5_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected


def test_wrap_and_branch_edges():
    assert manstep_reference(
        [1, 100, 1, (1 << 63) - 1, 100, 1],
        CLASS_ADD * 16,
    )[3] == -(1 << 63)
    assert manstep_reference([0, 100, 0, -1, 100, 1], CLASS_BRANCH * 16)[:2] == [
        3,
        99,
    ]
