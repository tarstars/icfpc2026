"""Pipes, I/O rooms, blocking. Fixtures are textbook lesson programs."""

from littleman.sim import Machine

IO1 = """\
+-----+
|@3s v|   +-+
|     |>->|O|
|H   <|   +-+
+-----+
"""

IO2 = """\
   +-+
   |I|
   +-+
    v
    v
+-------+  +-+
|@2Wr*sH|>>|O|
+-------+  +-+
"""

PIPES1 = """\
+----+    +---+
|    |    |   |
|@2sH|>-->|@rH|
|    |    |   |
+----+    +---+
"""

TRIANGLE = """\
+-+ +-+
|I| |O|
+-+ +-+
 v   ^
 v   ^
+-------+
|@rM1+*v|
|Hs/W2M<|
+-------+
"""


def test_parse_finds_io_rooms_and_pipe():
    m = Machine.parse(IO1)
    kinds = sorted(r.kind for r in m.rooms)
    assert kinds == ["output", "room"]
    assert len(m.pipes) == 1


def test_output_simple_value():
    m = Machine.parse(IO1)
    res = m.run()
    assert res.status == "halted"
    assert res.output == [3]


def test_input_times_two():
    m = Machine.parse(IO2)
    res = m.run(inputs=[42])
    assert res.status == "halted"
    assert res.output == [84]


def test_value_travels_between_rooms():
    m = Machine.parse(PIPES1)
    res = m.run()
    assert res.status == "halted"
    # receiving man ends with 2 in his main hand
    receiver = max(m.men, key=lambda man: man.c)
    assert receiver.A == 2


def test_receive_blocks_until_value_arrives():
    # receiver executes r long before the value arrives; must block, not error
    m = Machine.parse(PIPES1)
    res = m.run()
    assert res.status == "halted"


def test_triangle_program():
    for n, expected in [(0, 0), (1, 1), (4, 10), (10, 55), (987, 487578)]:
        m = Machine.parse(TRIANGLE)
        res = m.run(inputs=[n])
        assert res.status == "halted", (n, res.error)
        assert res.output == [expected], n


def test_output_emission_tick_recorded():
    m = Machine.parse(IO1)
    res = m.run()
    assert len(res.output_ticks) == 1
    assert 0 < res.output_ticks[0] <= res.ticks
