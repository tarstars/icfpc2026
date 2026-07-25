"""Assembly harness gates: rooms lifted byte-identical, pipes routed right."""

from __future__ import annotations

import pathlib

import pytest

from littleman import lllm_assemble as A
from littleman import lllm_classify, lllm_draw, lllm_fetch, lllm_scan, lllm_step
from littleman.sim import Machine

ARTIFACT = pathlib.Path("submissions/lllm/lllm_00.man")


@pytest.fixture(scope="module")
def text() -> str:
    return A.build_machine()


@pytest.fixture(scope="module")
def machine(text) -> Machine:
    return Machine.parse(text)


def _rows(room) -> list[str]:
    return room if isinstance(room, list) else room.render()


@pytest.mark.parametrize(
    "name, builder",
    [
        ("SCAN", lambda: lllm_scan.build_scan_room()),
        ("SCANRELAY", lambda: lllm_scan.build_relay()),
        ("CLASSIFY", lambda: lllm_classify.build_classify_room()),
        ("FETCH", lambda: lllm_fetch.build_fetch().render()),
        ("FETCHRELAY", lambda: lllm_fetch.build_relay().render()),
        ("STEP", lambda: lllm_step.build_step_room().render()),
        ("STEPRELAY", lambda: lllm_step.build_step_relay().render()),
        ("DIST", lambda: lllm_draw.build_dist()),
        ("ADDRDRV", lambda: lllm_draw.build_addrdrv()),
        ("DATADRV", lambda: lllm_draw.build_datadrv()),
        ("SWAPDRV", lambda: lllm_draw.build_swapdrv()),
    ],
)
def test_room_is_byte_identical_to_its_source(text, name, builder):
    """Placement may move a room; it may never change one byte of it."""
    anchor = {v: k for k, v in A.room_anchors().items()}[name]
    want = _rows(builder())
    got = A.extract_room(text, anchor[0], anchor[1], len(want), len(want[0]))
    assert got == [line.ljust(len(want[0])) for line in want]


def test_every_component_is_present_exactly_once(machine):
    names = sorted(A.label_rooms(machine).values())
    assert names == sorted(A.room_anchors().values())


def test_topology_matches_the_work_order(machine):
    links = set(A.pipe_names(machine).values())
    for edge in (
        "I->SCAN", "SCAN->CLASSIFY", "CLASSIFY->STEP",
        "STEP->FETCH", "FETCH->STEP",
        "FETCH->FETCHRELAY", "FETCHRELAY->FETCH",
        "STEP->DIST", "DIST->ADDRDRV", "ADDRDRV->DATADRV",
        "DATADRV->SWAPDRV", "ADDRDRV->DISPLAY", "DATADRV->DISPLAY",
        "SWAPDRV->DISPLAY",
    ):
        assert edge in links, edge


def test_no_output_room(machine):
    assert all(room.kind != "output" for room in machine.rooms)
    assert sum(room.kind == "display" for room in machine.rooms) == 1


def test_fetch_relay_ring_is_at_least_70_cells(machine):
    assert A.ring_cells(machine, "FETCH", "FETCHRELAY") >= 70


def test_no_one_cell_pipes(machine):
    assert min(len(p.cells) for p in machine.pipes) >= 2


def test_no_shared_walls(text):
    from littleman import server_compat

    server_compat.validate_layout(text)


def test_step_bypass_and_display_bands_are_disjoint(machine):
    """Fixed cross-band routes must stay outside the completed STEP room."""
    names = A.label_rooms(machine)
    step = next(room for room in machine.rooms if names[id(room)] == "STEP")
    draw_rooms = [
        room for room in machine.rooms
        if names[id(room)] in {"DIST", "ADDRDRV", "DATADRV", "SWAPDRV", "DISPLAY"}
    ]
    assert step.bottom < A.ROW_LOAD_FAR
    assert A.ROW_LOAD_FAR < min(room.top for room in draw_rooms)


def test_port_binding_margins_are_at_least_two(text):
    for line in A.audit_ports(text):
        margin = int(line.split("margin=")[1].split()[0])
        assert margin >= 2, line


def test_artifact_on_disk_matches_the_builder(text):
    assert ARTIFACT.exists(), "run scripts/build_lllm.py"
    assert ARTIFACT.read_text() == text


def test_50_fuzz_cases_pass_the_complete_machine(text):
    from littleman.judge import normalize_case
    from littleman.llm_fuzz import corpus
    from littleman.server_compat import judge_case

    failures = []
    for i, case in enumerate(corpus(20260726, 50)):
        result = judge_case(text, normalize_case(case), max_ticks=1_000_000)
        if not result.passed:
            failures.append((i, result.reason, result.ticks))
    assert failures == []
