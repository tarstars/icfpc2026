"""Room behavioural contracts (docs/MANIFEST.md step 1).

The contract is what makes a component library possible: it pins what a
room DOES at its pipe boundary while saying nothing about where its cells
sit, so a mutation is legal exactly when the replayed trace is unchanged.

The ground truth here is a real edit the user made by hand in the visual
editor: `memory_13` -> `tarstars_memory_14` moves twelve cells across three
rows, shortening a hot loop's excursion by five cells each way. Identical
box, identical rooms at identical positions, identical pipe lengths, 2.71%
fewer ticks, and it is live. Function unchanged, speed improved -- exactly
the transformation the library pipeline is meant to find automatically, so
it is the right thing to pin.
"""

import json
import pathlib

import pytest

from littleman import room_lab

REPO = pathlib.Path(__file__).resolve().parent.parent
BEFORE = REPO / "submissions" / "memory" / "memory_13.man"
AFTER = REPO / "submissions" / "memory" / "tarstars_memory_14.man"


def _cases():
    spec = json.loads(
        (REPO / "data" / "small" / "problems" / "memory.json").read_text())
    return spec["publicTestData"][:2]        # two cases is plenty and fast


@pytest.mark.skipif(not (BEFORE.exists() and AFTER.exists()),
                    reason="memory artifacts not in the working tree")
def test_hand_edit_preserves_every_room_contract():
    """The user's 12-cell edit changed speed, not behaviour."""
    cases = _cases()
    before = room_lab.record_all(BEFORE.read_text(), cases)
    after = room_lab.record_all(AFTER.read_text(), cases)
    assert set(before) == set(after)
    for index in sorted(before):
        assert room_lab.same_behaviour(before[index], after[index]), (
            f"room {index} changed behaviour")


@pytest.mark.skipif(not AFTER.exists(), reason="artifact not present")
def test_contract_actually_observes_traffic():
    """A contract of zero events would make `same_behaviour` vacuously true.

    The first version of the recorder hooked `Machine._execute` to attribute
    values to the acting man and silently recorded NOTHING, because
    `Pipe.take` is called from the blocking-resolution path instead. Every
    room here must show real traffic.
    """
    contracts = room_lab.record_all(AFTER.read_text(), _cases())
    assert contracts, "no non-I/O rooms found"
    for index, contract in contracts.items():
        assert contract.events() > 0, f"room {index} recorded no traffic"


@pytest.mark.skipif(not AFTER.exists(), reason="artifact not present")
def test_distinct_rooms_have_distinct_digests():
    """Digests key the component library, so unrelated rooms must not
    collide -- another way the zero-event bug would have hidden itself."""
    contracts = room_lab.record_all(AFTER.read_text(), _cases())
    digests = {i: c.digest() for i, c in contracts.items()}
    assert len(set(digests.values())) > 1, digests


# ---------------------------------------------------------------------------
# Interface metadata: which socket reaches which pipe.
#
# The language never names a connection -- r/R read from the NEAREST incoming
# pipe and s/S write to the nearest outgoing one, by distance from the man's
# own cell. So connection is positional and every reshape re-derives it by
# accident. These tests pin the explicit record that makes a room
# substitutable.
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not AFTER.exists(), reason="artifact not present")
def test_every_room_reports_sockets_and_ports():
    """A port count of zero would make `interface_preserved` far weaker.

    An earlier version tested whether a pipe's end cell was INSIDE the room
    and found none, because a pipe ends one cell OUTSIDE the wall it serves.
    """
    ifaces = room_lab.describe(AFTER.read_text())
    assert ifaces
    for index, iface in ifaces.items():
        assert iface.sockets, f"room {index} has no sockets"
        assert iface.ports, f"room {index} has no ports"
        for socket in iface.sockets:
            assert socket.direction in ("in", "out")
            assert 0 <= socket.row < iface.height
            assert 0 <= socket.col < iface.width


@pytest.mark.skipif(not (BEFORE.exists() and AFTER.exists()),
                    reason="artifacts not present")
def test_the_hand_edit_preserves_every_connection():
    """memory_13 -> memory_14 moves twelve cells and must NOT rewire."""
    assert room_lab.interface_preserved(BEFORE.read_text(),
                                        AFTER.read_text()) == []


@pytest.mark.skipif(not AFTER.exists(), reason="artifact not present")
def test_signature_ignores_position_but_not_wiring():
    """A variant may move its sockets anywhere; it may not change which pipe
    they reach. That freedom is exactly what a packer needs."""
    ifaces = room_lab.describe(AFTER.read_text())
    index = max(ifaces, key=lambda i: len(ifaces[i].sockets))
    iface = ifaces[index]
    moved = room_lab.RoomInterface(
        room_index=iface.room_index, width=iface.width + 3,
        height=iface.height - 1, ports=list(iface.ports),
        sockets=[room_lab.Socket(s.row + 1, s.col + 2, s.glyph, s.direction,
                                 s.pipe) for s in iface.sockets])
    assert moved.signature() == iface.signature()

    rewired = room_lab.RoomInterface(
        room_index=iface.room_index, width=iface.width, height=iface.height,
        ports=list(iface.ports),
        sockets=[room_lab.Socket(s.row, s.col, s.glyph, s.direction,
                                 s.pipe + 1) for s in iface.sockets])
    assert rewired.signature() != iface.signature()
