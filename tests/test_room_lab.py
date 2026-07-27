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
