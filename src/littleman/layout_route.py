"""Route pipes for a solver placement, then re-emit the artifact.

Three routers over one primitive, plus a loop that re-places when routing
proves the placement wrong:

* `route` -- greedy, shortest-first, hard obstacles. Fast and usually
  enough for small instances.
* `route_negotiated` -- PathFinder. Every pipe takes its best path, then a
  rising price on contested cells sorts the lanes out. Needed because a
  greedy router loses whenever an early pipe takes the only lane a later
  one wanted, and reordering only shuffles who loses.
* `place_route_repair` -- feeds the contested cells back to the placer as
  per-room clearance. Measured on plotter_05: a uniform channel and even a
  20-cell frame margin left the SAME twelve cells contested, because the
  shortage was one corridor rather than global space.

What grazing actually costs, measured rather than assumed: our own live
plotter_05 has 172 interior pipe cells flush against a room and loads
fine, so a blanket ban on adjacency is far stricter than the server and
made real placements unroutable. The rules that are real are narrower:

* an ARROW next to a wall pointing away from it starts a whole extra pipe
  in `sim._find_pipes`, whose trace then walks into this pipe's body and
  the machine fails to load. Only bends carry arrows, so `_shortest`
  searches over (cell, heading) and refuses to TURN where the cell behind
  the new heading is a room;
* an INPUT room counts a pipe merely running alongside it as connected,
  and rejects the layout 0/0 -- that one cost us reverse_03 -- so input
  rooms alone are fenced off.

Bindings survive re-placement by construction: `sim._outgoing` considers
only pipes attached to the man's OWN room, and ports keep their
room-relative side/offset, so every man-to-port distance is unchanged.
The one exception is a tie between two ports of the same room, whose
tie-break uses ABSOLUTE coordinates -- which is precisely what
`room_ports.audit` reports as margin 0. Gate on it.
"""

from __future__ import annotations

import heapq
import random
from collections import deque

from .canvas import Canvas
from .layout_ir import Layout
from .layout_solve import Placement, _port_cell


class RouteError(str):
    """A failure string that also remembers WHICH connection failed.

    The router is greedy, so the identity of the loser is the one piece of
    information a retry can act on: putting it first is what turns most
    congestion failures into successes.
    """

    conn: int

    def __new__(cls, conn: int, message: str, cells=()):
        obj = super().__new__(cls, f"conn {conn}: {message}")
        obj.conn = conn
        # The cells that could not be shared out. This is what the repair
        # loop acts on: global channel widening is useless when the
        # shortage is one corridor, which is what plotter measured.
        obj.cells = tuple(cells)
        return obj


def _room_cells(layout: Layout, place: Placement) -> dict[tuple[int, int], int]:
    """Every cell owned by a room -> that room's index."""
    owned: dict[tuple[int, int], int] = {}
    for room in layout.rooms:
        top, left = place.tops[room.index], place.lefts[room.index]
        for dr in range(room.height):
            for dc in range(room.width):
                owned[(top + dr, left + dc)] = room.index
    return owned


def _adjacent_rooms(cell: tuple[int, int],
                    owned: dict[tuple[int, int], int]) -> set[int]:
    r, c = cell
    out = set()
    for nb in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
        if nb in owned:
            out.add(owned[nb])
    return out


def route(layout: Layout, place: Placement, *, margin: int = 0,
          order: list[int] | None = None):
    """Route every connection greedily. Returns (paths, None) or (None, err).

    Routing happens inside the placement's SQUARE, not its bounding box:
    the score is `max(W,H)^2`, so every cell of the minor dimension is
    already paid for and using it costs nothing. `margin` widens that
    square further, which does cost score, so it defaults to none.
    """
    owned = _room_cells(layout, place)
    nets = [_net_endpoints(layout, place, ci) for ci in range(len(layout.conns))]
    reserved = {cell for start, _f, goal, _e, _a in nets for cell in (start, goal)}
    hi = max(place.width, place.height, place.frame) + margin - 1
    used: set[tuple[int, int]] = set()
    paths = []
    if order is None:
        # Longest first: the constrained routes get the free grid.
        order = sorted(range(len(layout.conns)),
                       key=lambda i: -layout.conns[i].length)
    for ci in order:
        start, first, goal, ends, away = nets[ci]
        if start in owned or goal in owned:
            return None, RouteError(ci, "port cell inside a room")
        blocked = set(owned) | reserved | _forbidden_flanks(layout, owned, ends)
        # Order matters: `discard(goal)` un-blocks THIS net's own port, and
        # doing it after the union with `used` would also un-block a cell a
        # previous pipe had already taken. That produced two pipes sharing
        # one cell and a machine that would not load.
        blocked.discard(goal)
        blocked |= used
        blocked.add(start)
        if first in blocked and first != goal:
            return None, RouteError(ci, "cannot leave source wall")
        path = _shortest(first, away, goal, blocked, lambda _cell: 1.0, hi,
                         owned)
        if path is None:
            return None, RouteError(ci, f"no route ({start} -> {goal})")
        path = [start] + path
        if len(path) < 2:
            return None, RouteError(ci, "degenerate path")
        conn = layout.conns[ci]
        if conn.exact and len(path) != conn.length:
            return None, RouteError(
                ci, f"timing-exact needs {conn.length}, routed {len(path)}")
        used.update(path)
        paths.append((ci, path))
    paths.sort()
    bad = _violations(layout, place, paths)
    if bad:
        return None, RouteError(bad[0][0], bad[0][1])
    return paths, None


def _violations(layout: Layout, place: Placement, paths) -> list:
    """Last line of defence: cell-disjoint, and no arrow beside a wall.

    Both failures show up only as a LoadError from the server-side parser,
    so they are checked here rather than discovered by the gate.
    """
    owned = _room_cells(layout, place)
    seen: dict = {}
    out = []
    for ci, path in paths:
        for cell in path:
            if cell in seen:
                out.append((ci, f"shares {cell} with conn {seen[cell]}"))
            seen[cell] = ci
        for i in range(1, len(path) - 1):
            step = (path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1])
            came = (path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1])
            if came != step and (path[i][0] - step[0],
                                 path[i][1] - step[1]) in owned:
                out.append((ci, f"bend at {path[i]} is flush against a wall"))
    return out


_ARROW = {(-1, 0): "^", (1, 0): "v", (0, -1): "<", (0, 1): ">"}
_BODY = {(-1, 0): "|", (1, 0): "|", (0, -1): "-", (0, 1): "-"}


_AWAY = {"N": (-1, 0), "S": (1, 0), "W": (0, -1), "E": (0, 1)}
_INTO = {"N": "v", "S": "^", "W": ">", "E": "<"}


def glyphs_for(path, src_side: str | None = None,
               dst_side: str | None = None) -> list[str]:
    """Glyphs for a routed path, matching the convention real artifacts use.

    Read off working machines via the IR: an arrowhead on the FIRST cell,
    on every BEND, and on the LAST cell; `-`/`|` bodies on straight runs.
    Each glyph encodes the direction of travel LEAVING that cell, except
    the last, which points into the destination wall.
    """
    out = []
    for i, cell in enumerate(path):
        if i == len(path) - 1:
            # The LAST cell points INTO the destination wall, which is not
            # the travel direction when the pipe arrives sideways. Read off
            # working artifacts: history conn0 travels east and ends 'v'.
            out.append(_INTO[dst_side] if dst_side else _BODY[(0, 1)])
            continue
        nxt = path[i + 1]
        step = (nxt[0] - cell[0], nxt[1] - cell[1])
        if i == 0:
            out.append(_ARROW[step])            # away from the source wall
            continue
        prev = path[i - 1]
        came = (cell[0] - prev[0], cell[1] - prev[1])
        out.append(_ARROW[step] if came != step else _BODY[step])
    return out


def emit(layout: Layout, place: Placement, paths) -> str:
    """Render rooms at their placed positions and draw the routed pipes."""
    canvas = Canvas()
    for room in layout.rooms:
        canvas.put(place.tops[room.index], place.lefts[room.index], room.lines)
    for ci, path in paths:
        src_port, dst_port = place.ports_for(ci, layout.conns[ci])
        for cell, glyph in zip(path, glyphs_for(path, src_port.side,
                                                dst_port.side)):
            canvas.cells[cell] = glyph
    return canvas.render()


def _net_endpoints(layout: Layout, place: Placement, ci: int):
    conn = layout.conns[ci]
    src_port, dst_port = place.ports_for(ci, conn)
    start = _port_cell(place.tops[src_port.room], place.lefts[src_port.room],
                       layout.rooms[src_port.room], src_port)
    goal = _port_cell(place.tops[dst_port.room], place.lefts[dst_port.room],
                      layout.rooms[dst_port.room], dst_port)
    away = _AWAY[src_port.side]
    return start, (start[0] + away[0], start[1] + away[1]), goal, \
        {src_port.room, dst_port.room}, away


def _forbidden_flanks(layout: Layout, owned, ends) -> set:
    """Cells beside an INPUT room this pipe does not connect to.

    The one grazing rule the server has actually charged us for: it counts
    a pipe merely running alongside an input room's wall as connected, and
    rejects the layout 0/0 with "the input room has more than one outgoing
    pipe". Ordinary rooms tolerate grazing -- our live artifacts do it by
    the hundred cells -- so only input rooms are fenced.
    """
    fenced = {room.index for room in layout.rooms
              if room.kind == "input" and room.index not in ends}
    if not fenced:
        return set()
    return {cell for cell in _flanks(owned)
            if _adjacent_rooms(cell, owned) & fenced}


def _shortest(first, first_dir, goal, blocked, cost, hi, owned):
    """Dijkstra over (cell, heading), because a BEND next to a wall is illegal.

    Grazing a wall is NOT what the server objects to -- our own live
    plotter has 172 pipe cells flush against a room and loads fine. What
    it cannot survive is an ARROW next to a wall pointing away from it:
    `sim._find_pipes` starts a fresh pipe trace at exactly that pattern,
    and the phantom trace then walks into this pipe's body and the machine
    fails to load with "bad pipe glyph". Only bends carry arrows, so the
    rule is precisely: do not turn where the cell behind the new heading
    is a room. Straight runs may hug as much wall as they like.
    """
    start_state = (first, first_dir)
    dist = {start_state: cost(first)}
    heap = [(dist[start_state], first, first_dir)]
    prev: dict = {start_state: None}
    while heap:
        d, cur, came = heapq.heappop(heap)
        if d > dist.get((cur, came), d + 1):
            continue
        if cur == goal:
            path = []
            state = (cur, came)
            while state is not None:
                path.append(state[0])
                state = prev[state]
            path.reverse()
            return path
        r, c = cur
        for step in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            if step == (-came[0], -came[1]):
                continue                       # `sim` rejects a reversal
            if step != came and (r - step[0], c - step[1]) in owned:
                continue                       # a bend flush against a wall
            nb = (r + step[0], c + step[1])
            if not (0 <= nb[0] <= hi and 0 <= nb[1] <= hi) or nb in blocked:
                continue
            nd = d + cost(nb)
            if nd < dist.get((nb, step), 1 << 60):
                dist[(nb, step)] = nd
                prev[(nb, step)] = (cur, came)
                heapq.heappush(heap, (nd, nb, step))
    return None


def route_negotiated(layout: Layout, place: Placement, *, iterations: int = 120,
                     margin: int = 0, growth: float = 1.3,
                     history_step: float = 0.5, seed: int = 0):
    """PathFinder (Ebeling/McMurchie): price the contested cells apart.

    A greedy router loses whenever an early pipe takes the only lane a
    later one needed, and reordering only shuffles who loses. Negotiation
    lets every pipe take its best path, then charges a rising price for
    cells more than one pipe wants. Hard obstacles stay hard: a cell
    inside a room, or flush against an INPUT room this pipe does not
    terminate at, is never for sale.

    Two details are the whole algorithm, and getting them wrong is what
    made the first version plateau. **Rip-up is per net, not per pass**:
    occupancy persists across iterations and only the net being re-routed
    is subtracted from it, so every net always sees all the others.
    Clearing the field at the top of each pass instead made each iteration
    a fresh greedy sweep whose first net saw an empty grid; plotter_05
    stuck at 18 contested cells for 120 passes and 190s. Per-net rip-up
    with a shuffled order took the same instance to 8 in 3s. **The price
    is geometric and effectively uncapped** (0.5 -> 200), so a cell two
    pipes both want ends up dearer than any detour that exists.

    What survives that is not congestion, and no amount of routing fixes
    it -- see `_crossings`.
    """
    owned = _room_cells(layout, place)
    hi = max(place.width, place.height, place.frame) + margin - 1
    nets = [_net_endpoints(layout, place, ci) for ci in range(len(layout.conns))]
    # Every port cell belongs to exactly ONE pipe. Leaving them merely
    # expensive rather than forbidden gave negotiation an unwinnable game:
    # two nets fighting over a cell that one of them is anchored to can
    # never separate, and the router reported "cells still shared" forever.
    reserved = {cell for start, _f, goal, _e, _a in nets for cell in (start, goal)}
    blocked_for = []
    for ci, (start, first, goal, ends, _away) in enumerate(nets):
        blocked = set(owned) | reserved | _forbidden_flanks(layout, owned, ends)
        blocked.discard(goal)
        blocked.add(start)
        # `_shortest` seeds its search AT `first` without testing it, so an
        # unchecked blocked `first` hands back a path whose second cell is
        # inside a room or on another net's port -- a machine that will not
        # load, and one `_violations` cannot phrase an explanation for.
        if first in blocked and first != goal:
            return None, RouteError(ci, "cannot leave source wall",
                                    cells=(first,))
        blocked_for.append(blocked)
    rng = random.Random(seed)
    history: dict = {}
    occupancy: dict = {}
    routed: list = [None] * len(nets)
    penalty = 0.5
    order = sorted(range(len(nets)), key=lambda i: -layout.conns[i].length)
    best = (1 << 30, None, None)
    for _ in range(iterations):
        for ci in order:
            if routed[ci] is not None:          # rip up THIS net only
                for cell in routed[ci][1:]:
                    occupancy[cell] -= 1
            start, first, goal, _ends, away = nets[ci]

            def cell_cost(cell, _h=history, _o=occupancy, _p=penalty):
                return (1.0 + _h.get(cell, 0.0)) * (1.0 + _p * _o.get(cell, 0))
            path = _shortest(first, away, goal, blocked_for[ci], cell_cost,
                             hi, owned)
            if path is None:
                return None, RouteError(ci, "no route at all (hard obstacles)",
                                        cells=(start, goal))
            path = [start] + path
            for cell in path[1:]:
                occupancy[cell] = occupancy.get(cell, 0) + 1
            routed[ci] = path
        paths = [(ci, path) for ci, path in enumerate(routed)]
        shared = [cell for cell, n in occupancy.items() if n > 1]
        improved = len(shared) < best[0]
        if improved:
            best = (len(shared), [(ci, list(p)) for ci, p in paths],
                    dict(occupancy))
        # Only worth closing when negotiation has already got near, and only
        # on a field it has not already tried: the settle pass is dozens of
        # exact re-routes and dominates the run time otherwise.
        if shared and improved and len(shared) <= _SETTLE_MAX:
            # Negotiation oscillates: the shared count on tcp went
            # 16-14-12-21-9-13 and never reached zero even with half the
            # frame empty. But most nets are already disjoint, so freeze
            # those and re-route only the losers against them as hard
            # obstacles -- that turns a near-miss into a solution.
            settled = _settle(layout, nets, blocked_for, paths, occupancy,
                              hi, owned)
            if settled is not None and not _violations(layout, place, settled):
                paths, shared = settled, []
        if not shared:
            return _accept(layout, place, paths)
        for cell in shared:
            history[cell] = history.get(cell, 0.0) + history_step * (
                occupancy[cell] - 1)
        penalty = min(penalty * growth, 200.0)
        # A fixed order re-runs the same standoff forever; shuffling gives
        # the loser of one pass first pick in the next.
        rng.shuffle(order)
    return None, _congestion_error(best)


# Freezing the disjoint pipes and hard-routing the losers costs an A* per
# contested net per random order, so it only pays once negotiation is near.
_SETTLE_MAX = 24


def _accept(layout: Layout, place: Placement, paths):
    """The checks a conflict-free path set still has to pass."""
    for ci, path in paths:
        conn = layout.conns[ci]
        if conn.exact and len(path) != conn.length:
            return None, RouteError(
                ci, f"timing-exact needs {conn.length}, routed {len(path)}")
        if len(path) < 2:
            return None, RouteError(ci, "degenerate path")
    bad = _violations(layout, place, paths)
    if bad:
        return None, RouteError(bad[0][0], bad[0][1])
    return paths, None


def _crossings(paths, occupancy) -> int:
    """How many contested cells are two pipes CROSSING at right angles.

    The number that decides whether to keep routing or go back and re-place.
    A cell two pipes want to run ALONG is congestion, and a price separates
    them. A cell where one runs north-south and the other east-west is a
    topological crossing, and the grid has exactly one layer. Measured on
    plotter_05 at 129: all eight residual cells were crossings, every one in
    open space with four free neighbours, and margins of 10, 20 and 40 left
    the count at exactly eight -- space was never the constraint.
    """
    axis: dict = {}
    for _ci, path in paths:
        for i, cell in enumerate(path):
            if occupancy.get(cell, 0) < 2:
                continue
            nxt = path[i + 1] if i + 1 < len(path) else cell
            prv = path[i - 1] if i else cell
            axis.setdefault(cell, set()).add(nxt[0] != cell[0]
                                             or prv[0] != cell[0])
    return sum(1 for kinds in axis.values() if len(kinds) > 1)


def _congestion_error(best) -> RouteError:
    count, paths, occupancy = best
    if paths is None:                                    # pragma: no cover
        return RouteError(0, "no iteration completed")
    contested = [cell for cell, n in occupancy.items() if n > 1]
    worst = max(occupancy.items(), key=lambda kv: kv[1])
    cross = _crossings(paths, occupancy)
    return RouteError(
        paths[0][0],
        f"{count} cells still shared ({cross} of them right-angle CROSSINGS, "
        f"which no single-layer router can price apart), worst {worst[1]} "
        f"pipes at {worst[0]}", cells=contested)


def _settle(layout, nets, blocked_for, paths, occupancy, hi, owned,
            orders: int = 40):
    """Keep the disjoint pipes, re-route the contested ones exactly."""
    contested = {ci for ci, path in paths
                 if any(occupancy.get(cell, 0) > 1 for cell in path[1:])}
    if not contested or len(contested) == len(paths):
        return None
    fixed = {cell for ci, path in paths if ci not in contested
             for cell in path[1:]}
    rng = random.Random(len(fixed))
    todo = sorted(contested, key=lambda i: -layout.conns[i].length)
    for attempt in range(orders):
        used = set(fixed)
        found = []
        for ci in todo:
            start, first, goal, _ends, away = nets[ci]
            path = _shortest(first, away, goal, blocked_for[ci] | used,
                             lambda _cell: 1.0, hi, owned)
            if path is None:
                break
            used |= set(path)
            found.append((ci, [start] + path))
        else:
            keep = [(ci, path) for ci, path in paths if ci not in contested]
            return sorted(keep + found)
        if attempt == 0:
            todo = list(contested)
        rng.shuffle(todo)
    return None


def _flanks(owned):
    """Every cell orthogonally adjacent to some room cell."""
    out = set()
    for (r, c) in owned:
        for nb in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if nb not in owned:
                out.add(nb)
    return out


def route_with_ripup(layout: Layout, place: Placement, *, tries: int = 8,
                     margin: int = 0, restarts: int = 0, seed: int = 0):
    """Route, and on failure re-run with the loser promoted to first.

    Straight rip-up-and-reorder, not negotiated congestion: the greedy
    router only ever loses to pipes routed BEFORE it, so promoting the
    victim is the smallest move that can fix the ordering. Cheap enough to
    run every time, and it converges in a handful of passes or not at all.
    """
    order = sorted(range(len(layout.conns)), key=lambda i: -layout.conns[i].length)
    err = None
    for _ in range(tries):
        paths, err = route(layout, place, margin=margin, order=order)
        if err is None:
            return paths, None
        loser = getattr(err, "conn", None)
        if loser is None or order[0] == loser:
            return None, err
        order = [loser] + [i for i in order if i != loser]
    rng = random.Random(seed)
    base = sorted(range(len(layout.conns)), key=lambda i: -layout.conns[i].length)
    for _ in range(restarts):
        # A greedy router's whole outcome is its net ORDER, and the orders
        # that work are not the ones that look sensible: shuffling is a
        # cheaper search over that space than any ranking heuristic.
        rng.shuffle(base)
        paths, err = route(layout, place, margin=margin, order=list(base))
        if err is None:
            return paths, None
    return None, err


def _blame(layout: Layout, place: Placement, cells, reach: int = 3) -> set[int]:
    """Which rooms are squeezing the cells the router could not share?"""
    guilty = set()
    for room in layout.rooms:
        top, left = place.tops[room.index], place.lefts[room.index]
        for r, c in cells:
            if (top - reach <= r <= top + room.height - 1 + reach
                    and left - reach <= c <= left + room.width - 1 + reach):
                guilty.add(room.index)
    return guilty


def place_route_repair(layout: Layout, *, seconds: float = 25.0,
                       channel: int = 1, rounds: int = 8, restarts: int = 60):
    """Place, route, and on congestion widen only the rooms that caused it.

    Measured on plotter_05: a uniform channel and even a 20-cell frame
    margin left the SAME twelve cells contested, because the shortage was
    one corridor rather than global space. So the loop reads the router's
    contested cells back into the placer as per-room clearance and
    re-places. Returns (place, paths, log).
    """
    from .layout_solve import solve
    pads: dict[int, int] = {}
    log = []
    for _ in range(rounds):
        # The frame has to grow with the padding or the model goes
        # infeasible for a reason that looks like "unplaceable".
        place = solve(layout, seconds=seconds, channel=channel, pads=pads,
                      slack=6 + channel + sum(pads.values()))
        if place is None:
            log.append((dict(pads), "no placement"))
            return None, None, log
        paths, err = route_with_ripup(layout, place, tries=6, restarts=restarts)
        if err is not None:
            paths, err = route_negotiated(layout, place)
        box = max(place.width, place.height, place.frame)
        if err is None:
            log.append((dict(pads), f"routed at {box}"))
            return place, paths, log
        log.append((dict(pads), f"{box}: {err}"))
        if "hard obstacles" in err:
            # Nothing to negotiate: some pipe has no legal path at all, so
            # the through-corridors themselves are too narrow. That is the
            # one failure a UNIFORM widening is the right answer to.
            channel += 1
            continue
        blamed = _blame(layout, place, getattr(err, "cells", ()) or ())
        if not blamed:
            channel += 1              # congestion nowhere near a room
            continue
        for index in blamed:
            pads[index] = pads.get(index, 0) + 1
    return None, None, log


def search_place_and_route(layout: Layout, *, seeds=range(16),
                           channels=(3, 2, 4), seconds: float = 25.0,
                           iterations: int = 60, margin: int = 0,
                           report=None):
    """Walk the family of equal-diameter placements until one ROUTES.

    Negotiation's residue on plotter_05 was eight cells, every one of them
    two pipes crossing at right angles in open space, and margins of 10, 20
    and 40 left the count at eight. A crossing is a property of the cyclic
    order the endpoints sit in, not of how much room the router has, so the
    only lever left is the placement -- specifically which wall each port
    ends up on. `layout_solve.solve(seed=...)` re-weights phase B to walk
    that family; this loop routes each member and keeps the first that is
    conflict-free. Returns (place, paths, attempts).
    """
    from .layout_solve import solve
    attempts = []
    for seed in seeds:
        for channel in channels:
            place = solve(layout, seconds=seconds, channel=channel, seed=seed)
            if place is None:
                attempts.append((seed, channel, 0, "no placement"))
                continue
            box = max(place.width, place.height, place.frame)
            paths, err = route_with_ripup(layout, place, tries=4, margin=margin)
            if err is not None:
                paths, err = route_negotiated(layout, place, margin=margin,
                                              iterations=iterations, seed=seed)
            attempts.append((seed, channel, box, "ROUTED" if err is None
                             else str(err)))
            if report is not None:
                report(attempts[-1])
            if err is None:
                return place, paths, attempts
    return None, None, attempts


def place_and_route(layout: Layout, *, seconds: float = 25.0,
                    channels=(1, 2, 3, 4)):
    """Escalate the inter-room channel until the pipes actually route.

    Placement and routing are co-dependent: the tightest box is often
    unroutable because a pipe passing between two rooms it does not
    terminate at may not touch either (the grazing rule), which needs a
    3-cell gap. Rather than model channels exactly, try increasing gaps
    and keep the first that routes -- the box grows monotonically, so the
    first success is the best of the family.
    """
    from .layout_solve import solve
    attempts = []
    for channel in channels:
        place = solve(layout, seconds=seconds, channel=channel)
        if place is None:
            attempts.append((channel, "no placement"))
            continue
        paths, err = route_with_ripup(layout, place)
        if err is not None:
            paths, err = route_negotiated(layout, place)
        if err is None:
            return place, paths, attempts
        attempts.append((channel, f"{place.width}x{place.height}: {err}"))
    return None, None, attempts
