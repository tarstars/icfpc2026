"""`coil_to_length`: lengthen an exact-length pipe without moving its ends.

A length-exact connection that routes SHORTER than required used to be a
flat failure. It doesn't have to be: a grid path between two FIXED cells
only ever changes length in steps of 2, because every detour is a
"staple" -- side-step off the path, one cell forward, one cell back --
which trades one edge for three. So an even shortfall can always be
absorbed somewhere beside the path; an odd one never can.

Hand-built grids only, per the package brief: no large artifact, and no
dependency on the sibling packages' `layout_ir.py` / `layout_solve.py`
changes. This exercises `coil_to_length` in isolation.
"""

from __future__ import annotations

from littleman.layout_route import coil_to_length


def _assert_valid_path(path, blocked, endpoints=None):
    """Requirement 4: verified by a helper, not by eye."""
    assert path is not None
    assert len(set(path)) == len(path), f"path repeats a cell: {path}"
    for cell in path:
        assert cell not in blocked, f"{cell} is in blocked: {path}"
    for a, b in zip(path, path[1:]):
        dr, dc = b[0] - a[0], b[1] - a[1]
        assert (abs(dr), abs(dc)) in {(1, 0), (0, 1)}, (
            f"{a} -> {b} is not a unit orthogonal step")
    if endpoints is not None:
        assert path[0] == endpoints[0]
        assert path[-1] == endpoints[1]


def _straight(n):
    """A Manhattan-distance-`n` path: n + 1 cells, row 0, west to east."""
    return [(0, c) for c in range(n + 1)]


# 1. Manhattan distance 4 (5 cells) coils to exactly 7 and exactly 9.

def test_coils_distance_four_to_seven():
    path = _straight(4)
    out = coil_to_length(path, 7, blocked=set())
    assert len(out) == 7
    _assert_valid_path(out, blocked=set(), endpoints=(path[0], path[-1]))


def test_coils_distance_four_to_nine():
    path = _straight(4)
    out = coil_to_length(path, 9, blocked=set())
    assert len(out) == 9
    _assert_valid_path(out, blocked=set(), endpoints=(path[0], path[-1]))


def test_already_exact_length_returned_unchanged():
    path = _straight(4)
    out = coil_to_length(path, len(path), blocked=set())
    assert out == path


def test_does_not_mutate_input_path():
    path = _straight(4)
    original = list(path)
    coil_to_length(path, 9, blocked=set())
    assert path == original


# 2. An odd shortfall is impossible on a grid.

def test_odd_shortfall_returns_none():
    path = _straight(4)                                   # 5 cells
    assert coil_to_length(path, 6, blocked=set()) is None  # shortfall 1
    assert coil_to_length(path, 8, blocked=set()) is None  # shortfall 3


def test_never_shortens():
    path = _straight(4)                                    # 5 cells
    assert coil_to_length(path, 3, blocked=set()) is None


# 3. Hemmed in on all sides collides with nothing -- it gives up instead.

def test_hemmed_in_on_all_sides_returns_none():
    path = _straight(4)                                    # (0,0)..(0,4)
    # Every staple off this path needs a cell at row -1 or row +1, in one
    # of columns 0..4 -- the only rows/columns any edge of this path can
    # reach. Fence both rows completely and there is nowhere left to coil.
    blocked = {(-1, c) for c in range(5)} | {(1, c) for c in range(5)}
    assert coil_to_length(path, 7, blocked) is None


def test_finds_the_one_gap_left_open():
    """Same fence as above but for one pair of cells -- must find exactly it."""
    path = _straight(4)
    blocked = {(-1, c) for c in range(5)} | {(1, c) for c in range(5)}
    blocked.discard((1, 2))
    blocked.discard((1, 3))    # the only usable staple: edge (0,2)-(0,3)
    out = coil_to_length(path, 7, blocked)
    _assert_valid_path(out, blocked, endpoints=(path[0], path[-1]))
    assert len(out) == 7
    assert (1, 2) in out and (1, 3) in out


# 4. Every returned path above was already run through `_assert_valid_path`;
# these two add blocked-adjacent grids (an L-bend and a vertical path) so
# the helper is exercised beyond the single straight-line shape.

def test_coils_with_blocked_cells_present_elsewhere():
    path = _straight(4)
    blocked = {(5, 5), (5, 6), (-5, -5)}     # far away, must not matter
    out = coil_to_length(path, 9, blocked)
    _assert_valid_path(out, blocked, endpoints=(path[0], path[-1]))
    assert len(out) == 9


def test_coils_a_vertical_path():
    path = [(0, 0), (1, 0), (2, 0), (3, 0)]  # Manhattan distance 3
    out = coil_to_length(path, 6, blocked=set())
    _assert_valid_path(out, blocked=set(), endpoints=(path[0], path[-1]))
    assert len(out) == 6
