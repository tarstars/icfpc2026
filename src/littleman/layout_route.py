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

from collections import deque

from .canvas import Canvas
from .layout_ir import Layout
from .layout_solve import Placement, _port_cell


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


def route(layout: Layout, place: Placement, *, margin: int = 40):
    """Route every connection. Returns (paths, None) or (None, reason)."""
    owned = _room_cells(layout, place)
    used: set[tuple[int, int]] = set()
    paths = []
    lo_r = min(place.tops) - margin
    hi_r = max(place.tops[i] + r.height for i, r in enumerate(layout.rooms)) + margin
    lo_c = min(place.lefts) - margin
    hi_c = max(place.lefts[i] + r.width for i, r in enumerate(layout.rooms)) + margin

    # Longest first: the constrained routes get the free grid.
    order = sorted(range(len(layout.conns)),
                   key=lambda i: -layout.conns[i].length)
    for ci in order:
        conn = layout.conns[ci]
        src_room, dst_room = conn.src.room, conn.dst.room
        start = _port_cell(place.tops[src_room], place.lefts[src_room],
                           layout.rooms[src_room], conn.src)
        goal = _port_cell(place.tops[dst_room], place.lefts[dst_room],
                          layout.rooms[dst_room], conn.dst)
        endpoints = {src_room, dst_room}

        def passable(cell, is_end=False):
            if cell in owned or cell in used:
                return False
            r, c = cell
            if not (lo_r <= r <= hi_r and lo_c <= c <= hi_c):
                return False
            touching = _adjacent_rooms(cell, owned)
            return touching <= endpoints if not is_end else True

        if start in owned or goal in owned:
            return None, f"conn {ci}: port cell inside a room"
        # The first cell must point AWAY from its wall (a server rule), so
        # force the first step in that direction.
        away = _AWAY[conn.src.side]
        first = (start[0] + away[0], start[1] + away[1])
        if first != goal and not passable(first):
            return None, f"conn {ci}: cannot leave source wall"
        prev: dict = {start: None, first: start}
        queue = deque([first])
        found = False
        while queue:
            cur = queue.popleft()
            if cur == goal:
                found = True
                break
            r, c = cur
            for nb in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                if nb in prev:
                    continue
                if nb != goal and not passable(nb):
                    continue
                if nb == goal and (nb in owned or nb in used):
                    continue
                prev[nb] = cur
                queue.append(nb)
        if not found:
            return None, f"conn {ci}: no route ({start} -> {goal})"
        path = []
        cur = goal
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        path.reverse()
        if len(path) < 2:
            return None, f"conn {ci}: degenerate path"
        if conn.exact and len(path) != conn.length:
            return None, (f"conn {ci}: timing-exact needs {conn.length}, "
                          f"routed {len(path)}")
        used.update(path)
        paths.append((ci, path))
    paths.sort()
    return paths, None


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
        conn = layout.conns[ci]
        for cell, glyph in zip(path, glyphs_for(path, conn.src.side,
                                                conn.dst.side)):
            canvas.cells[cell] = glyph
    return canvas.render()


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
        paths, err = route(layout, place)
        if err is None:
            return place, paths, attempts
        attempts.append((channel, f"{place.width}x{place.height}: {err}"))
    return None, None, attempts
