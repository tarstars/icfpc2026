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
