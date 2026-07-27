"""The two primitives that make a multi-band room fold possible.

Folding a tall room moves half its cells into a new column band. `r`/`s`
bind to the NEAREST pipe, and a pipe has one endpoint, which cannot be
nearest to two disjoint column clusters while rivals compete -- so every
band-B I/O cell rebinds at once and the machine deadlocks with its pipe
multiset byte-identical. That killed two pathfinder fold attempts.

The way out is to split each shared pipe per band and reunite the halves:

* OUTGOING -- a merger room (`@ R s`) reads both halves. Ordering is NOT
  guaranteed by "the man is in one band at a time", because the other
  band's pipe can still hold in-flight values. It is guaranteed by `R`'s
  tie-break, which is purely geometric.
* INCOMING -- for a request/response pair the responder uses `U` to tell
  which band asked. `U` discriminates by the WALL SIDE the pipe attaches
  to, so the two request pipes must arrive on different walls.

These tests pin both, because the whole construction rests on them.
See docs/architecture/claude_43_fold_with_merger_and_splitter.md.
"""

import pytest

from littleman import sim

NORTH, SOUTH, EAST, WEST = (-1, 0), (1, 0), (0, 1), (0, -1)


def _run(rows, inputs, max_ticks=40):
    text = "\n".join(rows) + "\n"
    machine = sim.Machine.parse(text)
    trace = []
    original = machine._tick

    def traced(res, _m=machine, _o=original, _t=trace):
        err = _o(res)
        for man in _m.men:
            _t.append((man.r, man.c, man.direction, man.A))
        return err

    machine._tick = traced
    machine.run(max_ticks=max_ticks, inputs=list(inputs))
    return machine, trace


def test_U_turns_away_from_a_north_wall():
    """A value arriving on the NORTH wall must leave the man heading SOUTH."""
    _, trace = _run([
        "  +-+      ",
        "  |I|      ",
        "  +-+      ",
        "   v       ",
        "   v       ",
        " +-----+   ",
        " |@ U  |   ",
        " |     |   ",
        " |     |   ",
        " +-----+   ",
    ], [7])
    after = [step for step in trace if step[3] == 7]
    assert after, "the man never received the value"
    assert after[0][2] == SOUTH, f"expected SOUTH, got {after[0][2]}"


def test_U_turns_away_from_a_west_wall():
    """The same value on the WEST wall must leave him heading EAST.

    This is the pair that makes `U` a SPLITTER: two request pipes on two
    different walls put the responder on two different code paths.
    """
    _, trace = _run([
        "+-+        ",
        "|I|        ",
        "+-+        ",
        " v         ",
        " v +-----+ ",
        " v |     | ",
        " >>|@U   | ",
        "   |     | ",
        "   +-----+ ",
    ], [7])
    after = [step for step in trace if step[3] == 7]
    assert after, "the man never received the value"
    assert after[0][2] == EAST, f"expected EAST, got {after[0][2]}"


def test_R_drains_the_smaller_entry_cell_first():
    """`R` picks `min(ready, key=lambda p: p.cells[-1])` -- the entry cell
    smallest in (row, col) order.

    This is what makes a merger room order-preserving: put band A's pipe
    entry above band B's and A always drains first when both are ready,
    which matches program order because band A is the earlier half.
    """
    text = "\n".join([
        "+-+   +-+    ",
        "|I|   | |    ",
        "+-+   +-+    ",
        " v     v     ",
        " v     v     ",
        " >>>>>>+---+ ",
        "       |@R | ",
        "       |   | ",
        "       +---+ ",
    ]) + "\n"
    machine = sim.Machine.parse(text)
    work = [r for r in machine.rooms if r.kind == "room"][-1]
    incoming = machine.in_pipes.get(id(work), [])
    assert len(incoming) == 2, f"expected two incoming pipes, got {len(incoming)}"

    smaller, larger = sorted(incoming, key=lambda p: p.cells[-1])
    assert smaller.cells[-1] < larger.cells[-1]
    smaller.put(len(smaller.cells) - 1, 111)
    larger.put(len(larger.cells) - 1, 222)

    man = machine.men[0]
    man.r, man.c = work.top + 1, work.left + 2      # stand on the `R`
    assert machine.grid[man.r][man.c] == "R"
    machine._execute(man)
    assert man.A == 111, "R must drain the smaller-(row,col) entry first"


def test_a_mirror_would_break_conditional_turns_but_a_rotation_does_not():
    """Why the fold rotates 180 degrees instead of mirroring.

    `X`/`d`/`a`/`x` turn by CLOCKWISE/COUNTERCW. A rotation is orientation
    -preserving so it commutes with both; a reflection reverses them and
    would silently invert every conditional branch -- 33 `X` and 33 `d` in
    pathfinder's room 0 -- while the machine still parses and loads.
    """
    rotate = {d: (-d[0], -d[1]) for d in (NORTH, SOUTH, EAST, WEST)}
    for d in (NORTH, SOUTH, EAST, WEST):
        assert rotate[sim.CLOCKWISE[d]] == sim.CLOCKWISE[rotate[d]]
        assert rotate[sim.COUNTERCW[d]] == sim.COUNTERCW[rotate[d]]

    mirror = {NORTH: SOUTH, SOUTH: NORTH, EAST: EAST, WEST: WEST}
    assert any(mirror[sim.CLOCKWISE[d]] != sim.CLOCKWISE[mirror[d]]
               for d in (NORTH, SOUTH, EAST, WEST)), \
        "a vertical mirror must NOT commute with CLOCKWISE"


# ---------------------------------------------------------------------------
# The same three facts, re-checked against the ORGANIZERS' OWN ENGINE.
#
# This matters because our simulator was proven wrong TWICE on 2026-07-27:
# it never implemented `Y`, and it had the wall rule wrong in a way that
# changed pass/fail. A design resting on sim.py alone is not verified.
# ---------------------------------------------------------------------------

import json
import pathlib
import shutil
import subprocess

REPO = pathlib.Path(__file__).resolve().parent.parent
HARNESS = REPO / "claude" / "official-sim" / "harness.mjs"
NODE = shutil.which("node")

wasm_only = pytest.mark.skipif(
    NODE is None or not HARNESS.exists(),
    reason="organizers' WASM harness unavailable")


def _wasm(program, inputs, max_ticks=200):
    request = {"program": program, "input": [list(inputs)], "expected": [[]],
               "maxTicks": max_ticks, "stopOnSettle": False}
    proc = subprocess.run([NODE, str(HARNESS)], input=json.dumps(request),
                          capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, proc.stderr[:300]
    return json.loads(proc.stdout)


@wasm_only
@pytest.mark.parametrize("rows,expected_dir,label", [
    ([
        "  +-+      ",
        "  |I|      ",
        "  +-+      ",
        "   v       ",
        "   v       ",
        " +-----+   ",
        " |@ U  |   ",
        " |     |   ",
        " |     |   ",
        " +-----+   ",
    ], [0, 1], "north wall -> SOUTH"),
    ([
        "+-+        ",
        "|I|        ",
        "+-+        ",
        " v         ",
        " v +-----+ ",
        " v |     | ",
        " >>|@U   | ",
        "   |     | ",
        "   +-----+ ",
    ], [1, 0], "west wall -> EAST"),
])
def test_U_wall_side_discrimination_on_the_real_engine(rows, expected_dir, label):
    """`U` turns away from the SIDE OF THE ROOM the pipe attaches to.

    The `wall` fatal is expected: these probes have no `H`, so the man
    walks out after turning. The turn itself is the observable.
    """
    state = _wasm("\n".join(rows) + "\n", [7])
    runners = state.get("runners") or []
    assert runners, f"{label}: no runner reported"
    assert runners[0]["dir"] == expected_dir, (
        f"{label}: got {runners[0]['dir']}")
    assert int(runners[0]["a"]) == 7, f"{label}: value not delivered"


@wasm_only
def test_R_tiebreak_matches_our_simulator_on_the_real_engine():
    """The merger's entire ordering guarantee.

    Two values are sent into two pipes whose entry cells are (11,4) and
    (11,11); the first value goes to the smaller one. `R` twice, then out.
    Output [7, 9] means the smaller-(row,col) entry drained first, so a
    merger can be ordered by geometry alone.
    """
    artifact = REPO / "tests" / "data_fold_r_tiebreak.man"
    if not artifact.exists():
        pytest.skip("probe artifact missing")
    state = _wasm(artifact.read_text(), [7, 9])
    assert state.get("fatal") in (None, {}), state.get("fatal")
    assert [int(v) for v in (state.get("output") or [])] == [7, 9]
