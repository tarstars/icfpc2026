"""Unit tests for the memory solution's building blocks.

Each room of the memory pipeline is exercised standalone inside a tiny
harness program (I room -> room under test -> O room).
"""

from littleman.canvas import Canvas
from littleman.memory import build_newh_room, build_relay_init_room
from littleman.sim import Machine


def harness(room_rows, in_attach, out_attach):
    """Wrap a room (list of strings) with I and O rooms on the left."""
    cv = Canvas()
    # I room feeding the room's left wall, O room fed from its right wall
    cv.put(0, 5, room_rows)
    room_h = len(room_rows)
    room_w = max(len(r) for r in room_rows)
    cv.put(in_attach, 0, ["+-+", "|I|", "+-+"])
    cv.pipe([(in_attach + 1, 3), (in_attach + 1, 4)])
    cv.put(out_attach, 5 + room_w + 2, ["+-+", "|O|", "+-+"])
    cv.pipe(
        [(out_attach + 1, 5 + room_w), (out_attach + 1, 5 + room_w + 1)]
    )
    return cv.render()


def test_newh_room_sends_initial_zero_then_increments_mod_100():
    rows = build_newh_room()
    text = harness(rows, in_attach=0, out_attach=0)
    m = Machine.parse(text)
    res = m.run(inputs=[5, 99, 42], max_ticks=2000)
    # prologue emits the initial head pointer 0, then (addr+1) % 100
    assert res.output == [0, 6, 0, 43]


def test_relay_init_room_sends_100_zeros_then_relays():
    rows = build_relay_init_room()
    text = harness(rows, in_attach=len(rows) - 3, out_attach=0)
    m = Machine.parse(text)
    res = m.run(inputs=[7, 8], max_ticks=5000)
    assert len(res.output) >= 102
    assert res.output[:100] == [0] * 100
    assert res.output[100:102] == [7, 8]
