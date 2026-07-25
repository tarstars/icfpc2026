"""Gates for the pressed Matrix Multiply (`matmul_03.man`).

`matmul_03` re-places the *same* rooms as the live `matmul_02.man`: only the
A ring, the B ring and the output pipe are re-routed.  These tests prove
four things and nothing else -- every room rectangle is byte-identical,
every `s`/`r` still binds to a pipe with the same ROLE, every pipe keeps its
`matmul_02` length to the cell (so ring capacity and phase are untouched),
and the box got smaller.
"""

import json
import pathlib

import pytest

from littleman import room_ports
from littleman.ir_export import machine_ir
from littleman.judge import judge_problem
from littleman.matmul_press import build_matmul_press
from littleman.sim import Machine

REPO = pathlib.Path(__file__).resolve().parent.parent
LIVE = REPO / "submissions" / "matmul" / "matmul_02.man"
ARTIFACT = REPO / "submissions" / "matmul" / "matmul_03.man"

#: Values in a ring may reach N*M = M*K = 16*16.
RING_CAPACITY = 256


def grid(text):
    return text.rstrip("\n").split("\n")


def rect(rows, room):
    out = []
    for r in range(room.top, room.bottom + 1):
        line = rows[r] if r < len(rows) else ""
        line = line + " " * (room.right + 1 - len(line))
        out.append(line[room.left:room.right + 1])
    return out


def name_of(room):
    """Rooms are keyed by kind and left edge; zone columns are shared."""
    return room.kind if room.kind != "room" else f"room@{room.left}"


def rooms_by_name(machine):
    return {name_of(r): r for r in machine.rooms}


@pytest.fixture(scope="module")
def pressed():
    return build_matmul_press()


@pytest.fixture(scope="module")
def live():
    return LIVE.read_text()


def test_matches_shipped_artifact(pressed):
    assert ARTIFACT.read_text() == pressed


def test_deterministic(pressed):
    assert build_matmul_press() == pressed
    assert build_matmul_press() == pressed


def test_dimensions(pressed):
    rows = grid(pressed)
    height, width = len(rows), max(len(r) for r in rows)
    assert (width, height) == (128, 145)
    assert max(width, height) < 183
    assert max(width, height) ** 2 == 21025


def test_room_rectangles_are_byte_identical(pressed, live):
    src, dst = grid(live), grid(pressed)
    before = rooms_by_name(Machine.parse(live))
    after = rooms_by_name(Machine.parse(pressed))
    assert set(before) == set(after)
    for name, room in before.items():
        assert rect(dst, after[name]) == rect(src, room), name


def role_map(text):
    """Every instruction cell keyed by (room, offset) -> op + pipe roles."""
    machine = Machine.parse(text)
    rooms = list(machine.rooms)
    pipes = list(machine.pipes)
    role = {i: (name_of(p.source), name_of(p.dest)) for i, p in enumerate(pipes)}
    out = {}
    for key, entry in machine_ir(text)["resolution"].items():
        r, c = (int(x) for x in key.split(","))
        room = next(
            rm for rm in rooms if rm.top < r < rm.bottom and rm.left < c < rm.right
        )
        ids = [entry["pipe"]] if "pipe" in entry else entry["pipes"]
        out[(name_of(room), r - room.top, c - room.left)] = (
            entry["op"],
            tuple(sorted(role[i] for i in ids if i is not None)),
        )
    return out


def test_binding_roles_unchanged(pressed, live):
    before, after = role_map(live), role_map(pressed)
    assert set(before) == set(after)
    assert [k for k in before if before[k] != after[k]] == []


def pipe_lengths(text):
    machine = Machine.parse(text)
    counts = {}
    for pipe in machine.pipes:
        counts.setdefault((name_of(pipe.source), name_of(pipe.dest)), []).append(
            len(pipe.cells)
        )
    return {k: sorted(v) for k, v in counts.items()}


def test_pipe_lengths_match_live_exactly(pressed, live):
    """Capacity, ring phase and per-value shift cost are unchanged."""
    assert pipe_lengths(pressed) == pipe_lengths(live)


def test_matrix_rings_hold_a_full_16x16(pressed):
    machine = Machine.parse(pressed)
    rings = sorted(len(p.cells) for p in machine.pipes)[-2:]
    assert min(rings) >= RING_CAPACITY, rings


def test_port_margins(pressed):
    machine = Machine.parse(pressed)
    worst = {}
    for room in machine.rooms:
        if room.kind != "room":
            continue
        ops, seen = [], {}
        for pipe in machine.pipes:
            for cell, outgoing in ((pipe.cells[0], True), (pipe.cells[-1], False)):
                owner = pipe.source if outgoing else pipe.dest
                if owner is not room:
                    continue
                seen[cell] = f"p{len(seen)}"
                ops.append(room_ports.Op(cell, seen[cell], outgoing))
        if ops:
            worst[name_of(room)] = room_ports.audit(machine, room, ops)["margin"]
    assert min(worst.values()) >= 2, worst


def test_public_cases_pass(pressed):
    spec = REPO / "data" / "small" / "problems" / "matmul.json"
    report = judge_problem(pressed, json.loads(spec.read_text()))
    assert report.cases_passed == report.cases_total
    assert report.footprint == 21025
