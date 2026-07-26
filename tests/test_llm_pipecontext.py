"""Physical gates for indexed LLM pipe-context packing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat
from littleman.llm_fetchjoin import fetchjoin_reference
from littleman.llm_fuzz import llm_corpus
from littleman.llm_maskmap import maskmap_reference
from littleman.llm_packraw import pack_reference
from littleman.llm_perimeter import perimeter_reference
from littleman.llm_pipecontext import build_pipecontext_rig, pipecontext_reference
from littleman.llm_pipestarts import pipestarts_reference
from littleman.llm_pipetrace import PIPE_END, pipetrace_dest_reference
from littleman.llm_roomfind import roomfind_reference
from littleman.llm_scan import scan_reference
from littleman.llm_statebuild import PIPE_MASK, PIPE_VALUES, statebuild_reference
from littleman.llm_stateindex import INDEX_END, INDEX_SPLIT, stateindex_reference
from littleman.sim import Machine

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/small/problems/little-little-man.json").read_text())[
    "publicTestData"
]
FUZZ = llm_corpus(20260726, 20)


def indexed_state(case):
    source = [int(value) for value in case["rounds"][0]["in"]]
    stream = pack_reference(scan_reference(source))
    stream = roomfind_reference(stream)
    stream = perimeter_reference(stream)
    stream = pipestarts_reference(stream)
    stream = pipetrace_dest_reference(stream)
    stream = statebuild_reference(stream)
    world, state = stream[:64], stream[64:]
    state = fetchjoin_reference([*world, *maskmap_reference(state)])
    return stateindex_reference(state)


def pipe_records(case):
    tokens = indexed_state(case)
    index = tokens.index(INDEX_SPLIT) + 1
    out = []
    while tokens[index] != INDEX_END:
        start = index
        while tokens[index] != PIPE_MASK:
            index += 2
        index += 2
        assert tokens[index] == PIPE_VALUES
        count = tokens[index + 1]
        index += 2 + count
        assert tokens[index] == PIPE_END
        index += 1
        out.extend(tokens[start:index])
    return out


class Script:
    def __init__(self, tokens):
        self.input = list(tokens)
        self.expected = pipecontext_reference(tokens)
        self.output = []

    def pop_input(self):
        return self.input.pop(0) if self.input else None

    def on_output(self, value, _tick):
        self.output.append(value)
        return "passed" if len(self.output) == len(self.expected) else None


@pytest.fixture(scope="module")
def text():
    return build_pipecontext_rig()


def test_generator_is_deterministic_and_server_safe(text):
    assert build_pipecontext_rig() == text
    server_compat.validate_layout(text)
    alexey_pipecheck.check(text)


def test_physical_public_and_fuzz_records(text):
    tokens = [
        item
        for case in [*CASES, *FUZZ]
        for item in pipe_records(case)
    ]
    script = Script(tokens)
    result = Machine.parse(text).run(max_ticks=50_000_000, controller=script)
    assert result.error is None
    assert result.status == "passed"
    assert script.output == script.expected
