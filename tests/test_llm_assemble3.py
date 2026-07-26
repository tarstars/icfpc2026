"""LLM3 assembly gates: rooms lifted byte-identical, pipes routed right."""

from __future__ import annotations

import pathlib

import pytest

from littleman import llm_assemble3 as A
from littleman import lllm_draw, lllm_fetch, lllm_scan, lllm_step, llm_scan3
from littleman.memory import P3R, P3W
from littleman.sim import Machine

ARTIFACT = pathlib.Path("submissions/llm/llm3_00.man")


@pytest.fixture(scope="module")
def spec() -> dict:
    return A.step3_spec()


@pytest.fixture(scope="module")
def built(spec):
    return A.assemble(spec)


@pytest.fixture(scope="module")
def text(built) -> str:
    return built[0]


@pytest.fixture(scope="module")
def anchors(built) -> dict:
    return built[1]


@pytest.fixture(scope="module")
def machine(text) -> Machine:
    return Machine.parse(text)


def _rows(room):
    return room if isinstance(room, list) else room.render()


BUILDERS = {
    "S1": lambda s: lllm_scan.build_scan_room_v2(),
    "S1RING": lambda s: lllm_scan.build_relay(),
    "SR": lambda s: llm_scan3.build_sr_room(),
    "SRRING": lambda s: lllm_scan.build_relay(),
    "P1": lambda s: llm_scan3._compile3(llm_scan3._build_p1_asm(3).fsm()),
    "MEMW": lambda s: P3W,
    "MEMR": lambda s: P3R,
    "MEM312": lambda s: llm_scan3.RELAY312,
    "S2": lambda s: llm_scan3.build_s2_room(),
    "S2RING": lambda s: lllm_scan.build_relay(),
    "STEP3": lambda s: s["rows"],
    "FETCH": lambda s: lllm_fetch.build_fetch(),
    "FETCHRELAY": lambda s: lllm_fetch.build_relay(),
    "STEP3RELAY": lambda s: lllm_step.build_step_relay(),
    "DIST": lambda s: lllm_draw.build_dist(),
    "ADDRDRV": lambda s: lllm_draw.build_addrdrv(),
    "DATADRV": lambda s: lllm_draw.build_datadrv(),
    "SWAPDRV": lambda s: lllm_draw.build_swapdrv(),
}


@pytest.mark.parametrize("name", sorted(BUILDERS))
def test_room_is_byte_identical_to_its_source(text, anchors, spec, name):
    """Placement may move a room; it may never change one byte of it."""
    anchor = {v: k for k, v in anchors.items()}[name]
    want = _rows(BUILDERS[name](spec))
    got = A.extract_room(text, anchor[0], anchor[1], len(want), len(want[0]))
    assert got == [line.ljust(len(want[0])) for line in want]


def test_every_component_is_present_exactly_once(machine, anchors):
    names = sorted(A.label_rooms(machine, anchors).values())
    assert names == sorted(anchors.values())
    assert not any(n.startswith("?@") for n in names)


def test_topology_matches_the_work_order(machine, anchors):
    links = set(A.pipe_names(machine, anchors).values())
    for edge in (
        "I->S1", "S1->S1RING", "S1RING->S1", "S1->SR",
        "SR->SRRING", "SRRING->SR", "SR->P1",
        "P1->MEMW", "MEMW->MEMR", "MEMR->MEM312", "MEM312->MEMW",
        "MEMR->P1", "P1->S2", "S2->S2RING", "S2RING->S2",
        "S2->STEP3", "STEP3->FETCH", "FETCH->STEP3",
        "FETCH->FETCHRELAY", "FETCHRELAY->FETCH",
        "STEP3->STEP3RELAY", "STEP3RELAY->STEP3",
        "STEP3->DIST", "DIST->ADDRDRV", "ADDRDRV->DATADRV",
        "DATADRV->SWAPDRV", "ADDRDRV->DISPLAY", "DATADRV->DISPLAY",
        "SWAPDRV->DISPLAY",
    ):
        assert edge in links, edge


def test_frame_judged_no_output_room(machine):
    assert all(room.kind != "output" for room in machine.rooms)
    assert sum(room.kind == "display" for room in machine.rooms) == 1


def test_server_layout_and_io_pipe_rule(text):
    from littleman import server_compat

    server_compat.validate_layout(text)


def test_ring_and_pipe_capacities(machine, anchors):
    assert A.ring_cells(machine, anchors, "FETCH", "FETCHRELAY") >= 70
    assert A.ring_cells(machine, anchors, "STEP3", "STEP3RELAY") >= 20
    names = A.pipe_names(machine, anchors)
    mem = sum(len(p.cells) for p in machine.pipes
              if names[id(p)] in ("MEMR->MEM312", "MEM312->MEMW")
              or (names[id(p)] == "MEMW->MEMR" and len(p.cells) > 3))
    assert mem >= 314, "312-slot memory ring must hold every slot"
    load = next(p for p in machine.pipes if names[id(p)] == "S2->STEP3")
    assert len(load.cells) >= 84, "whole 68+8P stream must fit in flight"
    assert min(len(p.cells) for p in machine.pipes) >= 2


def test_binding_audit_margins(text, anchors):
    """ir_export resolution + room_ports margins: >= 2 everywhere except
    MEMW, which inherits the proven SCAN3 rig's own margin-1 binding."""
    for line in A.binding_audit(text, anchors):
        room = line.split()[0]
        if "NO pipe" in line:
            assert room == "STEP3", line  # mid-transcription only
            continue
        margin = int(line.split("margin=")[1].split()[0])
        assert margin >= (1 if room == "MEMW" else 2), line


def test_artifact_on_disk_matches_the_builder(text):
    assert ARTIFACT.exists(), "run scripts/build_llm3.py"
    assert ARTIFACT.read_text() == text


def test_stream_section_labels():
    rows = ["+--+", "|@ |", "|  |", "+--+"]
    assert A.stream_section(rows, 0).startswith("world word 0")
    assert A.stream_section(rows, 65) == "man addr 1"
    assert A.stream_section(rows, 67) == "pipe count"
    assert A.stream_section(rows, 68) == "round-2 k value"
