"""The compact LLLM re-placement must be behaviour-identical to lllm_02.man.

Every check here is a rigid-motion invariant: rooms byte-identical, every
`s`/`r`/`q`/`S`/`R`/`U` bound to the same pipe ROLE, port margins no worse,
and the FETCH<->RELAY ring still >= 70 cells.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from littleman import lllm_assemble as A  # noqa: E402
from littleman import lllm_press as P  # noqa: E402
from littleman.ir_export import machine_ir  # noqa: E402
from littleman.sim import Machine  # noqa: E402

BASE = pathlib.Path(__file__).resolve().parents[1] / "submissions/lllm/lllm_02.man"


def _rekey(text: str, anchors) -> tuple[dict, dict]:
    """IR resolution and pipe roles keyed by (room name, offset in room)."""
    machine = Machine.parse(text)
    names = A.label_rooms(machine)
    boxes = [
        (names[id(rm)], rm.top, rm.left, rm.bottom, rm.right) for rm in machine.rooms
    ]
    pipes = list(machine.pipes)
    roles = {
        i: f"{names[id(p.source)]}->{names[id(p.dest)]}" for i, p in enumerate(pipes)
    }
    ir = machine_ir(text)
    out = {}
    for key, entry in ir["resolution"].items():
        r, c = (int(x) for x in key.split(","))
        name, top, left = next(
            (n, t, l) for n, t, l, b, ri in boxes if t <= r <= b and l <= c <= ri
        )
        val = dict(entry)
        if "pipe" in val:
            val["pipe"] = roles.get(val["pipe"])
        if "pipes" in val:
            val["pipes"] = sorted(roles[i] for i in val["pipes"])
        out[(name, r - top, c - left)] = val
    shapes = {}
    for name, top, left, bottom, right in boxes:
        rows = machine.grid[top:bottom + 1]
        shapes[name] = ["".join(row[left:right + 1]) for row in rows]
    return out, shapes


def _with_anchors(anchors):
    saved = A.room_anchors
    A.room_anchors = anchors
    return saved


def test_press_preserves_every_binding_and_room():
    old_anchors = _with_anchors(A.room_anchors)
    base_res, base_rooms = _rekey(BASE.read_text(), A.room_anchors)
    A.room_anchors = P.room_anchors
    try:
        new_text = P.build_machine()
        new_res, new_rooms = _rekey(new_text, P.room_anchors)
    finally:
        A.room_anchors = old_anchors

    assert sorted(base_rooms) == sorted(new_rooms)
    for name in base_rooms:
        assert base_rooms[name] == new_rooms[name], f"room {name} changed"
    assert set(base_res) == set(new_res)
    diffs = [k for k in base_res if base_res[k] != new_res[k]]
    assert diffs == [], f"{len(diffs)} pipe-role diffs, e.g. {diffs[:5]}"


def test_press_geometry_and_ring():
    old_anchors = _with_anchors(P.room_anchors)
    try:
        text = P.build_machine()
        machine = Machine.parse(text)
        assert A.ring_cells(machine, "FETCH", "FETCHRELAY") >= 70
        step_margins = [
            line for line in A.audit_ports(text) if line.strip().startswith("STEP")
        ]
        for line in step_margins:
            assert int(line.split("margin=")[1].split()[0]) >= 2, line
    finally:
        A.room_anchors = old_anchors
    lines = text.rstrip("\n").split("\n")
    assert max(len(x) for x in lines) < 775
    assert len(lines) < 775
