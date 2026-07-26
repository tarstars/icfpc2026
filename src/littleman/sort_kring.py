"""Two parallel sub-ring selection-sort pumps with splitter and merger.

Architecture (sort_08 candidate): the input list of n values is split
round-robin into two independent shrinking-ring selection-sort pumps
(m1 = ceil(n/2), m2 = floor(n/2) values); each pump emits its values in
ascending order followed by a sentinel (16384 > any input value); a
merger performs a standard two-way sorted merge and stops emitting at
the double sentinel.  The pumps run in parallel, so the dominant
A*m(m+1)/2 scan term drops ~4x against ``sort_07``.

Model: T(n) ~ max(split*n, load*m1) + A*m1(m1-1)/2 + pass_c*m1 + tail.
"""

from __future__ import annotations

from .canvas import Canvas

SENTINEL = 16384  # built in-machine by `7M1{{` : ((1) << 7) << 7


def predict_round_ticks(n: int, a: float = 10.6, pass_c: float = 22.0,
                        split_pv: float = 6.0, load_pv: float = 8.0,
                        tail: float = 30.0) -> float:
    m1 = (n + 1) // 2
    return (max(split_pv * n, load_pv * m1) + 10.0
            + a * m1 * (m1 - 1) / 2 + pass_c * m1 + tail)


def _room(interior: list[str]) -> list[str]:
    width = len(interior[0])
    assert all(len(row) == width for row in interior), "ragged interior"
    edge = "+" + "-" * width + "+"
    return [edge] + ["|" + row + "|" for row in interior] + [edge]


# Pump interior, 10x13.  Protocol per round: read count m from the
# splitter pipe (top wall); m==0: emit sentinel, park.  Else stream m
# values to the ring (bottom wall out col 4, back in col 6), then run
# the sort_07 shrinking-ring selection sort; emit mins to the merger
# pipe (bottom wall col 0); after token 0, emit sentinel and park.
#
#  r0  sentinel emitter (W-run): 7 M 1 { { -> A=16384, s, park at r
#  r1  prologue @ r M b d; d BP=m: m>0 turn S, m=0 straight E to r0
#  r2-3   load loop (6 cells) entered via > m with BP=m-1
#  r4  first-pass entry W-run: W b M 1 W -  (A=m-1, B=1, BP=m)
#  r5  E-return corridor to the pass row
#  r6  pass row W-run: m s r M (send token, take first value as min)
#  r7-11  scan loop, verbatim sort_07 rows 6-10
#  r12 token row: r b M 1 W - then a: BP>0 loop via col-8 ascent,
#      BP=0 home via col-9 ascent to the r0 sentinel run
PUMP_INTERIOR = [
    " vs{{1M7<<",
    "@rMbd   ^ ",
    "    >mrsv ",
    "      ^md ",
    " v-W1MbW< ",
    " >      v ",
    " v  Mrsm< ",
    "v amsW<   ",
    "Wa v  +   ",
    "v<>>r-Xv  ",
    "s     ++  ",
    "vsWdms<<  ",
    ">rbM1W- a^",
]

RELAY = [
    "@rv",
    "^s<",
]
