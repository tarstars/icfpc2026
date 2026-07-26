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
    # Per connection, the (source, destination) ports the model CHOSE. None
    # means "as in the IR"; callers must prefer these when present.
    ports: list[tuple[Port, Port]] | None = None
    # The square the model guaranteed everything fits in, ports included.
    # Rooms alone can be narrower; the frame is what the router may use.
    frame: int = 0

    @property
    def footprint(self) -> int:
        return max(self.width, self.height) ** 2

    def ports_for(self, index: int, conn: Conn) -> tuple[Port, Port]:
        return self.ports[index] if self.ports else (conn.src, conn.dst)


def _port_cell(top: int, left: int, room, port: Port) -> tuple:
    """The (row, col) expression of a port, given its room's origin."""
    if port.side == "N":
        return (top - 1, left + port.offset)
    if port.side == "S":
        return (top + room.height, left + port.offset)
    if port.side == "W":
        return (top + port.offset, left - 1)
    return (top + port.offset, left + room.width)


_SIDES = ("N", "S", "W", "E")
# The direction a pipe's first cell must point, per wall (a server rule).
_AWAY = {"N": (-1, 0), "S": (1, 0), "W": (0, -1), "E": (0, 1)}


def _port_vars(model, room, top, left, port: Port, movable: bool, ub: int,
               tag: str):
    """(row, col, side_literals) for one endpoint.

    A movable endpoint gets one Boolean per wall and channelled position
    constraints; offsets stay one cell clear of both corners, because a
    corner cell is adjacent to TWO walls and `sim._find_pipes` would let
    either claim it. A pinned endpoint is the same cell the IR recorded,
    expressed relative to the room so it travels with it.
    """
    row = model.NewIntVar(0, ub + 2, f"pr{tag}")
    col = model.NewIntVar(0, ub + 2, f"pc{tag}")
    step_r = model.NewIntVar(-1, 1, f"sr{tag}")
    step_c = model.NewIntVar(-1, 1, f"sc{tag}")
    if not movable:
        fixed_r, fixed_c = _port_cell(top, left, room, port)
        model.Add(row == fixed_r)
        model.Add(col == fixed_c)
        model.Add(step_r == _AWAY[port.side][0])
        model.Add(step_c == _AWAY[port.side][1])
        return row, col, step_r, step_c, {port.side: 1}
    lits = {side: model.NewBoolVar(f"b{tag}{side}") for side in _SIDES}
    if room.width < 3:                     # no non-corner offset on N/S
        model.Add(lits["N"] == 0)
        model.Add(lits["S"] == 0)
    if room.height < 3:
        model.Add(lits["W"] == 0)
        model.Add(lits["E"] == 0)
    model.AddExactlyOne(lits.values())
    for side in ("N", "S"):
        anchor = top - 1 if side == "N" else top + room.height
        model.Add(row == anchor).OnlyEnforceIf(lits[side])
        model.Add(col >= left + 1).OnlyEnforceIf(lits[side])
        model.Add(col <= left + room.width - 2).OnlyEnforceIf(lits[side])
    for side in ("W", "E"):
        anchor = left - 1 if side == "W" else left + room.width
        model.Add(col == anchor).OnlyEnforceIf(lits[side])
        model.Add(row >= top + 1).OnlyEnforceIf(lits[side])
        model.Add(row <= top + room.height - 2).OnlyEnforceIf(lits[side])
    for side, (dr, dc) in _AWAY.items():
        model.Add(step_r == dr).OnlyEnforceIf(lits[side])
        model.Add(step_c == dc).OnlyEnforceIf(lits[side])
    return row, col, step_r, step_c, lits


def _cell_id(model, row, col, stride: int, tag: str):
    """A single integer naming a cell, so `AddAllDifferent` can own it."""
    ident = model.NewIntVar(0, stride * stride, f"id{tag}")
    model.Add(ident == row * stride + col)
    return ident


def _clear_of_rooms(model, rooms, tops, lefts, row, col, skip, tag: str,
                    pad: int = 0):
    """Forbid a cell from landing inside (or, with `pad`, beside) a room.

    Without this the placer happily chose a wall that faces straight into
    a neighbour one cell away: legal as a port, but the pipe's first cell
    has to point AWAY from the wall and there was nowhere to point. That
    was the whole of M1's "cannot leave source wall". `pad=1` additionally
    keeps the cell off a room's flank, which is the router's grazing rule
    -- a pipe cell touching a room it does not terminate at is a pipe INTO
    that room as far as the server is concerned.
    """
    skip = {skip} if isinstance(skip, int) else set(skip)
    for room in rooms:
        if room.index in skip:
            continue
        top, left = tops[room.index], lefts[room.index]
        options = []
        for name, expr in (
                ("n", row <= top - 1 - pad),
                ("s", row >= top + room.height + pad),
                ("w", col <= left - 1 - pad),
                ("e", col >= left + room.width + pad)):
            lit = model.NewBoolVar(f"clr{tag}_{room.index}{name}")
            model.Add(expr).OnlyEnforceIf(lit)
            options.append(lit)
        model.AddBoolOr(options)


def endpoint_freedom(layout: Layout) -> tuple[list[bool], list[bool]]:
    """Per connection: may its source / its destination port be moved?

    A room's `s` binds through `sim._nearest_outgoing`, which ranks only
    THAT room's outgoing pipes; `r`/`q` rank its incoming ones. So an
    endpoint is free exactly when its room has a single pipe in that
    direction: there is nothing to rank and no tie to break, and the port
    may go to any wall at any offset. Two exceptions, both read off `sim`:

    * a `display` room reads the attach SIDE as the port's MEANING
      (top=addr, bottom=swap, left=data, right is a load error), so moving
      one silently renames it;
    * `U` calls `_turn_away`, which sets the man's direction from which
      wall the incoming pipe arrives at -- so with any `U` present every
      incoming port is behaviour-carrying, single or not.
    """
    out_count: dict[int, int] = {}
    in_count: dict[int, int] = {}
    for conn in layout.conns:
        out_count[conn.src.room] = out_count.get(conn.src.room, 0) + 1
        in_count[conn.dst.room] = in_count.get(conn.dst.room, 0) + 1
    turns = any("U" in line for room in layout.rooms for line in room.lines[1:-1])
    src_free, dst_free = [], []
    for conn in layout.conns:
        src_room = layout.rooms[conn.src.room]
        dst_room = layout.rooms[conn.dst.room]
        src_free.append(out_count[conn.src.room] <= 1
                        and src_room.kind != "display")
        dst_free.append(in_count[conn.dst.room] <= 1 and not turns
                        and dst_room.kind != "display")
    return src_free, dst_free


def solve(layout: Layout, *, seconds: float = 30.0, slack: int = 6,
          workers: int = 8, channel: int = 1, free_ports: bool = True,
          diameter_hint: int | None = None,
          pads: dict | None = None) -> Placement | None:
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
        # `pads` is the repair loop's only lever: a uniform channel is the
        # wrong shape of answer when one corridor is short of lanes, so a
        # room that congested gets its own extra clearance.
        gap = channel + (pads or {}).get(room.index, 0)
        ys.append(model.NewIntervalVar(
            top, room.height + gap, top + room.height + gap, f"y{room.index}"))
        xs.append(model.NewIntervalVar(
            left, room.width + gap, left + room.width + gap, f"x{room.index}"))
    model.AddNoOverlap2D(xs, ys)

    diameter = model.NewIntVar(1, ub, "D")
    for room, top, left in zip(rooms, tops, lefts):
        model.Add(top + room.height <= diameter)
        model.Add(left + room.width <= diameter)

    # Connections: leave enough Manhattan room to route, and pin the
    # distance exactly when the machine's logic observes pipe timing.
    src_free, dst_free = endpoint_freedom(layout)
    if not free_ports:
        src_free = [False] * len(layout.conns)
        dst_free = [False] * len(layout.conns)
    port_lits: list[tuple] = []
    dists = []
    # Every port cell, and every cell a pipe steps out to, belongs to
    # exactly ONE pipe. Nothing said so before, and two endpoints landing
    # on the same cell is a conflict no router can negotiate away: the
    # repair loop grew tcp's box from 32 to 49 chasing it.
    stride = ub + 4
    cell_ids = []
    for ci, conn in enumerate(layout.conns):
        src, dst = conn.src, conn.dst
        sr, sc, ssr, ssc, s_lits = _port_vars(
            model, rooms[src.room], tops[src.room], lefts[src.room], src,
            src_free[ci], ub, f"{ci}s")
        dr, dc, dsr, dsc, d_lits = _port_vars(
            model, rooms[dst.room], tops[dst.room], lefts[dst.room], dst,
            dst_free[ci], ub, f"{ci}d")
        port_lits.append((s_lits, sr, sc, d_lits, dr, dc))
        # The port cell itself, and the cell one step further out, must be
        # clear of every OTHER room -- the pipe has to start (and arrive)
        # somewhere.
        for cr, cc, own, tag in ((sr, sc, src.room, f"{ci}s"),
                                 (dr, dc, dst.room, f"{ci}d")):
            # pad=1: a port cell may touch its OWN room and nothing else,
            # or the server counts the pipe as connected to the neighbour
            # too -- and `sim._find_pipes` may start a second trace there.
            _clear_of_rooms(model, rooms, tops, lefts, cr, cc, own, tag, pad=1)
            model.Add(cr <= diameter - 1)
            model.Add(cc <= diameter - 1)
            cell_ids.append(_cell_id(model, cr, cc, stride, tag))
        ends = {src.room, dst.room}
        for base_r, base_c, st_r, st_c, tag in (
                (sr, sc, ssr, ssc, f"{ci}sa"), (dr, dc, dsr, dsc, f"{ci}da")):
            ar_ = model.NewIntVar(0, ub + 3, f"ar_{tag}")
            ac_ = model.NewIntVar(0, ub + 3, f"ac_{tag}")
            model.Add(ar_ == base_r + st_r)
            model.Add(ac_ == base_c + st_c)
            model.Add(ar_ <= diameter - 1)
            model.Add(ac_ <= diameter - 1)
            _clear_of_rooms(model, rooms, tops, lefts, ar_, ac_, ends, tag,
                            pad=1)
            cell_ids.append(_cell_id(model, ar_, ac_, stride, tag))
        dist = model.NewIntVar(0, 4 * ub, f"d{ci}")
        ar = model.NewIntVar(0, 2 * ub, f"ar{ci}")
        ac = model.NewIntVar(0, 2 * ub, f"ac{ci}")
        model.AddAbsEquality(ar, sr - dr)
        model.AddAbsEquality(ac, sc - dc)
        model.Add(dist == ar + ac)
        dists.append(dist)
        if conn.exact:
            model.Add(dist == conn.length - 1)
        else:
            # Only a LOWER bound. Capping length near the original forbade
            # the spreading that squarification needs -- and cold-path pipe
            # length is free (plotter's EUPD went 4 -> 335 cells with zero
            # tick cost). Tick regressions are caught by the judge, not
            # prevented here.
            model.Add(dist >= MIN_PIPE - 1)

    model.AddAllDifferent(cell_ids)

    # symmetry breaking: keep the largest room in the origin corner, but
    # leave it the two-cell slack a north/west port needs to exist at all.
    biggest = max(rooms, key=lambda r: r.height * r.width).index
    model.Add(tops[biggest] <= 2)
    model.Add(lefts[biggest] <= 2)
    if diameter_hint is not None:
        model.Add(diameter <= diameter_hint)

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = workers
    # Two phases, lexicographic. Phase A gets the box; phase B then spends
    # its budget pointing the free ports AT each other, which is what makes
    # the placement routable -- a minimal box with ports facing outward is
    # exactly the unroutable state M1 kept producing.
    model.Minimize(diameter)
    solver.parameters.max_time_in_seconds = max(seconds * 0.6, 1.0)
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None
    best = solver.Value(diameter)
    if dists:
        model.Add(diameter <= best)
        model.Minimize(sum(dists))
        solver.parameters.max_time_in_seconds = max(seconds * 0.4, 1.0)
        phase_b = solver.Solve(model)
        if phase_b not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None
    t = [solver.Value(v) for v in tops]
    l = [solver.Value(v) for v in lefts]
    w = max(l[i] + r.width for i, r in enumerate(rooms))
    h = max(t[i] + r.height for i, r in enumerate(rooms))
    ports = []
    for ci, conn in enumerate(layout.conns):
        s_lits, sr, sc, d_lits, dr, dc = port_lits[ci]
        ports.append((
            _read_port(solver, conn.src, rooms[conn.src.room], s_lits,
                       solver.Value(tops[conn.src.room]),
                       solver.Value(lefts[conn.src.room]),
                       solver.Value(sr), solver.Value(sc)),
            _read_port(solver, conn.dst, rooms[conn.dst.room], d_lits,
                       solver.Value(tops[conn.dst.room]),
                       solver.Value(lefts[conn.dst.room]),
                       solver.Value(dr), solver.Value(dc)),
        ))
    return Placement(tops=t, lefts=l, width=w, height=h, ports=ports,
                     frame=best)


def _read_port(solver, original: Port, room, lits, top: int, left: int,
               row: int, col: int) -> Port:
    """Turn a solved port cell back into a room-relative (side, offset)."""
    if not isinstance(lits, dict) or len(lits) == 1:
        return original
    side = next(s for s in _SIDES if solver.Value(lits[s]))
    offset = col - left if side in ("N", "S") else row - top
    return Port(original.room, side, offset)
