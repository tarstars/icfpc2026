"""Backpack control flow, X turning, and backtick numeric literals."""

import pytest

from littleman.sim import LoadError, Machine

LITERALS1 = """\
+---------+  +-+
|@`123`s H|>>|O|
+---------+  +-+
"""

LOOP = """\
+------+  +-+
|@3b5v |>>|O|
| >  v |  +-+
|Hdms< |
+------+
"""

TURNING = """\
+-+
|I|
+-+
 v
 v
+-------+
|  H    |
|  s    |
|  9    |  +-+
|@rX0sH |>>|O|
|  1    |  +-+
|  s    |
|  H    |
+-------+
"""

BACKPACK_BINARY = """\
+---------+
|         |
|    >  x |
|    ]  ] |
| @2bx  H |
|         |
+---------+
"""

VERTICAL_LITERAL = """\
+-----+  +-+
|@  v |>>|O|
|   ` |  +-+
|   1 |
|   2 |
|   ` |
|   s |
|   H |
+-----+
"""

UNMATCHED = """\
+------+
|@`12 H|
+------+
"""


def test_horizontal_literal_loads_and_outputs():
    res = Machine.parse(LITERALS1).run()
    assert res.status == "halted"
    assert res.output == [123]


def test_backpack_loop_outputs_three_times():
    res = Machine.parse(LOOP).run()
    assert res.status == "halted"
    assert res.output == [5, 5, 5]


@pytest.mark.parametrize("n,expected", [(4, 1), (-4, 9), (0, 0)])
def test_turning_on_sign(n, expected):
    res = Machine.parse(TURNING).run(inputs=[n])
    assert res.status == "halted"
    assert res.output == [expected]


def test_backpack_even_odd_walk():
    m = Machine.parse(BACKPACK_BINARY)
    res = m.run()
    assert res.status == "halted"
    assert m.men[0].BP == 0


def test_vertical_literal_walked_downward():
    res = Machine.parse(VERTICAL_LITERAL).run()
    assert res.status == "halted"
    assert res.output == [12]


def test_unmatched_backtick_is_load_error():
    with pytest.raises(LoadError):
        Machine.parse(UNMATCHED)
