"""Tests for the Y-probe: YMachine /split semantics, jog tuner, artifacts.

One directed test per /split bullet (claude/split-instruction-20260725.md),
including the /split demo program and the user's editor map that resolved
die-vs-stop, plus the probe choreography acceptance checks (a)-(e) from
claude/y-probe-design.md and the artifact / stand-in plumbing gates.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import server_compat
from littleman.sim import Machine
from littleman.split_probe import (
    COLLIDER_WINDOW,
    GATE_AT,
    RELAY_R_CELL,
    ROLES,
    STOP_CELL,
    X_CELL,
    YMachine,
    build_probe_collision,
    build_probe_nav,
    build_standin,
    gate_interior,
    strip_walls,
    tune,
)

ROOT = Path(__file__).resolve().parents[1]
E, W, N, S = (0, 1), (0, -1), (-1, 0), (1, 0)


def i0(cell):
    return (cell[0] - 1, cell[1] - 1)


# ------------------------------------------------------- YMachine: /split
def test_hand_checked_three_ticks():
    """Split geometry tick by tick: born left/right, inert on the birth tick,
    executing the birth cell and moving the tick after."""
    sim = YMachine(["   ", "   ", "@Y ", "   ", "   "])
    sim.tick()                                   # @ is a nop; P steps onto Y
    assert [(m.name, m.r, m.c) for m in sim.men] == [("P", 2, 1)]
    sim.tick()                                   # Y executes: P is gone
    assert sim.names() == ["Pr", "Pl"]           # right copy inherited P's slot
    assert (sim.man("Pr").r, sim.man("Pr").c) == (3, 1)   # right of east = south
    assert (sim.man("Pl").r, sim.man("Pl").c) == (1, 1)   # left of east = north
    assert sim.man("Pr").d == S and sim.man("Pl").d == N  # heading away from Y
    assert not sim.man("P").alive
    sim.tick()                                   # copies act the tick after
    assert (sim.man("Pr").r, sim.man("Pr").c) == (4, 1)
    assert (sim.man("Pl").r, sim.man("Pl").c) == (0, 1)
    assert sim.error is None


def test_ordering_right_inherits_slot_left_appended():
    """Creation order after nested splits: [Pr, Plr, Pll] in the gate."""
    sim = YMachine(gate_interior("collision", *_jogs()), "die").run(8)
    assert sim.names()[0] == ROLES["D"]          # right copy of the first split
    assert sim.names()[-2:] == [ROLES["B"], ROLES["A"]]  # Y2: right, then left
    assert sim.names() == ["Pr", "Plr", "Pll"]


def test_copies_carry_registers_including_backpack():
    sim = YMachine(["      ", "@5M3bY", "      "]).run(6)
    for name in ("Pr", "Pl"):
        man = sim.man(name)
        assert (man.A, man.B, man.BP) == (3, 5, 3)


def test_wall_birth_is_an_error():
    sim = YMachine(["@Y "]).run(3)               # both birth cells are walls
    assert sim.error == "wall-birth"


def test_birth_onto_a_blocked_man_kills_both_not_an_error():
    # P1 halts on H at (0,1); P0 walks onto Y below it heading east, so the
    # left copy is born onto the blocked man: both die, the right copy lives.
    grid = [" H ", "@Y ", "   "]
    sim = YMachine(grid, men=[(1, 0, E), (0, 1, E)]).run(2)
    assert sim.error is None
    deaths = [e for e in sim.events if e[1] == "die"]
    assert len(deaths) == 1 and deaths[0][4] == "birth"
    assert set(deaths[0][2]) == {"P0l", "P1"}
    assert [m.name for m in sim.live()] == ["P0r"]


def test_spawn_conflict_two_splits_same_cell_kill_both_copies():
    grid = ["  ", " Y", "  ", " Y", "  "]
    sim = YMachine(grid, men=[(1, 0, E), (3, 0, E)]).run(2)
    assert sim.error is None
    deaths = [e for e in sim.events if e[1] == "die"]
    assert len(deaths) == 1 and deaths[0][3] == (2, 1)
    assert set(deaths[0][2]) == {"P0r", "P1l"}   # both spawned onto (2,1)
    assert sorted((m.name, m.r, m.c) for m in sim.live()) == [
        ("P0l", 0, 1), ("P1r", 4, 1)]


def test_same_cell_same_tick_arrival_die_vs_stop():
    grid = ["   "]
    die = YMachine(grid, "die", men=[(0, 0, E), (0, 2, W)]).run(2)
    assert die.error is None and die.live() == []
    assert die.events == [(1, "die", ("P0", "P1"), (0, 1), "meet")]
    stop = YMachine(grid, "stop", men=[(0, 0, E), (0, 2, W)]).run(2)
    assert stop.error is None
    assert all(m.halted for m in stop.live())    # both stop, both remain


def test_swap_through_each_other_dies():
    sim = YMachine(["  "], "die", men=[(0, 0, E), (0, 1, W)]).run(2)
    assert sim.error is None and sim.live() == []
    assert sim.events[0][1] == "die" and sim.events[0][4] == "swap"


def test_walking_onto_a_standing_man_die_vs_stop():
    grid = [" H  "]
    die = YMachine(grid, "die", men=[(0, 3, W), (0, 0, E)]).run(4)
    assert die.error is None and die.live() == []
    assert [e[4] for e in die.events if e[1] == "die"] == ["touch"]
    stop = YMachine(grid, "stop", men=[(0, 3, W), (0, 0, E)]).run(4)
    assert stop.error is None
    assert [(m.r, m.c) for m in stop.live()] == [(0, 2), (0, 1)]
    assert all(m.halted for m in stop.live())    # mover halts one cell short


def test_live_men_cap():
    grid = ["   ", "   ", "@Y ", "   ", "   "]
    assert YMachine(grid, cap=1).run(3).error == "men-cap"
    assert YMachine(grid, cap=2).run(3).error is None


def test_split_demo_program():
    """The /split docs demo: copies head up/down and halt on the two H."""
    demo = strip_walls(
        "+------+\n| >  H |\n|      |\n|@Y    |\n|      |\n| >  H |\n+------+"
    )
    sim = YMachine(demo).run(20)
    assert sim.error is None
    assert sorted((m.name, m.r, m.c, m.halted) for m in sim.live()) == [
        ("Pl", 0, 4, True), ("Pr", 4, 4, True)]


EDITOR_MAP = """\
+-------------------+
|     >     v       |
|                   |
| >   Y             |
|                   |
|     >          v  |
|@Y<                |
|  ^             <  |
|                   |
|                   |
|                   |
| >         ^       |
+-------------------+"""


def test_editor_map_divide_annihilate_reproduce():
    """The user's official-editor experiment that resolved die-vs-stop:
    copies meet mid-column and both die (removed, program continues), and a
    surviving copy re-enters a Y afterwards (reproduction)."""
    sim = YMachine(strip_walls(EDITOR_MAP), "die").run(60)
    assert sim.error is None
    deaths = [e for e in sim.events if e[1] == "die"]
    assert deaths[0][1:] == ("die", ("Pr", "Pll"), (5, 11), "meet")
    first_death = deaths[0][0]
    splits = [e[0] for e in sim.events if e[1] == "split"]
    assert any(t > first_death for t in splits)  # program continued into a Y
    assert sim.live()                            # ... with a live man at t60
    assert len(deaths) >= 2                      # the cycle annihilates again
    assert {d[3] for d in deaths} == {(5, 11)}


# ---------------------------------------------------------------- the tuner
def _jogs():
    t = tune()
    return t.ja, t.jd


def test_tuner_converges_and_choreography_holds():
    t = tune()
    assert t.ja >= 0 and t.jd >= 0
    x0 = i0(X_CELL)
    grid = gate_interior("collision", t.ja, t.jd)
    die = YMachine(grid, "die").run(60)
    stop = YMachine(grid, "stop").run(60)
    assert die.error is None and stop.error is None

    # (a) A and B enter X on the same tick (a single same-cell meet at X)
    deaths = [e for e in die.events if e[1] == "die"]
    assert len(deaths) == 1
    tick, _, names, cell, why = deaths[0]
    assert set(names) == {ROLES["A"], ROLES["B"]}
    assert cell == x0 and why == "meet" and tick == t.collision_tick

    # (b) D crosses X at least 2 ticks later
    d_die = die.man(ROLES["D"])
    cross = next(tk for tk, p in d_die.path if p == x0)
    assert cross == t.cross_tick >= t.collision_tick + 2

    # (c) no unintended meetings: the X meet is the only collision event in
    # either mode besides D touching the corpse, and no man ever overlaps
    assert [e for e in die.events if e[1] == "die"] == deaths
    stops = [e for e in stop.events if e[1] == "stop"]
    assert {e[3] for e in stops} == {x0} and len(stops) == 2

    # (d) die mode: D reaches the relay loop and parks on its blocking `r`
    assert d_die.parked and (d_die.r, d_die.c) == i0(RELAY_R_CELL)

    # (e) stop mode: D halts one cell short and never crosses X
    d_stop = stop.man(ROLES["D"])
    assert d_stop.halted and (d_stop.r, d_stop.c) == i0(STOP_CELL)
    assert all(p != x0 for _, p in d_stop.path)
    assert not any(e[1] == "park" and e[2] == ROLES["D"] for e in stop.events)


def test_nav_gate_is_collision_free_under_both_semantics():
    for mode in ("die", "stop"):
        sim = YMachine(gate_interior("nav", *_jogs()), mode).run(60)
        assert sim.error is None
        assert not [e for e in sim.events if e[1] in ("die", "stop")]
        d = sim.man(ROLES["D"])
        assert d.parked and (d.r, d.c) == i0(RELAY_R_CELL)
        u = sim.man(ROLES["U"])                  # U circles the square forever
        assert u.alive and not u.halted and not u.parked


# ----------------------------------------------------------- the artifacts
NAV = ROOT / "submissions/memory/memory_05_probe_y_nav.man"
COLLISION = ROOT / "submissions/memory/memory_06_probe_y_collision.man"


def test_artifacts_match_generator_byte_for_byte():
    assert NAV.read_bytes() == build_probe_nav().encode()
    assert COLLISION.read_bytes() == build_probe_collision().encode()
    assert build_probe_nav() == build_probe_nav()          # deterministic


@pytest.mark.parametrize("path", [NAV, COLLISION], ids=["nav", "collision"])
def test_artifacts_parse_with_expected_topology(path):
    machine = Machine.parse(path.read_text())
    assert len(machine.rooms) == 8               # I, GATE + the 5 + O
    assert len(machine.men) == 6                 # GATE man + one per pipeline room
    assert len(machine.pipes) == 8
    assert min(len(p.cells) for p in machine.pipes) >= 2
    server_compat.validate_layout(path.read_text())


def test_probe_diff_is_localized_to_the_collider_window():
    nav, col = NAV.read_text().split("\n"), COLLISION.read_text().split("\n")
    assert len(nav) == len(col)
    width = max(map(len, nav + col))
    diff = [
        (r, c)
        for r, (a, b) in enumerate(zip(nav, col))
        for c, (x, y) in enumerate(zip(a.ljust(width), b.ljust(width)))
        if x != y
    ]
    assert diff                                  # the probes DO differ
    (r1, r2), (c1, c2) = COLLIDER_WINDOW         # interior coords -> canvas
    top, left = GATE_AT
    for r, c in diff:
        assert top + r1 <= r <= top + r2
        assert left + 1 + c1 - 1 <= c <= left + 1 + c2 - 1
    assert NAV.read_text().count("Y") == 1       # nav: Y1 only
    assert COLLISION.read_text().count("Y") == 2  # collision: Y1 + Y2


# ------------------------------------------------------ stand-in plumbing
def test_standin_has_no_Y_and_passes_all_public_memory_cases():
    text = build_standin()
    assert "Y" not in text
    machine = Machine.parse(text)
    assert len(machine.rooms) == 8 and len(machine.pipes) == 8
    problem = json.loads(
        (ROOT / "data/small/problems/memory.json").read_text())
    report = server_compat.judge_problem(text, problem)
    assert report.cases_passed == report.cases_total == 7
