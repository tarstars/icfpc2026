"""Physical parity for the transient runtime-record stripper."""

from __future__ import annotations

import json
from pathlib import Path

from littleman import alexey_pipecheck, server_compat
from littleman.llm_fetchjoin import fetchjoin_reference
from littleman.llm_fuzz import llm_corpus
from littleman.llm_manmap import manmap_reference
from littleman.llm_packraw import pack_reference
from littleman.llm_perimeter import perimeter_reference
from littleman.llm_pipestarts import pipestarts_reference
from littleman.llm_pipetrace import pipetrace_dest_reference
from littleman.llm_recordstrip import (
    build_recordstrip_rig,
    recordstrip_reference,
)
from littleman.llm_roomfind import roomfind_reference
from littleman.llm_scan import scan_reference
from littleman.llm_statebuild import statebuild_reference
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/small/problems/little-little-man.json").read_text())[
    "publicTestData"
]
FUZZ = llm_corpus(20260726, 20)


def fetched_stream(case):
    source = [int(value) for value in case["rounds"][0]["in"]]
    stream = pack_reference(scan_reference(source))
    stream = roomfind_reference(stream)
    stream = perimeter_reference(stream)
    stream = pipestarts_reference(stream)
    stream = pipetrace_dest_reference(stream)
    return fetchjoin_reference(statebuild_reference(stream))


class Script:
    def __init__(self, stream):
        self.input = list(stream)
        self.expected = recordstrip_reference(stream)
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


def test_physical_state_cycles():
    text = build_recordstrip_rig()
    assert build_recordstrip_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)
    for case in [*CASES, *FUZZ[:10]]:
        stream = manmap_reference(fetched_stream(case))
        script = Script(stream)
        result = Machine.parse(text).run(max_ticks=1_000_000, controller=script)
        assert result.error is None
        assert result.status == "passed", case["name"]
        assert script.output == script.expected
