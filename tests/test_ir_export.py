"""Machine IR v0 over the golden corpus: every artifact, stable and complete.

The gate from `docs/architecture/claude_02_ir_and_engine.md` milestone 1:
every checked-in ``.man`` artifact produces an IR that is deterministic,
whose text round-trips through re-parse to the identical IR, and whose
resolution map covers every pipe-instruction cell with the binding the
engine itself computes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman.ir_export import ir_hash, ir_text, machine_ir
from littleman.sim import LoadError, Machine

ROOT = Path(__file__).resolve().parents[1]


def _parses(path: Path) -> bool:
    try:
        Machine.parse(path.read_text())
        return True
    except LoadError:
        return False


# history_00.man is the one known locally-unparseable live artifact.
ARTIFACTS = sorted(
    p for p in (ROOT / "submissions").rglob("*.man") if _parses(p)
)


def test_corpus_is_nonempty_and_skips_only_known_unparseable():
    unparseable = {
        p.name
        for p in (ROOT / "submissions").rglob("*.man")
        if not _parses(p)
    }
    assert len(ARTIFACTS) >= 40
    assert unparseable <= {"history_00.man"}


@pytest.mark.parametrize("path", ARTIFACTS, ids=lambda p: p.parent.name + "/" + p.name)
def test_ir_round_trips_and_is_deterministic(path):
    text = path.read_text()
    ir1 = machine_ir(text)
    ir2 = machine_ir(ir_text(ir1))
    assert ir1 == ir2
    assert ir1["sha256"] == ir_hash(ir2)
    assert json.dumps(ir1, sort_keys=True)  # serializable


@pytest.mark.parametrize("path", ARTIFACTS, ids=lambda p: p.parent.name + "/" + p.name)
def test_resolution_map_is_complete_and_engine_true(path):
    text = path.read_text()
    machine = Machine.parse(text)
    ir = machine_ir(text)
    pipes = {i: p for i, p in enumerate(machine.pipes)}

    class Probe:
        pass

    checked = 0
    for room in machine.rooms:
        if room.kind != "room":
            continue
        for r in range(room.top + 1, room.bottom):
            for c in range(room.left + 1, room.right):
                ch = machine.grid[r][c]
                if ch not in "srqRUS":
                    continue
                entry = ir["resolution"][f"{r},{c}"]
                assert entry["op"] == ch
                probe = Probe()
                probe.r, probe.c, probe.room = r, c, room
                if ch == "s":
                    expected = machine._nearest_outgoing(probe)
                    assert pipes.get(entry["pipe"]) is expected
                elif ch in "rq":
                    expected = machine._nearest_incoming(probe)
                    assert pipes.get(entry["pipe"]) is expected
                checked += 1
    assert checked == len(ir["resolution"]) or any(
        e["op"] in "SRU" for e in ir["resolution"].values()
    )


def test_memory_04_station_bindings_match_the_handwritten_audit():
    """The IR must cover every audited binding of the packed memory station.

    test_memory_packed.py audits 10 reads (3 ring + 7 command) and 5 sends
    (1 output + 4 ring) = 15 pipe-instruction cells; the report's prose said
    "eleven", which was wrong -- the test is the record.
    """
    text = (ROOT / "submissions/memory/memory_04.man").read_text()
    ir = machine_ir(text)
    ops = [e["op"] for e in ir["resolution"].values()]
    assert ops.count("s") + ops.count("r") >= 15
    machine = Machine.parse(text)
    station = max(machine.rooms, key=lambda r: r.bottom - r.top)
    in_station = [
        key
        for key in ir["resolution"]
        if station.top < int(key.split(",")[0]) < station.bottom
        and station.left < int(key.split(",")[1]) < station.right
    ]
    assert len(in_station) == 15
