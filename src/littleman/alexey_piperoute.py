"""Route a pipe between two rooms through the free cells of a program.

Re-routing by hand is where the deadlocks come from. Three constraints have
to hold at once and it is easy to satisfy two of them:

1. **Length is buffer capacity.** A pipe holds one value per cell. Shorten
   it below what the protocol needs and the machine deadlocks with no other
   symptom -- it just stops. So a re-route must be able to hit a *target
   length*, not merely connect two points.
2. **Clearance.** A pipe cell whose backward neighbour is a room wall makes
   the parser start a new pipe there, so a route must stay one cell clear of
   every foreign room; only the two endpoints may touch a wall.
3. **Glyphs.** Straight runs must be drawn with `-` and `|`, arrowheads only
   at turns and at the two ends, or `alexey_squeeze` is blinded and stops
   finding deletable rows and columns.

`route()` handles all three: a BFS shortest path, then inflated to the
target length with two-cell bumps (a detour of exactly +2 keeps the parity
that grid paths are stuck with anyway), then rendered.

    from littleman.alexey_piperoute import Router
    rt = Router(text)
    rt.erase(old_pipe_cells)                    # free the old route first
    cells = rt.route(start, end, into=(0,-1), target=28)
    text  = rt.apply(cells, into=(0,-1))

`start` must be adjacent to the source room, `end` adjacent to the target
room, and `into` is the unit vector from `end` into the target room's wall
-- that is what the terminal arrowhead points along.
"""

from collections import deque

from .sim import Machine

DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))
ARROW = {(-1, 0): "^", (1, 0): "v", (0, -1): "<", (0, 1): ">"}
RUN = {(-1, 0): "|", (1, 0): "|", (0, -1): "-", (0, 1): "-"}


class RouteError(Exception):
    pass


class Router:
    def __init__(self, text: str, extra_blocked=()):
        lines = text.rstrip("\n").split("\n")
        self.w = max(len(line) for line in lines)
        self.grid = [list(line.ljust(self.w)) for line in lines]
        self.h = len(self.grid)
        machine = Machine.parse(text)
        self.rooms = machine.rooms
        self.machine = machine
        self.blocked = set(extra_blocked)
        self._near = None

    # -- geometry -----------------------------------------------------
    def _wall_cells(self):
        cells = set()
        for r in self.rooms:
            for y in range(r.top, r.bottom + 1):
                for x in range(r.left, r.right + 1):
                    if y in (r.top, r.bottom) or x in (r.left, r.right):
                        cells.add((y, x))
        return cells

    def _room_cells(self):
        cells = set()
        for r in self.rooms:
            for y in range(r.top, r.bottom + 1):
                for x in range(r.left, r.right + 1):
                    cells.add((y, x))
        return cells

    def erase(self, cells):
        for y, x in cells:
            self.grid[y][x] = " "

    def near_rooms(self):
        """Cells orthogonally touching a room. A pipe may *pass* through
        these -- long runs along a room wall are normal and several live
        programs do it -- but it may not carry an ARROW there. An arrow
        pointing away from the room makes the parser start a spurious pipe
        at that cell; an arrow pointing into it ends the pipe early. Only
        `-` and `|` are safe against a wall."""
        if self._near is None:
            self._near = set()
            for y, x in self._room_cells():
                for dy, dx in DIRS:
                    self._near.add((y + dy, x + dx))
        return self._near

    def free(self, endpoints=(), strict=False):
        """Cells a pipe may pass through. `strict` also excludes every cell
        touching a room, which is the conservative choice when there is
        plenty of room; the endpoints are always exempt."""
        rooms = self._room_cells()
        near = self.near_rooms()
        ok = set()
        for y in range(self.h):
            for x in range(self.w):
                if self.grid[y][x] != " " or (y, x) in self.blocked:
                    continue
                if (y, x) in rooms:
                    continue
                if strict and (y, x) in near and (y, x) not in endpoints:
                    continue
                ok.add((y, x))
        return ok

    def route_via(self, points, into, target=None, bounds=None, out=None):
        """Route through waypoints, then inflate the whole thing.

        Inflation only thickens a path where it already runs, so a shortest
        path that never enters the big empty region cannot be grown into it
        and `_inflate` dies with cells to spare elsewhere on the canvas. A
        waypoint dropped in the middle of that region fixes it: the path goes
        there, and the bumps then have somewhere to go."""
        legs = []
        reserved = set()
        for i in range(len(points) - 1):
            self.blocked.update(reserved - {points[i], points[i + 1]})
            leg = self.route(points[i], points[i + 1], into, None, bounds,
                             out if i == 0 else None)
            self.blocked.difference_update(reserved)
            legs.append(leg if i == 0 else leg[1:])
            reserved.update(leg)
        path = [c for leg in legs for c in leg]
        if len(set(path)) != len(path):
            raise RouteError("waypoint legs overlap")
        if target and len(path) < target:
            ok = self.free({points[0], points[-1]})
            if bounds:
                ok = {(y, x) for (y, x) in ok if y <= bounds[0] and x <= bounds[1]}
            path = self._inflate(path, target, ok | set(path))
        return path

    def route_safe(self, start, end, into, target=None, bounds=None, out=None,
                   attempts=200):
        """`route`, then forbid any turn that landed against a room wall and
        try again. Converges because each pass permanently blocks at least
        one cell."""
        for _ in range(attempts):
            cells = self.route(start, end, into, target, bounds, out)
            marks = self.glyphs(cells, into)
            bad = [c for c in cells[1:-1]
                   if c in self.near_rooms() and marks[c] in "<>^v"]
            if not bad:
                return cells
            self.blocked.update(bad)
        raise RouteError("could not keep arrowheads off the walls")

    # -- routing ------------------------------------------------------
    def route(self, start, end, into, target=None, bounds=None, out=None):
        """A cell list from `start` to `end` of length >= target.

        `out` forces the first step's direction. Give it whenever the start
        cell sits against a wall: the parser only recognises a pipe when the
        cell touching the room carries an arrow pointing *away* from it, so a
        route that happens to leave sideways is silently not a pipe at all.
        That is worth an explicit argument -- the machine then loads, runs,
        and fails, with a pipe count one short as the only clue.

        `bounds` is an optional (max_row, max_col) the route must respect --
        use it to stop a re-route from re-inflating the bounding box.
        """
        if out is not None:
            head = (start[0] + out[0], start[1] + out[1])
            self.blocked.add(start)
            try:
                tail = self.route(head, end, into, target and target - 1, bounds)
            finally:
                self.blocked.discard(start)
            return [start] + tail
        endpoints = {start, end}
        ok = self.free(endpoints)
        if bounds:
            mr, mc = bounds
            ok = {(y, x) for (y, x) in ok if y <= mr and x <= mc}
        ok |= endpoints
        if start not in ok or end not in ok:
            raise RouteError(f"endpoint not free: {start} {end}")

        prev = {start: None}
        q = deque([start])
        while q:
            cur = q.popleft()
            if cur == end:
                break
            for dy, dx in DIRS:
                nxt = (cur[0] + dy, cur[1] + dx)
                if nxt in ok and nxt not in prev:
                    prev[nxt] = cur
                    q.append(nxt)
        if end not in prev:
            raise RouteError(f"no route {start} -> {end}")
        path = []
        cur = end
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        path.reverse()

        if target and len(path) < target:
            path = self._inflate(path, target, ok)
        return path

    def _inflate(self, path, target, ok):
        """Grow the path to `target` cells with +2 detours.

        Replacing one step a->b with a->x->y->b adds exactly two cells, which
        preserves the parity every grid path between two fixed cells is stuck
        with, so the target is reachable whenever its parity matches."""
        used = set(path)
        guard = 0
        while len(path) < target and guard < 10000:
            guard += 1
            grew = False
            # Never bump the first or last step. The first one carries the
            # arrow that makes the parser recognise the pipe at all, and the
            # last one the arrow that points into the destination room; a
            # detour inserted there silently turns the pipe into scenery.
            for i in range(1, len(path) - 2):
                a, b = path[i], path[i + 1]
                step = (b[0] - a[0], b[1] - a[1])
                sides = ((0, 1), (0, -1)) if step[0] else ((1, 0), (-1, 0))
                for sy, sx in sides:
                    x1 = (a[0] + sy, a[1] + sx)
                    x2 = (b[0] + sy, b[1] + sx)
                    if x1 in ok and x2 in ok and x1 not in used and x2 not in used:
                        path[i + 1 : i + 1] = [x1, x2]
                        used.add(x1)
                        used.add(x2)
                        grew = True
                        break
                if grew:
                    break
            if not grew:
                raise RouteError(f"cannot inflate past {len(path)} (target {target})")
        return path

    # -- rendering ----------------------------------------------------
    def glyphs(self, cells, into):
        """Map each cell to its character: arrowheads at the start, at every
        turn and at the terminal cell; `-`/`|` along straight runs."""
        out = {}
        steps = [(cells[i + 1][0] - cells[i][0], cells[i + 1][1] - cells[i][1])
                 for i in range(len(cells) - 1)]
        steps.append(into)
        prev = None
        for cell, step in zip(cells, steps):
            if step not in ARROW:
                raise RouteError(f"non-unit step {step} at {cell}")
            out[cell] = ARROW[step] if (prev is None or step != prev) else RUN[step]
            prev = step
        out[cells[-1]] = ARROW[into]
        return out

    def apply(self, cells, into):
        for cell, ch in self.glyphs(cells, into).items():
            y, x = cell
            if self.grid[y][x] != " ":
                raise RouteError(f"collision at {cell}: {self.grid[y][x]!r}")
            self.grid[y][x] = ch
        return self.text()

    def text(self):
        return "\n".join("".join(row).rstrip() for row in self.grid) + "\n"
