"""Plotter display-driver rooms (WIP). ADDRDRV decode+branch validated."""

from littleman import plotter as P
from littleman.canvas import Canvas
from littleman.sim import Machine


def _addrdrv_harness():
    cv = Canvas()
    cv.put(2, 0, ["+-+", "|I|", "+-+"])
    cv.put(1, 6, P.build_addrdrv())
    cv.put(3, 22, ["+-+", "|O|", "+-+"])
    cv.put(8, 8, ["+---+", "|>@v|", "|^r<|", "+---+"])  # draining sink
    cv.pipe([(3, 3), (3, 5)])       # I -> ADDRDRV in(left)
    cv.pipe([(4, 19), (4, 21)])     # ADDR(right) -> O
    cv.pipe([(6, 10), (7, 10)])     # FWD(bottom) -> sink
    return cv.render()


def test_addrdrv_decodes_and_branches():
    # tokens v = addr+1; -1 = end. Expect decoded addresses at O.
    m = Machine.parse(_addrdrv_harness())
    res = m.run(inputs=[3, 6, 1, -1], max_ticks=500)
    assert res.output == [2, 5, 0]
