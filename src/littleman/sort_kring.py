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


# Pump interior, 10x13.  Protocol per round: read count m from the feed
# pipe; m == 0: emit the sentinel and park.  Otherwise stream m values
# into the ring, run the sort_07 shrinking-ring selection sort, emit the
# minima to the merger, and after the 0 token emit the sentinel and park.
#
#  r0  sentinel run (W): @ v s { { 1 M 7 <  -- boot and end-of-round path
#      converge on the `v`, which drops onto the r1 `>`
#  r1  prologue: > r M b m X; X on A=m: m>0 turn S into the load loop,
#      m==0 straight E into the col-9 home ascent
#  r2-3 load loop (W-run r s, return E-run through m, `a` is the test)
#  r4-5 first-pass entry: W b M / 1 W -  (A=m-1, B=1, BP=m)
#  r6  pass row (W): m s r M -- send the next token, take the first
#      ring value as the running minimum
#  r7-11 scan loop, verbatim sort_07 rows 6-10
#  r12 token row: r b M 1 W - then `a`: BP>0 re-enters the pass row by
#      the col-8 ascent, BP==0 goes home by the col-9 ascent
PUMP_INTERIOR = [
    " @vs{{1M7<",
    "  >rMbmX ^",
    "    vsr<  ",
    "    am ^  ",
    "vMbW<     ",
    ">1W-    v ",
    " v  Mrsm< ",
    "v amsW<   ",
    "Wa v  +   ",
    "v<>>r-Xv  ",
    "s     ++  ",
    "vsWdms<<  ",
    ">rbM1W- a^",
]

RELAY = [
    "@>rv",
    " ^s<",
]

# Merger interior, 16x6.  Lane A arrives on the LEFT wall, lane B on the
# RIGHT wall, the sorted stream leaves through the bottom wall.  Pump A
# prefixes its stream with the round's total count n, so the merger emits
# exactly n values and never reads past either sentinel.
#
#  r0  prologue: r n, b (BP=n), r a, M, ... r b, W  -> A=a, B=b
#  r1  "emit b" arm (a > b): W s + M r W, then the shared tail
#  r2  compare row (W-run): d test, m, ... , -, X
#  r3  "emit a" arm (a <= b): + s r, then down to the return corridor
#  r4  return corridor (E-run) climbing back into the tail
#  r5  end-of-round path back to the prologue up column 0
MERGER = [
    ">@rbrM       rWv",
    "      >Ws+MrW> v",
    "     vX-      md",
    " vrs+<<         ",
    " >           ^  ",
    "^              <",
]

# Feeder used only by the merger test rig: reads a lane tag then a value
# and forwards it to the top (lane A) or bottom (lane B) pipe.
FEEDER = [
    ">@rXrs v",
    "   r    ",
    "   s    ",
    "^  <   <",
]
