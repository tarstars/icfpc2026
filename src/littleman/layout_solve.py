"""L0 placer: CP-SAT over rigid rooms, minimising Chebyshev diameter.

Design notes that matter (claude_32):

* The objective is `max(W, H)`, NOT area. Slack in the minor dimension is
  free, so the model minimises one variable `D` bounding both extents.
  Area-minimising packers systematically make the wrong trade here.
* Rooms are rigid and never rotated: their text is copied verbatim, which
  is what makes a re-placement behaviour-preserving.
* Rooms are inflated by one cell on every side before the no-overlap
  constraint. That buys three things at once: the server's
  no-shared-wall-cells rule, a lane for a pipe to leave any wall, and the
  "a pipe grazing a wall counts as connected" hazard that cost us a
  submission.
* Connections are modelled as a Manhattan-distance budget between the two
  ports, not as routed paths. Routing happens afterwards; the model only
  has to leave enough room for it. For timing-sensitive machines the
  distance is pinned to an equality so a `q`/`R`/`U` machine cannot have
  its meaning changed by a shorter path.

The placer proposes; `layout_gate` disposes. Nothing here is trusted
until the binding audit and the judge agree with the original artifact.
"""

from __future__ import annotations

from dataclasses import dataclass

from .layout_ir import Conn, Layout, Port

try:                                    # optional: the stack degrades to hand layouts
    from ortools.sat.python import cp_model
    HAVE_ORTOOLS = True
except ImportError:                     # pragma: no cover
    cp_model = None
    HAVE_ORTOOLS = False

# A pipe needs at least 2 cells (the server rejects 1-cell pipes), and a
# port sits one cell outside its room's wall, so two ports that face each
# other need this much Manhattan separation at minimum.
MIN_PIPE = 2


@dataclass
class Placement:
    tops: list[int]
    lefts: list[int]
    width: int
    height: int

    @property
    def footprint(self) -> int:
        return max(self.width, self.height) ** 2


def _port_cell(top: int, left: int, room, port: Port) -> tuple:
    """The (row, col) expression of a port, given its room's origin."""
    if port.side == "N":
        return (top - 1, left + port.offset)
    if port.side == "S":
        return (top + room.height, left + port.offset)
    if port.side == "W":
        return (top + port.offset, left - 1)
    return (top + port.offset, left + room.width)


def solve(layout: Layout, *, seconds: float = 30.0, slack: int = 6,
          workers: int = 8, channel: int = 1) -> Placement | None:
    """Place `layout`'s rooms to minimise max(W,H). None if no model.

    `channel` is the guaranteed gap between rooms. 1 admits a pipe that
    TERMINATES at one of the two rooms; a pipe passing THROUGH between two
    rooms it does not terminate at needs 3, because it may not be adjacent
    to a non-endpoint room (the grazing rule). Callers escalate.
    """
    if not HAVE_ORTOOLS:
        return None
    rooms = layout.rooms
    model = cp_model.CpModel()
    # A generous but finite frame: the current box is always feasible, so
    # bound by it. The solver's job is to do better.
    span = max(layout.width, layout.height)
    ub = span + slack

    tops, lefts, xs, ys = [], [], [], []
    for room in rooms:
        top = model.NewIntVar(1, ub, f"t{room.index}")
        left = model.NewIntVar(1, ub, f"l{room.index}")
        tops.append(top)
        lefts.append(left)
        # Inflate by ONE cell total (not one per side). The server rule is
        # that rooms must not SHARE wall cells, i.e. a 1-cell gap suffices
        # -- and that gap is exactly where a pipe runs. Inflating both
        # sides demanded a 2-cell gap and made real artifacts INFEASIBLE.
        ys.append(model.NewIntervalVar(
            top, room.height + channel, top + room.height + channel,
            f"y{room.index}"))
        xs.append(model.NewIntervalVar(
            left, room.width + channel, left + room.width + channel,
            f"x{room.index}"))
    model.AddNoOverlap2D(xs, ys)

    diameter = model.NewIntVar(1, ub, "D")
    for room, top, left in zip(rooms, tops, lefts):
        model.Add(top + room.height <= diameter)
        model.Add(left + room.width <= diameter)

    # Connections: leave enough Manhattan room to route, and pin the
    # distance exactly when the machine's logic observes pipe timing.
    for conn in layout.conns:
        src, dst = conn.src, conn.dst
        sr, sc = _port_cell(tops[src.room], lefts[src.room],
                            rooms[src.room], src)
        dr, dc = _port_cell(tops[dst.room], lefts[dst.room],
                            rooms[dst.room], dst)
        dist = model.NewIntVar(0, 4 * ub, f"d{id(conn)}")
        ar = model.NewIntVar(0, 2 * ub, f"ar{id(conn)}")
        ac = model.NewIntVar(0, 2 * ub, f"ac{id(conn)}")
        model.AddAbsEquality(ar, sr - dr)
        model.AddAbsEquality(ac, sc - dc)
        model.Add(dist == ar + ac)
        if conn.exact:
            model.Add(dist == conn.length - 1)
        else:
            # Only a LOWER bound. Capping length near the original forbade
            # the spreading that squarification needs -- and cold-path pipe
            # length is free (plotter's EUPD went 4 -> 335 cells with zero
            # tick cost). Tick regressions are caught by the judge, not
            # prevented here.
            model.Add(dist >= MIN_PIPE - 1)

    # symmetry breaking: pin the largest room to the origin corner
    biggest = max(rooms, key=lambda r: r.height * r.width).index
    model.Add(tops[biggest] == 1)
    model.Add(lefts[biggest] == 1)

    model.Minimize(diameter)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = seconds
    solver.parameters.num_search_workers = workers
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None
    t = [solver.Value(v) for v in tops]
    l = [solver.Value(v) for v in lefts]
    w = max(l[i] + r.width for i, r in enumerate(rooms))
    h = max(t[i] + r.height for i, r in enumerate(rooms))
    return Placement(tops=t, lefts=l, width=w, height=h)
