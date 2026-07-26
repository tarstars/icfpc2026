"""Tight-loop shrinking-ring selection sort (``sort_07``).

The live artifact ``sort_06.man`` is a shrinking-ring selection sort whose
cost is *purely* the pump walker's step count: profiling shows the pump is
never blocked, so ticks == cells stepped on.  Fitting

    ticks(n) = A * n(n+1)/2 + B * n + C

to measured single-round runs of ``sort_06`` gives A = 18.67, B = 32.7,
C ~ 0.  ``A`` is the length of the scan loop (18 cells on the requeue
branch, 20 on the new-minimum branch) and ``B`` is the per-pass handler
plus the per-value load loop.

This module rebuilds the pump interior with the same protocol and the same
outer geometry (19x19, identical rooms and pipes) but a scan loop of 10/12
cells and a 30-cell pass handler.  Refitting the result gives A = 10.60,
B = 29.64: public average ticks 2,402.43 -> 1,581.57, local score
867,277 -> 570,947 (1.52x) at an unchanged footprint of 361.

Both this program and ``sort_06`` deadlock above 20 values in one list --
the ring pipe plus relay cannot hold n values and the count token -- so the
supported input range is unchanged.

Model helpers below predict a candidate's ticks before any geometry is
drawn; ``fit_model`` recovers A/B/C from measured per-case ticks.
"""

from __future__ import annotations

from .canvas import Canvas


def selection_traversals(n: int) -> int:
    """Value-past-pump events for the shrinking-ring selection sort."""
    return n * (n + 1) // 2


def round_ticks(n: int, a: float, b: float, c: float = 0.0) -> float:
    return a * selection_traversals(n) + b * n + c


def case_ticks(ns, a: float, b: float, c: float = 0.0, d: float = 0.0) -> float:
    return sum(round_ticks(n, a, b, c) for n in ns) + d


def fit_model(cases):
    """Least-squares fit of (a, b, c, d) to [(ns, ticks), ...].

    Pure Python (normal equations + Gaussian elimination) so the model has
    no third-party dependency.
    """
    rows = [
        [float(sum(selection_traversals(n) for n in ns)),
         float(sum(ns)), float(len(ns)), 1.0]
        for ns, _ in cases
    ]
    y = [float(t) for _, t in cases]
    k = 4
    m = [
        [sum(r[i] * r[j] for r in rows) for j in range(k)]
        + [sum(r[i] * t for r, t in zip(rows, y))]
        for i in range(k)
    ]
    for col in range(k):
        piv = max(range(col, k), key=lambda r: abs(m[r][col]))
        m[col], m[piv] = m[piv], m[col]
        if abs(m[col][col]) < 1e-12:
            continue
        for r in range(k):
            if r == col:
                continue
            f = m[r][col] / m[col][col]
            for c in range(col, k + 1):
                m[r][c] -= f * m[col][c]
    return tuple(
        m[i][k] / m[i][i] if abs(m[i][i]) > 1e-12 else 0.0 for i in range(k)
    )


# Pump interior, 12x12.  Column 0 of each string is interior column 0.
#
#  rows 0-1  load loop: read n, park it in B/BP, stream n values to the ring
#  row  2    "go home" corridor for a zero count token
#  rows 3-4  first-pass entry (A = n, BP = n) joining the pass handler
#  row  5    pass handler: A -> A-1, send it as the next count token,
#            take the first ring value as the running minimum
#  rows 6-10 scan loop (10 cells requeue / 12 cells new-minimum)
#  row  11   emit the minimum, read the next count token, test it
PUMP_INTERIOR = [
    ">@rMbm>rsv  ",
    "      ^ md  ",
    "^          <",
    "  v-W1MbW<  ",
    "  >     v   ",
    " v  Mrsm<   ",
    "v amsW<     ",
    "Wa v  +     ",
    "v<>>r-Xv    ",
    "s     ++    ",
    "vsWdms<<    ",
    ">rbM1W- a  ^",
]

RELAY = [
    "+----+",
    "|>s@v|",
    "|^r <|",
    "+----+",
]


def _room(interior: list[str]) -> list[str]:
    width = len(interior[0])
    assert all(len(row) == width for row in interior), "ragged interior"
    edge = "+" + "-" * width + "+"
    return [edge] + ["|" + row + "|" for row in interior] + [edge]


def build_sort_tight() -> str:
    """Assemble the tight-loop pump inside sort_06's outer geometry."""
    canvas = Canvas()
    canvas.put(0, 0, ["+-+", "|I|", "+-+"])
    canvas.put(0, 5, _room(PUMP_INTERIOR))
    canvas.put(14, 0, ["+-+", "|O|", "+-+"])
    canvas.put(14, 13, RELAY)
    canvas.pipe([(1, 3), (1, 4)])
    canvas.pipe([(14, 8), (15, 8), (15, 3)])
    canvas.pipe([(14, 11), (15, 11), (15, 12)])
    canvas.pipe(
        [(16, 12), (16, 11), (17, 11), (17, 5), (16, 5), (16, 10), (14, 10)]
    )
    return canvas.render()
