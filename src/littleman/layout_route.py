"""Route pipes for a solver placement, then re-emit the artifact.

BFS per connection over the free grid, obstacles being room cells, cells
adjacent to a NON-endpoint room, and cells already used by another pipe.

The adjacency obstacle is the expensive lesson: the server treats a pipe
merely GRAZING a room's wall as connected to that room. That cost us a
submission (reverse_03 was rejected 0/0 because an 18-cell return pipe
ran flush past the input room's wall) and later killed a tcp variant that
passed 6/6 locally. A router that only avoids overlap will keep
reproducing it, so adjacency is a hard obstacle here.

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
                     margin: int = 0, growth: float = 1.22,
                     history_step: float = 0.7):
    """PathFinder: route everything, then negotiate the shared cells away.

    A greedy router loses whenever an early pipe takes the only lane a
    later one needed, and reordering only shuffles who loses. Negotiated
    congestion lets every pipe take its best path, then charges a rising
    price for cells more than one pipe wants until the contested lanes
    sort themselves out. Hard obstacles stay hard: a cell inside a room,
    or flush against a room this pipe does not terminate at, is never for
    sale -- that is the server's grazing rule, not a preference.
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
    for start, first, goal, ends, _away in nets:
        blocked = set(owned) | reserved | _forbidden_flanks(layout, owned, ends)
        blocked.discard(goal)
        blocked.add(start)
        blocked_for.append(blocked)
    history: dict = {}
    occupancy: dict = {}
    penalty = 0.5
    paths = None
    order = sorted(range(len(nets)), key=lambda i: -layout.conns[i].length)
    # Where a net went last time, slightly discounted. Without this the
    # shared-cell count oscillates (16-14-12-21-9-13 on tcp) because every
    # net re-plans from scratch against a field that just changed.
    settled_in: dict = {}
    for _ in range(iterations):
        occupancy = {}
        paths = []
        for ci in order:
            start, first, goal, ends, away = nets[ci]
            keep = settled_in.get(ci, frozenset())

            def cell_cost(cell, _h=history, _o=occupancy, _k=keep):
                over = _o.get(cell, 0)
                base = (1.0 + _h.get(cell, 0.0)) * (1.0 + penalty * over)
                return base * 0.9 if cell in _k else base
            path = _shortest(first, away, goal, blocked_for[ci], cell_cost,
                             hi, owned)
            if path is None:
                return None, RouteError(ci, "no route at all (hard obstacles)",
                                        cells=(start, goal))
            path = [start] + path
            for cell in path[1:]:
                occupancy[cell] = occupancy.get(cell, 0) + 1
            settled_in[ci] = frozenset(path)
            paths.append((ci, path))
        paths.sort()
        shared = [cell for cell, n in occupancy.items() if n > 1]
        if shared:
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
            for ci, path in paths:
                if layout.conns[ci].exact and len(path) != layout.conns[ci].length:
                    return None, RouteError(
                        ci, f"timing-exact needs {layout.conns[ci].length}, "
                            f"routed {len(path)}")
                if len(path) < 2:
                    return None, RouteError(ci, "degenerate path")
            bad = _violations(layout, place, paths)
            if bad:
                return None, RouteError(bad[0][0], bad[0][1])
            return paths, None
        for cell in shared:
            history[cell] = history.get(cell, 0.0) + history_step * (
                occupancy[cell] - 1)
        penalty = min(penalty * growth, 64.0)
    contested = [cell for cell, n in occupancy.items() if n > 1]
    worst = max(occupancy.items(), key=lambda kv: kv[1])
    return None, RouteError(
        paths[0][0],
        f"{len(contested)} cells still shared, worst {worst[1]} pipes at "
        f"{worst[0]}", cells=contested)


def _settle(layout, nets, blocked_for, paths, occupancy, hi, owned,
            orders: int = 12):
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
