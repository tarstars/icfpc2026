"""Gates for the pressed Grade Book (`gradebook_03.man`).

The rooms are lifted verbatim out of `gradebook_02.man`, so the tests here
prove three things and nothing else: the rectangles are byte-identical, every
`s`/`r` still binds to a pipe with the same ROLE, and the box got smaller.
"""

import json
import pathlib

import pytest

from littleman import gradebook_press as gp
from littleman import room_ports
from littleman.ir_export import machine_ir
from littleman.judge import judge_problem
from littleman.sim import Machine

REPO = pathlib.Path(__file__).resolve().parent.parent
ARTIFACT = REPO / "submissions" / "gradebook" / "gradebook_03.man"


def grid(text):
    return text.rstrip("\n").split("\n")


def rect(rows, top, left, bottom, right):
    out = []
    for r in range(top, bottom + 1):
        line = rows[r] if r < len(rows) else ""
        line = line + " " * (right + 1 - len(line))
        out.append(line[left:right + 1])
    return out


@pytest.fixture(scope="module")
def pressed():
    return gp.build_pressed_gradebook()


@pytest.fixture(scope="module")
def source():
    return gp.SOURCE.read_text()


def test_matches_shipped_artifact(pressed):
    assert ARTIFACT.read_text() == pressed


def test_deterministic(pressed):
    assert gp.build_pressed_gradebook() == pressed


def test_dimensions(pressed):
    rows = grid(pressed)
    height, width = len(rows), max(len(r) for r in rows)
    assert (width, height) == (390, 404)
    assert max(width, height) < 423
    assert max(width, height) ** 2 == 163216


def test_room_rectangles_are_byte_identical(pressed, source):
    src, dst = grid(source), grid(pressed)
    for name, (top, left, bottom, right) in gp.ROOMS.items():
        row, col = gp.PLACE[name]
        want = rect(src, top, left, bottom, right)
        got = rect(dst, row, col, row + bottom - top, col + right - left)
        assert got == want, name


def name_by_corner(place):
    return {corner: name for name, corner in place.items()}


def role_map(text, place):
    """Every instruction cell keyed by (room, offset) -> op + pipe role."""
    machine = Machine.parse(text)
    names = name_by_corner(place)
    room_name = {id(r): names[(r.top, r.left)] for r in machine.rooms}
    pipes = list(machine.pipes)
    role = {
        i: (room_name[id(p.source)], room_name[id(p.dest)])
        for i, p in enumerate(pipes)
    }
    assert len(set(role.values())) == len(pipes), "pipe roles are not unique"
    rooms = {(r.top, r.left): r for r in machine.rooms}
    out = {}
    for key, entry in machine_ir(text)["resolution"].items():
        r, c = (int(x) for x in key.split(","))
        room = next(
            rm for rm in rooms.values()
            if rm.top < r < rm.bottom and rm.left < c < rm.right
        )
        ids = [entry["pipe"]] if "pipe" in entry else entry["pipes"]
        out[(room_name[id(room)], r - room.top, c - room.left)] = (
            entry["op"], tuple(sorted(role[i] for i in ids if i is not None))
        )
    return out


def test_binding_roles_unchanged(pressed, source):
    before = role_map(source, {n: (b[0], b[1]) for n, b in gp.ROOMS.items()})
    after = role_map(pressed, gp.PLACE)
    assert set(before) == set(after)
    diffs = [k for k in before if before[k] != after[k]]
    assert diffs == []


def test_port_margins(pressed):
    machine = Machine.parse(pressed)
    names = name_by_corner(gp.PLACE)
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
        if not ops:
            continue
        report = room_ports.audit(machine, room, ops)
        worst[names[(room.top, room.left)]] = report["margin"]
    assert min(worst.values()) >= 2, worst


def test_public_cases_pass(pressed):
    spec = REPO / "data" / "small" / "problems" / "gradebook.json"
    report = judge_problem(pressed, json.loads(spec.read_text()))
    assert report.cases_passed == report.cases_total
    assert report.footprint == 163216
