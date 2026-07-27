"""Tests for littleman.room_reflow, on small hand-built interiors where the
correct strand count can be stated by inspection.
"""

from littleman import room_reflow as rr
from littleman.sim import DOWN, LEFT, RIGHT, UP


def test_straight_vertical_corridor_crosses_every_line_once():
    # @ steps right onto 'v' (turns down), then walks straight down through
    # blank cells to 'H'. One lane, one column: every cut line between
    # consecutive rows carries exactly that one strand.
    interior = [
        "@v",
        " .",
        " .",
        " .",
        " H",
    ]
    profile = rr.strand_profile(interior)
    ys = [y for y, _count, _cols in profile]
    assert ys == [1, 2, 3, 4]
    for y, count, cols in profile:
        assert count == 1, f"cut line {y} should carry exactly 1 strand"
        assert cols == [(1, "v")]


def test_down_and_up_lane_crosses_twice():
    # @ walks down column 1 to the bottom, turns right then up, and walks
    # back up column 2 to the top wall. A corridor plus a return lane:
    # every cut line is crossed once going down and once going up.
    interior = [
        "@v ",
        " v ",
        " v ",
        " >^",
    ]
    profile = rr.strand_profile(interior)
    assert [y for y, _c, _cols in profile] == [1, 2, 3]
    for y, count, cols in profile:
        assert count == 2, f"cut line {y} should carry exactly 2 strands"
        assert cols == [(1, "v"), (2, "^")]


def test_horizontal_only_walk_crosses_nothing_and_frees_every_cut_line():
    # @ only ever moves along row 0; rows 1 and 2 are never visited, so both
    # cut lines (y=1, y=2) carry zero strands and are free fold points even
    # at max_strands=0.
    interior = [
        "@>H",
        "   ",
        "   ",
    ]
    profile = rr.strand_profile(interior)
    assert profile == [(1, 0, []), (2, 0, [])]
    assert rr.fold_points(interior, max_strands=0) == [1, 2]
    assert rr.fold_points(interior, max_strands=1) == [1, 2]


def test_X_branches_into_all_sign_dependent_directions():
    # @ steps right onto 'v' (down), then hits 'X' facing DOWN. sim.py turns
    # X clockwise if A>0, counter-clockwise if A<0, or straight if A==0 --
    # a register value this module does not track. All three outcomes for
    # an incoming DOWN are distinct: CW->LEFT, CCW->RIGHT, straight->DOWN.
    # All three must appear as edges out of the X state, even though any
    # single concrete run only ever takes one.
    interior = [
        "@v ",
        "HXH",
        " H ",
    ]
    graph = rr.walk_graph(interior)
    x_state = (1, 1, DOWN)
    assert x_state in graph
    assert graph[x_state] == {
        (0, 1, LEFT),   # clockwise from DOWN
        (2, 1, RIGHT),  # counter-clockwise from DOWN
        (1, 2, DOWN),   # straight (A == 0)
    }
    # And this shows up as a real strand-count consequence: the cut line
    # below the X (y=2) is crossed by the "straight" branch even though a
    # concrete run starting with A=0 (the only reachable value here, since
    # nothing in this interior ever sets A) never turns there.
    profile = rr.strand_profile(interior)
    by_y = {y: count for y, count, _cols in profile}
    assert by_y[1] == 1  # the initial 'v' turn, column 1
    assert by_y[2] == 1  # the X's straight branch, column 1


def test_fold_points_threshold_on_mixed_crossing_counts():
    # Two independent little men. The first walks down column 1, U-turns at
    # the bottom (row 3) and returns up column 2 to the top wall -- crossing
    # every line (y=1,2,3) once each way, i.e. 2 strands per line. The
    # second is a short, independent lane at column 4 that only crosses
    # y=1 before halting. So y=1 carries 3 strands; y=2 and y=3 carry 2.
    interior = [
        "@v @v",
        " v  H",
        " v   ",
        " >^  ",
    ]
    profile = rr.strand_profile(interior)
    by_y = {y: count for y, count, _cols in profile}
    assert by_y == {1: 3, 2: 2, 3: 2}

    assert rr.fold_points(interior, max_strands=1) == []
    assert rr.fold_points(interior, max_strands=2) == [2, 3]
    assert rr.fold_points(interior, max_strands=3) == [1, 2, 3]
