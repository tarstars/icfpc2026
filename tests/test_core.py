"""Core machine: parsing, movement, halting, hands, arithmetic."""

from littleman.sim import Machine

ROOM = """\
+-----+
|     |
|@  H |
|     |
|     |
+-----+
"""

WALK_LOOP = """\
+---+
|>@v|
|   |
|^ <|
+---+
"""

DIGIT = """\
+----+
|    |
|@4 H|
|    |
+----+
"""

HANDS = """\
+-------+
|       |
|@4  M v|
|       |
|H W  3<|
|       |
+-------+
"""

ARITH = """\
+--------+
|        |
| @3M4+H |
|        |
+--------+
"""

ESCAPE = """\
+-----+
|     |
| @   |
|     |
|     |
+-----+
"""


def test_parse_finds_room_and_man():
    m = Machine.parse(ROOM)
    assert len(m.rooms) == 1
    assert len(m.men) == 1
    man = m.men[0]
    assert man.direction == (0, 1)  # starts facing right
    assert man.A == 0 and man.B == 0 and man.BP == 0


def test_man_walks_right_and_halts():
    m = Machine.parse(ROOM)
    res = m.run()
    assert res.status == "halted"


def test_man_without_halt_hits_wall():
    m = Machine.parse(ESCAPE)
    res = m.run()
    assert res.status == "error"
    assert res.error == "wall"


def test_direction_instructions_keep_man_looping():
    m = Machine.parse(WALK_LOOP)
    res = m.run(max_ticks=100)
    assert res.status == "tick-cap"


def test_digit_loads_into_main_hand():
    m = Machine.parse(DIGIT)
    res = m.run()
    assert res.status == "halted"
    assert m.men[0].A == 4


def test_copy_and_swap_hands():
    # man runs over 4, M copies A->B, then 3 loads A, W swaps -> A=3? no:
    # path: @ 4 . . M v ... down, left: 3 ... W ... H
    # after 4: A=4; M: B=4; 3: A=3; W: A=4,B=3
    m = Machine.parse(HANDS)
    res = m.run()
    assert res.status == "halted"
    assert m.men[0].A == 4
    assert m.men[0].B == 3


def test_addition():
    m = Machine.parse(ARITH)
    res = m.run()
    assert res.status == "halted"
    assert m.men[0].A == 7  # 3 M 4 + -> 4+3
