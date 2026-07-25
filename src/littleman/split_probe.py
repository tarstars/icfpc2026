"""Y-probe experiment: `YMachine` (/split simulator), GATE choreography, tuner,
and generators for the two probe artifacts.

Design doc: `claude/y-probe-design.md`. Y semantics: the verbatim /split text
in `claude/split-instruction-20260725.md` (die-not-stop confirmed in the
official editor; see its RESOLVED section).

Pieces
------
* :class:`YMachine` -- a single-room simulator implementing full /split
  semantics: the `Y` op (birth cells left/right of the heading, copies head
  away, registers copied, copies act the tick AFTER birth), die-not-stop
  collisions with same-cell-arrival AND swap-through detection, spawn-conflict
  and birth-onto-man deaths, creation-order insertion (right copy inherits the
  parent's slot, left copy appended last), wall-birth error, and the 65536
  live-men cap.  Supports the non-pipe op set of `sim.py` plus `Y`; `r` parks
  a man forever (models a blocking read with no pipes) and `s` is a nop.
  A `mode="stop"` flag keeps the ruled-out reference semantics (colliding men
  halt in place, a mover halts short) purely for probe-2 discrimination tests.
* GATE room generators (`nav` / `collision` / `standin`) with two integer jog
  parameters, and :func:`tune`, which searches jog values until the collision
  choreography is exact (A and B enter X the same tick, D crosses >= 2 ticks
  later, no unintended meetings).
* :func:`assemble` splices the GATE between `I` and the proven memory_04
  pipeline: `I -> GATE -> P1 -> ...`.  The memory_04 rooms are imported
  read-only from `littleman.memory_packed` and re-assembled here with the
  whole block shifted :data:`SHIFT` columns right; nothing existing changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from .canvas import Canvas
from . import memory_packed as mp
from .memory_packed import Room
from .sim import wrap64

# ---------------------------------------------------------------- geometry
GATE_ROWS, GATE_COLS = 11, 8   # interior size of the GATE room
GATE_AT = (0, 5)               # canvas origin of the GATE (top-left wall cell)
SHIFT = 11                     # column shift applied to the memory_04 block
MEN_CAP = 65536

# 1-based interior coordinates (design-doc convention)
X_CELL = (6, 6)                # the collision cell; a SPACE on D's lane
RELAY_R_CELL = (8, 6)          # the racetrack's blocking `r`
STOP_CELL = (6, 5)             # where D halts under stop semantics
COLLIDER_WINDOW = ((1, 7), (4, 7))   # rows 1-7 x cols 4-7: all nav/collision diffs

UP, DOWN, LEFT, RIGHT = (-1, 0), (1, 0), (0, -1), (0, 1)
ARROWS = {"^": UP, "v": DOWN, "<": LEFT, ">": RIGHT}
CW = {UP: RIGHT, RIGHT: DOWN, DOWN: LEFT, LEFT: UP}
CCW = {v: k for k, v in CW.items()}

# role -> YMachine man name in the collision gate (P splits at Y1 into
# D=right/U=left; U splits at Y2 into B=right/A=left)
ROLES = {"P": "P", "D": "Pr", "U": "Pl", "B": "Plr", "A": "Pll"}


def strip_walls(text: str) -> list[str]:
    """Interior rows of a single-room `+--+ |..|` drawing (test convenience)."""
    lines = [l for l in text.split("\n") if l.strip()]
    return [line[1:-1] for line in lines[1:-1]]


# ----------------------------------------------------------------- YMachine
@dataclass
class YMan:
    name: str
    r: int
    c: int
    d: tuple
    A: int = 0
    B: int = 0
    BP: int = 0
    born: int = 0              # tick of birth; copies act the tick after
    alive: bool = True
    halted: bool = False       # H, or stop-mode collision
    parked: bool = False       # blocked forever on `r`
    path: list = field(default_factory=list)   # [(tick, (r, c))] actual moves


class YMachine:
    """Single-room littleman simulator with /split `Y` semantics.

    `rows` is the room INTERIOR (no walls), 0-based coordinates.  Men are the
    `@` cells in reading order heading right, or an explicit `men` list of
    `(r, c, direction)`.  `mode` is "die" (/split, default) or "stop" (the
    ruled-out reference text, kept only as a discrimination flag).
    """

    def __init__(self, rows, mode="die", men=None, cap=MEN_CAP):
        if mode not in ("die", "stop"):
            raise ValueError(mode)
        self.rows = list(rows)
        self.height = len(self.rows)
        self.width = max(len(r) for r in self.rows)
        self.mode, self.cap, self.tick_no = mode, cap, 0
        self.events: list[tuple] = []
        self.error: str | None = None
        self.graveyard: list[YMan] = []
        if men is None:
            men = [(r, c, RIGHT) for r, row in enumerate(self.rows)
                   for c, ch in enumerate(row) if ch == "@"]
        self.men = [YMan("P" if len(men) == 1 else f"P{i}", r, c, d)
                    for i, (r, c, d) in enumerate(men)]

    # ------------------------------------------------------------- helpers
    def glyph(self, r, c):
        row = self.rows[r]
        return row[c] if c < len(row) else " "

    def live(self):
        return [m for m in self.men if m.alive]

    def man(self, name):
        return next(m for m in self.men + self.graveyard if m.name == name)

    def names(self):
        return [m.name for m in self.men]

    def _bury(self, man):
        man.alive = False
        self.men.remove(man)
        self.graveyard.append(man)

    def _die_pair(self, a, b, cell, why):
        self.events.append((self.tick_no, "die", (a.name, b.name), cell, why))
        self._bury(a)
        self._bury(b)

    # ------------------------------------------------------------ splitting
    def _split(self, man):
        self.events.append((self.tick_no, "split", man.name, (man.r, man.c)))
        slot = self.men.index(man)
        copies = []
        for suffix, d in (("r", CW[man.d]), ("l", CCW[man.d])):
            r, c = man.r + d[0], man.c + d[1]
            if not (0 <= r < self.height and 0 <= c < self.width):
                self.error = "wall-birth"   # /split: birth into a wall errors
                return
            baby = YMan(man.name + suffix, r, c, d, A=man.A, B=man.B,
                        BP=man.BP, born=self.tick_no)
            copies.append(baby)
            self.events.append((self.tick_no, "born", baby.name, (r, c), d))
        right, left = copies
        self.men[slot] = right             # right copy inherits the slot
        self.men.append(left)              # left copy acts after all others
        man.alive = False
        self.graveyard.append(man)
        if len(self.live()) > self.cap:
            self.error = "men-cap"
            return
        for baby in (right, left):         # birth-cell conflicts: both die
            if not baby.alive:
                continue
            other = next((m for m in self.live()
                          if m is not baby and (m.r, m.c) == (baby.r, baby.c)),
                         None)
            if other is not None:
                self._die_pair(baby, other, (baby.r, baby.c), "birth")

    # ------------------------------------------------------------ execution
    def _execute(self, man):
        ch = self.glyph(man.r, man.c)
        if ch in " @.s":
            return
        if ch in ARROWS:
            man.d = ARROWS[ch]
        elif ch == "Y":
            self._split(man)
        elif ch == "r":
            man.parked = True
            self.events.append((self.tick_no, "park", man.name, (man.r, man.c)))
        elif ch == "H":
            man.halted = True
        elif ch.isdigit():
            man.A = int(ch)
        elif ch == "M":
            man.B = man.A
        elif ch == "W":
            man.A, man.B = man.B, man.A
        elif ch == "+":
            man.A = wrap64(man.A + man.B)
        elif ch == "-":
            man.A = wrap64(man.A - man.B)
        elif ch == "*":
            man.A = wrap64(man.A * man.B)
        elif ch == "N":
            man.A = wrap64(-man.A)
        elif ch == "%":
            man.A = 0 if man.B == 0 else wrap64(man.A % man.B)
        elif ch == "/":
            if man.B == 0:
                man.A, man.B = 0, man.A
            else:
                q, rem = divmod(man.A, man.B)
                man.A, man.B = wrap64(q), wrap64(rem)
        elif ch == "&":
            man.A = wrap64(man.A & man.B)
        elif ch == "|":
            man.A = wrap64(man.A | man.B)
        elif ch == "~":
            man.A = wrap64(man.A ^ man.B)
        elif ch == "{":
            man.A = wrap64(man.A << man.B) if 0 <= man.B <= 63 else 0
        elif ch == "}":
            man.A = 0 if man.B < 0 else wrap64(man.A >> min(man.B, 63))
        elif ch == "X":
            if man.A > 0:
                man.d = CW[man.d]
            elif man.A < 0:
                man.d = CCW[man.d]
        elif ch == "b":
            man.BP = man.A
        elif ch == "m":
            man.BP = wrap64(man.BP - 1)
        elif ch == "d":
            if man.BP > 0:
                man.d = CW[man.d]
        elif ch == "a":
            if man.BP > 0:
                man.d = CCW[man.d]
        elif ch == "]":
            man.BP = man.BP >> 1
        elif ch == "x":
            man.d = CW[man.d] if man.BP & 1 else CCW[man.d]
        else:
            self.error = f"bad-op {ch!r}"

    # ------------------------------------------------------------- movement
    def _acts(self, man):
        return (man.alive and not man.halted and not man.parked
                and man.born != self.tick_no)

    def _move_die(self):
        """Simultaneous /split movement: swaps, same-cell arrivals and
        walks onto standing men all kill both parties (removed, not error)."""
        movers = [m for m in self.men if self._acts(m)]
        target = {}
        for m in movers:
            nr, nc = m.r + m.d[0], m.c + m.d[1]
            if not (0 <= nr < self.height and 0 <= nc < self.width):
                self.error = "wall"
                return
            target[id(m)] = (nr, nc)
        standing = {(m.r, m.c): m for m in self.live() if id(m) not in target}
        doomed: dict[int, YMan] = {}

        def doom(a, b, cell, why):
            if id(a) not in doomed and id(b) not in doomed:
                self.events.append(
                    (self.tick_no, "die", (a.name, b.name), cell, why))
            doomed[id(a)] = a
            doomed[id(b)] = b

        origin = {(m.r, m.c): m for m in movers}
        for m in movers:                      # swap-through
            o = origin.get(target[id(m)])
            if o is not None and o is not m and target[id(o)] == (m.r, m.c):
                doom(m, o, ((m.r, m.c), target[id(m)]), "swap")
        by_target: dict[tuple, list] = {}
        for m in movers:                      # same-cell same-tick arrival
            by_target.setdefault(target[id(m)], []).append(m)
        for cell, group in by_target.items():
            if len(group) > 1:
                for a in group[1:]:
                    doom(group[0], a, cell, "meet")
        for m in movers:                      # walking onto a standing man
            o = standing.get(target[id(m)])
            if o is not None:
                doom(m, o, target[id(m)], "touch")
        for m in movers:
            if id(m) not in doomed:
                m.r, m.c = target[id(m)]
                m.path.append((self.tick_no, (m.r, m.c)))
        for m in doomed.values():
            if m.alive:
                self._bury(m)

    def _move_stop(self):
        """Reference-text movement (ruled out; kept for discrimination):
        a man entering an occupied cell halts in place, so does the occupant."""
        occupied = {(m.r, m.c): m for m in self.live()}
        for m in list(self.men):
            if not self._acts(m):
                continue
            nr, nc = m.r + m.d[0], m.c + m.d[1]
            if not (0 <= nr < self.height and 0 <= nc < self.width):
                self.error = "wall"
                return
            other = occupied.get((nr, nc))
            if other is not None:
                m.halted = other.halted = True
                self.events.append(
                    (self.tick_no, "stop", (m.name, other.name), (nr, nc),
                     "touch"))
                continue
            del occupied[(m.r, m.c)]
            m.r, m.c = nr, nc
            occupied[(nr, nc)] = m
            m.path.append((self.tick_no, (nr, nc)))

    # -------------------------------------------------------------- ticking
    def tick(self):
        self.tick_no += 1
        for man in list(self.men):         # creation order; newborns skipped,
            if self._acts(man):            # left copies appended mid-loop are
                self._execute(man)         # not in the snapshot anyway
            if self.error:
                return
        self._move_die() if self.mode == "die" else self._move_stop()
        if self.error:
            return
        pos = [(m.r, m.c) for m in self.live()]
        if len(pos) != len(set(pos)):      # invariant: men never overlap
            self.error = "overlap"

    def run(self, ticks):
        for _ in range(ticks):
            if self.error:
                break
            self.tick()
        return self


# ------------------------------------------------------------------- layout
def build_gate(kind: str, ja: int = 0, jd: int = 0) -> Room:
    """The GATE room interior.  kind: "nav" | "collision" | "standin".

    Choreography (1-based interior coords; jogs `ja`, `jd` are tuner-chosen):
    `@`(4,1)E onto Y1(4,2).  D (right copy) born (5,2)S, delays down col 2 to
    row 7+jd, back up col 3, then east along row 6 through X=(6,6) into the
    relay racetrack rows 8-9, parking on its blocking `r`.  U (left copy) born
    (3,2)N onto `>`, runs row 3 east, turns north at (3,6).  In "nav" U then
    circles a harmless 2x2 arrow square (rows 1-2, cols 6-7) forever.  In
    "collision" U walks onto Y2(2,6); A (left copy) born (2,5)W jogs `ja`
    cells west, drops to row 5, runs east and enters X from the north; B
    (right copy) born (2,7)E drops down col 7, turns west then north and
    enters X from the south.  "standin" replaces everything Y with one man
    walking row 4 east and down col 8 into the same racetrack (no split).
    """
    room = Room(GATE_ROWS, GATE_COLS)
    room.put(8, 5, ">rsv")                 # relay racetrack (all kinds):
    room.put(9, 5, "^")                    # parked on the blocking `r`,
    room.put(9, 8, "<")                    # latency-insensitive composition
    if kind == "standin":
        room.put(4, 1, "@")                # plain straight path, no Y at all
        room.put(4, 8, "v")
        room.put(6, 8, "v")
        return room
    room.put(4, 1, "@Y")                   # Y1
    room.put(3, 2, ">")                    # U's lane east along row 3
    room.put(3, 6, "^")
    room.put(7 + jd, 2, ">^")              # D's delay dip down col 2 / up col 3
    room.put(6, 3, ">")                    # D's lane east along row 6 (spaces)
    room.put(6, 8, "v")                    # ... then down col 8 into the loop
    if kind == "nav":
        room.put(1, 6, ">v")               # U's harmless parking square
        room.put(2, 6, "^<")
    elif kind == "collision":
        room.put(2, 6, "Y")                # Y2
        room.put(2, 7, "v")                # B: down col 7 ...
        room.put(7, 6, "^<")               # ... west along row 7, north into X
        room.put(2, 5 - ja, "v")           # A: `ja` cells west, then south ...
        room.put(5, 5 - ja, ">")           # ... east along row 5 ...
        room.put(5, 6, "v")                # ... south into X
    else:
        raise ValueError(kind)
    return room


def gate_interior(kind: str, ja: int = 0, jd: int = 0) -> list[str]:
    """The gate interior as YMachine rows (0-based == interior-1)."""
    rendered = build_gate(kind, ja, jd).render()
    return [line[1:-1] for line in rendered[1:-1]]


def _i0(cell):
    """1-based interior coordinate -> 0-based YMachine coordinate."""
    return (cell[0] - 1, cell[1] - 1)


# -------------------------------------------------------------------- tuner
@dataclass
class TuneResult:
    ja: int
    jd: int
    collision_tick: int      # A and B enter X together on this tick (die)
    cross_tick: int          # D crosses X on this tick (die mode)
    park_tick: int           # D parks on the racetrack `r` (die mode)
    stop_tick: int           # D halts at STOP_CELL (stop mode)


def _check(ja: int, jd: int) -> TuneResult | None:
    x0 = _i0(X_CELL)
    grid = gate_interior("collision", ja, jd)
    die = YMachine(grid, "die").run(60)
    stop = YMachine(grid, "stop").run(60)
    if die.error or stop.error:
        return None
    a, b, d_name = ROLES["A"], ROLES["B"], ROLES["D"]
    deaths = [e for e in die.events if e[1] == "die"]
    # (a) exactly one meeting: A and B arriving on X the same tick, and (c)
    # no other collision of any kind anywhere, in either mode
    if len(deaths) != 1:
        return None
    t, _, names, cell, why = deaths[0]
    if set(names) != {a, b} or cell != x0 or why != "meet":
        return None
    # (b) D crosses X at least 2 ticks after the collision
    d_path = dict(p[::-1] for p in die.man(d_name).path)
    cross = d_path.get(x0)
    if cross is None or cross < t + 2:
        return None
    # (d) die mode: D reaches the relay loop and parks on its `r`
    parks = [e for e in die.events if e[1] == "park"]
    if len(parks) != 1 or parks[0][2] != d_name or parks[0][3] != _i0(RELAY_R_CELL):
        return None
    # (e) stop mode: the corpse blocks X and D halts one cell short
    stops = [e for e in stop.events if e[1] == "stop"]
    d_stop = stop.man(d_name)
    if not (d_stop.halted and (d_stop.r, d_stop.c) == _i0(STOP_CELL)):
        return None
    if any(x0 == p[1] for p in d_stop.path):
        return None
    if any(e[1] == "park" and e[2] == d_name for e in stop.events):
        return None
    if len(stops) != 2 or {c for _, _, _, c, _ in stops} != {x0}:
        return None
    return TuneResult(ja, jd, t, cross, parks[0][0],
                      max(e[0] for e in stops))


@lru_cache(maxsize=1)
def tune() -> TuneResult:
    """Search the jogs; also validate the nav gate under both modes."""
    for ja in range(0, 3):
        for jd in range(0, 5):
            result = _check(ja, jd)
            if result is None:
                continue
            for mode in ("die", "stop"):
                nav = YMachine(gate_interior("nav", result.ja, result.jd),
                               mode).run(60)
                assert nav.error is None
                assert not [e for e in nav.events if e[1] in ("die", "stop")]
                d = nav.man(ROLES["D"])
                assert d.parked and (d.r, d.c) == _i0(RELAY_R_CELL)
                u = nav.man(ROLES["U"])
                assert u.alive and not u.halted and not u.parked
            return result
    raise AssertionError("no jog values satisfy the choreography")


# ----------------------------------------------------------------- assembly
def assemble(gate: Room) -> str:
    """I -> GATE -> memory_04 pipeline, the memory_04 block shifted right.

    Everything below the GATE splice replicates `build_memory_packed`'s
    assembly with `SHIFT` added to every column (rows unchanged); the I room
    stays at the origin and its pipe now feeds the GATE, whose single output
    pipe feeds P1 where I's pipe used to attach.
    """
    cv = Canvas()
    cv.put(1, 0, ["+-+", "|I|", "+-+"])
    cv.put(*GATE_AT, gate.render())
    cv.put(0, 6 + SHIFT, mp.build_p1().render())
    cv.put(7, 6 + SHIFT, mp.build_head().render())
    cv.put(13, 6 + SHIFT, mp.build_p2().render())
    st_r, st_c = 22, 6 + SHIFT
    cv.put(st_r, st_c, mp.build_station().render())
    cv.put(st_r + mp.STA_OUT_ROW - 1, 0 + SHIFT, ["+-+", "|O|", "+-+"])
    cv.put(30, 31 + SHIFT, mp.build_relay().render())

    cv.pipe([(2, 3), (2, 4)])                        # I -> GATE
    cv.pipe([(2, 15), (2, 16)])                      # GATE -> P1
    cv.pipe([(5, 10 + SHIFT), (6, 10 + SHIFT)])      # P1 -> HEAD
    cv.pipe([(11, 10 + SHIFT), (12, 10 + SHIFT)])    # HEAD -> P2
    cv.pipe([(20, 8 + SHIFT), (21, 8 + SHIFT)])      # P2 -> STATION
    out_row = st_r + mp.STA_OUT_ROW
    cv.pipe([(out_row, 5 + SHIFT), (out_row, 3 + SHIFT)])   # STATION -> O
    st_right = st_c + 23
    ring_out_row = st_r + mp.STA_RINGOUT_ROW
    ring_in_row = st_r + mp.STA_RINGIN_ROW
    cv.pipe([
        (ring_out_row, st_right + 1), (ring_out_row, 36 + SHIFT),
        (26, 36 + SHIFT), (26, 31 + SHIFT), (28, 31 + SHIFT),
        (28, 36 + SHIFT), (29, 36 + SHIFT), (29, 33 + SHIFT),
    ])
    cv.cells[(29, 33 + SHIFT)] = "v"
    cv.pipe([(34, 34 + SHIFT), (35, 34 + SHIFT), (35, 30 + SHIFT),
             (ring_in_row, 30 + SHIFT)])
    cv.cells[(ring_in_row, 30 + SHIFT)] = "<"
    return cv.render()


def build_probe_nav() -> str:
    t = tune()
    return assemble(build_gate("nav", t.ja, t.jd))


def build_probe_collision() -> str:
    t = tune()
    return assemble(build_gate("collision", t.ja, t.jd))


def build_standin() -> str:
    return assemble(build_gate("standin"))


def main() -> None:
    import hashlib
    import pathlib

    t = tune()
    print(f"jogs: ja={t.ja} jd={t.jd}")
    print(f"collision tick (A,B meet on X): {t.collision_tick}")
    print(f"D crosses X (die mode): {t.cross_tick}")
    print(f"D parks on relay r (die mode): {t.park_tick}")
    print(f"D halts short of X (stop mode): {t.stop_tick}")
    root = pathlib.Path(__file__).resolve().parents[2]
    for name, text in (
        ("memory_05_probe_y_nav.man", build_probe_nav()),
        ("memory_06_probe_y_collision.man", build_probe_collision()),
    ):
        path = root / "submissions" / "memory" / name
        path.write_text(text)
        digest = hashlib.sha256(text.encode()).hexdigest()
        print(f"{name}: sha256={digest} bytes={len(text.encode())}")


if __name__ == "__main__":
    main()
