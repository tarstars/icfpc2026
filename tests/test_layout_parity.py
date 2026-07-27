"""The parity constraint that unfreezes the placer on timing machines.

`layout_solve` used to pin a length-exact pipe with
``model.Add(dist == conn.length - 1)`` -- an exact MANHATTAN DISTANCE
between the two ports. That is a category error. A grid path between two
cells at Manhattan distance ``d`` can have length ``d``, ``d+2``, ``d+4``,
... because every detour off the straight line spends one cell going out
and one coming back. Requiring the distance to equal ``length - 1`` fixes
the geometric relation between two rooms when all the machine actually
needs is that a path of that many cells exists.

On the live little-little-man machine that pinned 231 pipes when 6 needed
it, and the placement could not move at all.

These tests pin the ARITHMETIC of the replacement, which is the part that
can silently go wrong: it is easy to relax the constraint so far that it
no longer says anything, and a solver that accepts every distance still
passes any test that only checks "a placement was found". So the
must-fail cases below matter more than the must-pass ones.
"""

from __future__ import annotations

import pytest
from ortools.sat.python import cp_model

# the exact constraint layout_solve emits for a length-exact pipe
def _feasible(distance: int, length: int) -> bool:
    """Can a pipe of `length` cells span ports `distance` apart?"""
    model = cp_model.CpModel()
    dist = model.NewIntVar(0, 10_000, "dist")
    model.Add(dist == distance)
    model.Add(dist <= length - 1)
    detours = model.NewIntVar(0, length, "k")
    model.Add(length - 1 - dist == 2 * detours)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5.0
    return solver.Solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)


@pytest.mark.parametrize("distance", [4, 2, 0])
def test_matching_parity_is_feasible(distance):
    """length-1 == 4: the straight run and every two-cell detour fit."""
    assert _feasible(distance, length=5)


@pytest.mark.parametrize("distance", [3, 1])
def test_wrong_parity_is_rejected(distance):
    """The test that proves the constraint was RELAXED, not DELETED.

    A path cannot cover an odd residual: each detour costs exactly two
    cells, so distance and length-1 must share parity.
    """
    assert not _feasible(distance, length=5)


@pytest.mark.parametrize("distance", [5, 6, 12])
def test_ports_farther_apart_than_the_pipe_is_rejected(distance):
    """A pipe can never be SHORTER than the straight line between its
    ends -- that is the direction which deadlocks, since a pipe's length
    is its capacity as well as its delay."""
    assert not _feasible(distance, length=5)


def test_the_old_equality_was_strictly_stronger():
    """Every distance the old constraint allowed, the new one still allows.

    The relaxation must not have changed which placements are legal, only
    which are *considered* -- so the one distance the equality permitted
    stays permitted.
    """
    length = 9
    assert _feasible(length - 1, length)          # what the equality pinned
    # ...and it now also admits the shorter, coilable separations
    assert _feasible(length - 3, length)
    assert _feasible(length - 5, length)


def test_a_two_cell_pipe_admits_only_adjacency():
    """MIN_PIPE is 2, and a 2-cell exact pipe has length-1 == 1, so the
    ports must be exactly one apart -- distance 0 has the wrong parity."""
    assert _feasible(1, length=2)
    assert not _feasible(0, length=2)


def test_solver_module_uses_a_non_shadowing_name():
    """`slack` is `solve`'s own keyword argument; rebinding it to a CP-SAT
    variable inside the constraint loop shadows it for the rest of the
    call. It was written that way once and is easy to reintroduce."""
    import inspect

    from littleman import layout_solve

    source = inspect.getsource(layout_solve.solve)
    assert "slack = model.NewIntVar" not in source
    assert "detours = model.NewIntVar" in source
