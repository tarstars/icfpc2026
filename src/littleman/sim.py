"""Littleman machine simulator.

Implements the semantics of docs/language-reference.md. Tick order:
pipes shift -> I/O -> execute -> movement.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field

MASK64 = (1 << 64) - 1


def wrap64(v: int) -> int:
    v &= MASK64
    return v - (1 << 64) if v >= (1 << 63) else v


UP, DOWN, LEFT, RIGHT = (-1, 0), (1, 0), (0, -1), (0, 1)
CLOCKWISE = {UP: RIGHT, RIGHT: DOWN, DOWN: LEFT, LEFT: UP}
COUNTERCW = {v: k for k, v in CLOCKWISE.items()}
ARROWS = {">": RIGHT, "<": LEFT, "^": UP, "v": DOWN}


class LoadError(Exception):
    pass


@dataclass
class Room:
    top: int
    left: int
    bottom: int  # inclusive border rows/cols
    right: int
    kind: str = "room"  # room | input | output | display
    # display state (kind == "display" only)
    disp_w: int = 0
    disp_h: int = 0
    cursor: int = 0
    current: list = None
    next: list = None

    def init_display(self):
        self.disp_w = self.right - self.left - 1
        self.disp_h = self.bottom - self.top - 1
        self.current = [[0] * self.disp_w for _ in range(self.disp_h)]
        self.next = [[0] * self.disp_w for _ in range(self.disp_h)]
        self.cursor = 0

    def interior(self):
        return range(self.top + 1, self.bottom), range(self.left + 1, self.right)

    def contains_interior(self, r, c):
        return self.top < r < self.bottom and self.left < c < self.right

    def contains(self, r, c):
        return self.top <= r <= self.bottom and self.left <= c <= self.right

    def on_border(self, r, c):
        on_edge = r in (self.top, self.bottom) or c in (self.left, self.right)
        return self.contains(r, c) and on_edge


@dataclass
class Pipe:
    cells: list  # [(r, c)] from source end to destination end
    source: Room
    dest: Room
    values: list = None
    side: str | None = None  # display pipes: addr | data | swap
    runs: list[list[int]] = field(default_factory=list)
    value_count: int = 0

    def __post_init__(self):
        if self.values is None:
            self.values = [None] * len(self.cells)
        self.runs = []
        for index, value in enumerate(self.values):
            if value is None:
                continue
            if self.runs and self.runs[-1][1] + 1 == index:
                self.runs[-1][1] = index
            else:
                self.runs.append([index, index])
        self.value_count = sum(end - start + 1 for start, end in self.runs)

    def put(self, index: int, value: int):
        index %= len(self.values)
        was_empty = self.values[index] is None
        self.values[index] = value
        if not was_empty:
            return
        self.value_count += 1
        for run_index, (start, end) in enumerate(self.runs):
            if index < start - 1:
                self.runs.insert(run_index, [index, index])
                return
            if index == start - 1:
                self.runs[run_index][0] = index
                return
            if index == end + 1:
                self.runs[run_index][1] = index
                if (
                    run_index + 1 < len(self.runs)
                    and index + 1 == self.runs[run_index + 1][0]
                ):
                    self.runs[run_index][1] = self.runs[run_index + 1][1]
                    self.runs.pop(run_index + 1)
                return
        self.runs.append([index, index])

    def take(self, index: int):
        index %= len(self.values)
        value = self.values[index]
        self.values[index] = None
        if value is None:
            return None
        self.value_count -= 1
        for run_index, (start, end) in enumerate(self.runs):
            if not start <= index <= end:
                continue
            if start == end:
                self.runs.pop(run_index)
            elif index == start:
                self.runs[run_index][0] += 1
            elif index == end:
                self.runs[run_index][1] -= 1
            else:
                self.runs[run_index : run_index + 1] = [
                    [start, index - 1],
                    [index + 1, end],
                ]
            break
        return value

    def shift(self):
        if not self.runs:
            return
        blocked_suffix = self.runs[-1][1] == len(self.values) - 1
        moving_count = len(self.runs) - int(blocked_suffix)
        for run_index in range(moving_count):
            start, end = self.runs[run_index]
            self.values[start + 1 : end + 2] = self.values[start : end + 1]
            self.values[start] = None
            self.runs[run_index] = [start + 1, end + 1]
        if blocked_suffix and moving_count:
            moving = self.runs[moving_count - 1]
            blocked = self.runs[moving_count]
            if moving[1] + 1 == blocked[0]:
                moving[1] = blocked[1]
                self.runs.pop(moving_count)

    @property
    def count(self):
        return self.value_count


@dataclass
class Man:
    r: int
    c: int
    room: Room
    direction: tuple = RIGHT
    A: int = 0
    B: int = 0
    BP: int = 0
    halted: bool = False
    blocked: bool = False
    wait_kind: str | None = None
    wait_pipes: tuple = ()
    # Stepped into a wall. The official engine lets the man ENTER the
    # wall cell and fires the fatal on the NEXT tick, after that tick's
    # pipe-shift and output-emit phases -- exactly one grace tick. See
    # docs/language-reference-updates-2026-07-27.md.
    crashed: bool = False


@dataclass
class RunResult:
    status: str  # halted | error | tick-cap
    error: str | None = None
    output: list = field(default_factory=list)
    output_ticks: list = field(default_factory=list)
    frames: list = field(default_factory=list)
    frame_ticks: list = field(default_factory=list)
    ticks: int = 0


class Machine:
    def __init__(self, grid, rooms, men, pipes):
        self.grid = grid
        self.rooms = rooms
        self.men = men
        self.pipes = pipes
        self.out_pipes = {}  # room id -> [pipes], sorted later
        self.in_pipes = {}
        self._nearest_outgoing_cache = {}
        self._nearest_incoming_cache = {}
        for p in pipes:
            self.out_pipes.setdefault(id(p.source), []).append(p)
            self.in_pipes.setdefault(id(p.dest), []).append(p)
        self.input_pipe = next((p for p in pipes if p.source.kind == "input"), None)
        self.output_pipe = next((p for p in pipes if p.dest.kind == "output"), None)
        self.displays = [r for r in rooms if r.kind == "display"]
        self._pipe_by_id = {id(pipe): pipe for pipe in pipes}
        self._active_pipes = {
            id(pipe): pipe for pipe in pipes if self._pipe_can_shift(pipe)
        }
        self._man_indices = {id(man): index for index, man in enumerate(men)}
        self._runnable_men = set(range(len(men)))
        self._receive_waiters: dict[int, set[int]] = {}
        self._send_waiters: dict[int, set[int]] = {}
        self._tick_heap = None
        self._tick_processed: set[int] = set()
        self._tick_current_index = -1
        self._occupied = {(man.r, man.c): man for man in men}

    # ------------------------------------------------------------- parsing
    @classmethod
    def parse(cls, text: str) -> Machine:
        lines = text.split("\n")
        while lines and lines[-1] == "":
            lines.pop()
        width = max((len(l) for l in lines), default=0)
        grid = [list(l.ljust(width)) for l in lines]

        rooms = cls._find_rooms(grid)
        men = []
        for room in rooms:
            rrange, crange = room.interior()
            for r in rrange:
                for c in crange:
                    if grid[r][c] == "@":
                        men.append(Man(r, c, room))
        men.sort(key=lambda m: (m.r, m.c))
        pipes = cls._find_pipes(grid, rooms)
        machine = cls(grid, rooms, men, pipes)
        machine._build_literals()
        return machine

    @staticmethod
    def _find_rooms(grid):
        h = len(grid)
        w = len(grid[0]) if h else 0
        candidates = []
        for r in range(h):
            for c in range(w):
                if grid[r][c] != "+":
                    continue
                c2 = c + 1
                while c2 < w and grid[r][c2] == "-":
                    c2 += 1
                if c2 >= w or grid[r][c2] != "+" or c2 == c + 1:
                    continue
                r2 = r + 1
                while r2 < h and grid[r2][c] == "|":
                    r2 += 1
                if r2 >= h or grid[r2][c] != "+" or r2 == r + 1:
                    continue
                if grid[r2][c2] != "+":
                    continue
                if not all(grid[r2][cc] == "-" for cc in range(c + 1, c2)):
                    continue
                if not all(grid[rr][c2] == "|" for rr in range(r + 1, r2)):
                    continue
                candidates.append(Room(r, c, r2, c2))
        # displays: + corners, = horizontal walls, : vertical walls
        for r in range(h):
            for c in range(w):
                if grid[r][c] != "+":
                    continue
                c2 = c + 1
                while c2 < w and grid[r][c2] == "=":
                    c2 += 1
                if c2 >= w or grid[r][c2] != "+" or c2 == c + 1:
                    continue
                r2 = r + 1
                while r2 < h and grid[r2][c] == ":":
                    r2 += 1
                if r2 >= h or grid[r2][c] != "+" or r2 == r + 1:
                    continue
                if grid[r2][c2] != "+":
                    continue
                if not all(grid[r2][cc] == "=" for cc in range(c + 1, c2)):
                    continue
                if not all(grid[rr][c2] == ":" for rr in range(r + 1, r2)):
                    continue
                disp = Room(r, c, r2, c2, kind="display")
                disp.init_display()
                candidates.append(disp)
        rooms = []
        for a in candidates:
            nested = any(
                b is not a
                and b.top <= a.top
                and b.left <= a.left
                and b.bottom >= a.bottom
                and b.right >= a.right
                for b in candidates
            )
            if not nested:
                rooms.append(a)
        for room in rooms:
            rr, cr = room.interior()
            if len(rr) == 1 and len(cr) == 1:
                ch = grid[rr[0]][cr[0]]
                if ch == "I":
                    room.kind = "input"
                elif ch == "O":
                    room.kind = "output"
        return rooms

    @classmethod
    def _find_pipes(cls, grid, rooms):
        h, w = len(grid), len(grid[0]) if grid else 0
        used = set()
        pipes = []

        def room_at(r, c):
            for room in rooms:
                if room.contains(r, c):
                    return room
            return None

        def border_room(r, c):
            for room in rooms:
                if room.on_border(r, c):
                    return room
            return None

        for room in rooms:
            starts = []
            for r in range(room.top, room.bottom + 1):
                for c in (
                    range(room.left, room.right + 1)
                    if r in (room.top, room.bottom)
                    else (room.left, room.right)
                ):
                    for d in (UP, DOWN, LEFT, RIGHT):
                        gr, gc = r + d[0], c + d[1]
                        if not (0 <= gr < h and 0 <= gc < w):
                            continue
                        if room.contains(gr, gc):
                            continue
                        if (gr, gc) in used:
                            continue
                        if ARROWS.get(grid[gr][gc]) == d:
                            starts.append((gr, gc, d))
            for gr, gc, d in starts:
                if (gr, gc) in used:
                    continue
                pipe = cls._trace_pipe(grid, rooms, room, gr, gc, d, border_room)
                if pipe:
                    for cell in pipe.cells:
                        used.add(cell)
                    pipes.append(pipe)
        return pipes

    @staticmethod
    def _trace_pipe(grid, rooms, source, r, c, d, border_room):
        h, w = len(grid), len(grid[0])
        cells = [(r, c)]
        while True:
            ch = grid[r][c]
            if ch in ARROWS:
                nd = ARROWS[ch]
                if len(cells) > 1 and nd == (-d[0], -d[1]):
                    raise LoadError(f"pipe reverses at {(r, c)}")
                d = nd
                fr, fc = r + d[0], c + d[1]
                if 0 <= fr < h and 0 <= fc < w:
                    target = border_room(fr, fc)
                    if target is not None and target is not source:
                        pipe = Pipe(cells=cells, source=source, dest=target)
                        if target.kind == "display":
                            on_top = fr == target.top
                            on_bottom = fr == target.bottom
                            on_left = fc == target.left
                            corner = (on_top or on_bottom) and (
                                fc in (target.left, target.right)
                            )
                            if corner or fc == target.right and not corner:
                                raise LoadError(f"bad display attach at {(fr, fc)}")
                            if on_top:
                                pipe.side = "addr"
                            elif on_bottom:
                                pipe.side = "swap"
                            elif on_left:
                                pipe.side = "data"
                            else:
                                raise LoadError(f"bad display attach at {(fr, fc)}")
                        return pipe
            # advance
            r, c = r + d[0], c + d[1]
            if not (0 <= r < h and 0 <= c < w):
                raise LoadError("pipe runs off grid")
            ch = grid[r][c]
            expected_body = "-" if d in (LEFT, RIGHT) else "|"
            if ch in ARROWS or ch == expected_body:
                cells.append((r, c))
            else:
                raise LoadError(f"bad pipe glyph {ch!r} at {(r, c)}")

    # ------------------------------------------------------------ literals
    def _build_literals(self):
        """Pair backticks per axis inside each room; record spans and digits.

        A backtick may pair horizontally, vertically, or both (corner
        backticks). One left unpaired on both axes is a load error.
        """
        self.hpairs = {}  # (r, c) -> (c1, c2) span on row r
        self.vpairs = {}  # (r, c) -> (r1, r2) span on col c
        self.hdigits = set()
        self.vdigits = set()
        ticks = []
        for room in self.rooms:
            rrange, crange = room.interior()
            for r in rrange:
                for c in crange:
                    if self.grid[r][c] == "`":
                        ticks.append((r, c))
            # horizontal pairing per row
            for r in rrange:
                cols = [c for c in crange if self.grid[r][c] == "`"]
                for i in range(0, len(cols) - 1, 2):
                    a, b = cols[i], cols[i + 1]
                    between = [self.grid[r][c] for c in range(a + 1, b)]
                    if not all(ch.isdigit() or ch == " " for ch in between):
                        raise LoadError(f"invalid horizontal literal at {(r, a)}")
                    self._register_literal(between, (r, a), (r, b), "h")
                    for c in range(a + 1, b):
                        if self.grid[r][c].isdigit():
                            self.hdigits.add((r, c))
            # vertical pairing per column
            for c in crange:
                rows = [r for r in rrange if self.grid[r][c] == "`"]
                for i in range(0, len(rows) - 1, 2):
                    a, b = rows[i], rows[i + 1]
                    between = [self.grid[r][c] for r in range(a + 1, b)]
                    if not all(ch.isdigit() or ch == " " for ch in between):
                        raise LoadError(f"invalid vertical literal at {(a, c)}")
                    self._register_literal(between, (a, c), (b, c), "v")
                    for r in range(a + 1, b):
                        if self.grid[r][c].isdigit():
                            self.vdigits.add((r, c))
        for pos in ticks:
            if pos not in self.hpairs and pos not in self.vpairs:
                raise LoadError(f"unmatched backtick at {pos}")

    def _register_literal(self, between, start, end, axis):
        digits = "".join(ch for ch in between if ch.isdigit())
        if digits:
            fwd, rev = int(digits), int(digits[::-1])
            if fwd >= (1 << 63) or rev >= (1 << 63):
                raise LoadError(f"literal too large at {start}")
        if axis == "h":
            span = (start[1], end[1])
            self.hpairs[start] = span
            self.hpairs[end] = span
        else:
            span = (start[0], end[0])
            self.vpairs[start] = span
            self.vpairs[end] = span

    def _literal_load(self, man):
        """Return value to load if man is on a closing backtick, else None."""
        r, c = man.r, man.c
        horizontal = man.direction in (LEFT, RIGHT)
        if horizontal and (r, c) in self.hpairs:
            a, b = self.hpairs[(r, c)]
            if man.direction == RIGHT and c == b:
                cells = [self.grid[r][x] for x in range(a + 1, b)]
            elif man.direction == LEFT and c == a:
                cells = [self.grid[r][x] for x in range(b - 1, a, -1)]
            else:
                return None
        elif not horizontal and (r, c) in self.vpairs:
            a, b = self.vpairs[(r, c)]
            if man.direction == DOWN and r == b:
                cells = [self.grid[x][c] for x in range(a + 1, b)]
            elif man.direction == UP and r == a:
                cells = [self.grid[x][c] for x in range(b - 1, a, -1)]
            else:
                return None
        else:
            return None
        digits = "".join(ch for ch in cells if ch.isdigit())
        return int(digits) if digits else None

    # ---------------------------------------------------------- scheduling
    @staticmethod
    def _pipe_can_shift(pipe: Pipe) -> bool:
        if not pipe.runs:
            return False
        return len(pipe.runs) > 1 or pipe.runs[-1][1] != len(pipe.values) - 1

    def _clear_wait(self, index: int) -> None:
        man = self.men[index]
        waiter_map = (
            self._receive_waiters
            if man.wait_kind in {"r", "RU"}
            else self._send_waiters
        )
        for pipe_id in man.wait_pipes:
            waiters = waiter_map.get(pipe_id)
            if waiters is None:
                continue
            waiters.discard(index)
            if not waiters:
                waiter_map.pop(pipe_id, None)
        man.wait_kind = None
        man.wait_pipes = ()

    def _schedule_man(self, index: int) -> None:
        man = self.men[index]
        if man.halted:
            return
        self._clear_wait(index)
        man.blocked = False
        if (
            self._tick_heap is not None
            and index > self._tick_current_index
            and index not in self._tick_processed
        ):
            heapq.heappush(self._tick_heap, index)
        else:
            self._runnable_men.add(index)

    def _wait_condition_ready(self, man: Man) -> bool:
        pipes = [self._pipe_by_id[pipe_id] for pipe_id in man.wait_pipes]
        if man.wait_kind == "r":
            return pipes[0].values[-1] is not None
        if man.wait_kind == "RU":
            return any(pipe.values[-1] is not None for pipe in pipes)
        if man.wait_kind == "s":
            return pipes[0].values[0] is None
        if man.wait_kind == "S":
            return all(pipe.values[0] is None for pipe in pipes)
        return False

    def _maybe_wake(self, index: int) -> None:
        man = self.men[index]
        if man.wait_kind is not None and self._wait_condition_ready(man):
            self._schedule_man(index)

    def _wake_pipe_receivers(self, pipe: Pipe) -> None:
        for index in tuple(self._receive_waiters.get(id(pipe), ())):
            self._maybe_wake(index)

    def _wake_pipe_senders(self, pipe: Pipe) -> None:
        for index in tuple(self._send_waiters.get(id(pipe), ())):
            self._maybe_wake(index)

    def _register_wait(self, index: int, kind: str, pipes: list[Pipe]) -> None:
        man = self.men[index]
        man.wait_kind = kind
        man.wait_pipes = tuple(id(pipe) for pipe in pipes)
        waiter_map = (
            self._receive_waiters if kind in {"r", "RU"} else self._send_waiters
        )
        for pipe in pipes:
            waiter_map.setdefault(id(pipe), set()).add(index)

    def _pipe_put(self, pipe: Pipe, index: int, value: int) -> None:
        pipe.put(index, value)
        pipe_id = id(pipe)
        if self._pipe_can_shift(pipe):
            self._active_pipes[pipe_id] = pipe
        else:
            self._active_pipes.pop(pipe_id, None)
        if pipe.values[-1] is not None:
            self._wake_pipe_receivers(pipe)

    def _pipe_take(self, pipe: Pipe, index: int):
        value = pipe.take(index)
        pipe_id = id(pipe)
        if self._pipe_can_shift(pipe):
            self._active_pipes[pipe_id] = pipe
        else:
            self._active_pipes.pop(pipe_id, None)
        if pipe.values[0] is None:
            self._wake_pipe_senders(pipe)
        return value

    # ------------------------------------------------------------- running
    def run(
        self, inputs=None, max_ticks: int = 5_000_000, controller=None
    ) -> RunResult:
        """Run to completion.

        `controller` (optional) gates input and observes output for judging:
        it must provide pop_input() -> value | None and
        on_output(value, tick) -> None | "passed" | "failed".
        """
        self._input_queue = list(inputs or [])
        self._controller = controller
        res = RunResult(status="tick-cap")
        for _ in range(max_ticks):
            res.ticks += 1
            err = self._tick(res)
            if err:
                res.status = "error"
                res.error = err
                return res
            if self._verdict:
                res.status = self._verdict
                return res
            if (
                not self._runnable_men
                and not self._receive_waiters
                and not self._send_waiters
            ):
                if self.output_pipe and self.output_pipe.count:
                    continue  # drain output pipe
                if any(p.count for p in self.pipes if p.dest.kind == "display"):
                    continue  # displays keep consuming in-flight values
                if any(man.crashed for man in self.men):
                    # A crashed man is marked halted so it stops moving,
                    # but the program did NOT end cleanly -- and a wall
                    # fatal does not drain, unlike a real `H` halt.
                    res.status = "error"
                    res.error = "wall"
                    return res
                res.status = "halted"
                return res
        return res

    def _tick(self, res: RunResult):
        # 1. pipes shift
        for pipe in tuple(self._active_pipes.values()):
            source_was_full = pipe.values[0] is not None
            destination_was_empty = pipe.values[-1] is None
            pipe.shift()
            pipe_id = id(pipe)
            if self._pipe_can_shift(pipe):
                self._active_pipes[pipe_id] = pipe
            else:
                self._active_pipes.pop(pipe_id, None)
            if source_was_full and pipe.values[0] is None:
                self._wake_pipe_senders(pipe)
            if destination_was_empty and pipe.values[-1] is not None:
                self._wake_pipe_receivers(pipe)
        # 2. I/O: emit output, then inject input
        self._verdict = None
        if self.output_pipe and self.output_pipe.values[-1] is not None:
            value = self._pipe_take(self.output_pipe, -1)
            res.output.append(value)
            res.output_ticks.append(res.ticks)
            if self._controller:
                verdict = self._controller.on_output(value, res.ticks)
                if verdict:
                    self._verdict = verdict
                    return None
        if self.input_pipe and self.input_pipe.values[0] is None:
            if self._controller:
                value = self._controller.pop_input()
                if value is not None:
                    self._pipe_put(self.input_pipe, 0, value)
            elif self._input_queue:
                self._pipe_put(self.input_pipe, 0, self._input_queue.pop(0))
        # 3. execute
        # A crash from the previous tick ends the program here: no man
        # executes, and there is no drain-to-empty (a clean `H` halt
        # DOES drain; a wall fatal does not).
        if any(man.crashed for man in self.men):
            self._tick_heap = None
            return "wall"
        self._tick_heap = list(self._runnable_men)
        heapq.heapify(self._tick_heap)
        self._runnable_men = set()
        self._tick_processed = set()
        movers = []
        while self._tick_heap:
            index = heapq.heappop(self._tick_heap)
            if index in self._tick_processed:
                continue
            self._tick_processed.add(index)
            self._tick_current_index = index
            man = self.men[index]
            if man.halted:
                continue
            man.blocked = False
            err = self._execute(man)
            if err:
                self._tick_heap = None
                return err
            if man.blocked:
                instruction = self.grid[man.r][man.c]
                if instruction == "r":
                    pipes = [self._nearest_incoming(man)]
                    kind = "r"
                elif instruction in "RU":
                    pipes = self._incoming(man)
                    kind = "RU"
                elif instruction == "s":
                    pipes = [self._nearest_outgoing(man)]
                    kind = "s"
                else:
                    pipes = self._outgoing(man)
                    kind = "S"
                self._register_wait(index, kind, pipes)
            elif not man.halted:
                movers.append(index)
                self._runnable_men.add(index)
        for disp in self.displays:
            err = self._display_tick(disp, res)
            if err:
                self._tick_heap = None
                return err
        # 4. movement
        occupied = self._occupied
        for index in movers:
            man = self.men[index]
            if man.halted:
                continue
            nr, nc = man.r + man.direction[0], man.c + man.direction[1]
            if not man.room.contains_interior(nr, nc):
                # ONE GRACE TICK. The man enters the wall cell; the
                # fatal fires at the start of the next execute phase,
                # so the next tick's pipe shift and output emit still
                # happen. Measured against the organizers' engine: a
                # value one cell from the end of an output pipe lands
                # (gpt_brackets_17, live at 376,792), one thirteen
                # cells away is lost (gpt_brackets_18, 19/26).
                man.crashed = True
                man.halted = True
                self._runnable_men.discard(index)
                continue
            occupant = occupied.get((nr, nc))
            if occupant:
                man.halted = True
                occupant.halted = True
                self._runnable_men.discard(index)
                occupant_index = self._man_indices[id(occupant)]
                self._runnable_men.discard(occupant_index)
                self._clear_wait(occupant_index)
                continue
            del occupied[(man.r, man.c)]
            man.r, man.c = nr, nc
            occupied[(nr, nc)] = man
        self._tick_heap = None
        self._tick_current_index = -1
        return None

    # ------------------------------------------------------------- display
    def _display_tick(self, disp, res: RunResult):
        """Consume one value from ADDR, then DATA, then SWAP pipes."""
        by_side = {}
        for p in self.in_pipes.get(id(disp), []):
            by_side[p.side] = p
        for side in ("addr", "data", "swap"):
            pipe = by_side.get(side)
            if pipe is None or pipe.values[-1] is None:
                continue
            v = self._pipe_take(pipe, -1)
            size = disp.disp_w * disp.disp_h
            if side == "addr":
                if not 0 <= v < size:
                    return "display"
                disp.cursor = v
            elif side == "data":
                if not 0 <= v <= 15:
                    return "display"
                disp.next[disp.cursor // disp.disp_w][disp.cursor % disp.disp_w] = v
                disp.cursor = (disp.cursor + 1) % size
            else:  # swap
                if v not in (0, 1):
                    return "display"
                disp.current = [row[:] for row in disp.next]
                res.frames.append([row[:] for row in disp.current])
                res.frame_ticks.append(res.ticks)
                on_frame = getattr(self._controller, "on_frame", None)
                if on_frame:
                    verdict = on_frame(disp.current, res.ticks)
                    if verdict:
                        self._verdict = verdict
                if v == 0:
                    disp.next = [[0] * disp.disp_w for _ in range(disp.disp_h)]
                    disp.cursor = 0
        return None

    # ------------------------------------------------------- pipe selection
    def _outgoing(self, man):
        return self.out_pipes.get(id(man.room), [])

    def _incoming(self, man):
        return self.in_pipes.get(id(man.room), [])

    @staticmethod
    def _nearest(pipes_with_seg, pos):
        return min(
            pipes_with_seg,
            key=lambda ps: (
                abs(ps[1][0] - pos[0]) + abs(ps[1][1] - pos[1]),
                ps[1][0],
                ps[1][1],
            ),
        )[0]

    def _nearest_outgoing(self, man):
        key = (id(man.room), man.r, man.c)
        if key not in self._nearest_outgoing_cache:
            pipes = self._outgoing(man)
            self._nearest_outgoing_cache[key] = (
                self._nearest(
                    [(p, p.cells[0]) for p in pipes],
                    (man.r, man.c),
                )
                if pipes
                else None
            )
        return self._nearest_outgoing_cache[key]

    def _nearest_incoming(self, man):
        key = (id(man.room), man.r, man.c)
        if key not in self._nearest_incoming_cache:
            pipes = self._incoming(man)
            self._nearest_incoming_cache[key] = (
                self._nearest(
                    [(p, p.cells[-1]) for p in pipes],
                    (man.r, man.c),
                )
                if pipes
                else None
            )
        return self._nearest_incoming_cache[key]

    def _turn_away(self, man, pipe):
        dr, dc = pipe.cells[-1]
        room = man.room
        if dr < room.top:
            man.direction = DOWN
        elif dr > room.bottom:
            man.direction = UP
        elif dc < room.left:
            man.direction = RIGHT
        else:
            man.direction = LEFT

    # ------------------------------------------------------------ execution
    def _execute(self, man: Man):
        ch = self.grid[man.r][man.c]
        if ch in " .@":
            return None
        if ch == "`":
            value = self._literal_load(man)
            if value is not None:
                man.A = value
            return None
        if ch.isdigit():
            horizontal = man.direction in (LEFT, RIGHT)
            in_literal = (man.r, man.c) in (
                self.hdigits if horizontal else self.vdigits
            )
            if not in_literal:
                man.A = int(ch)
            return None
        if ch == "H":
            man.halted = True
            return None
        if ch == ">":
            man.direction = RIGHT
        elif ch == "<":
            man.direction = LEFT
        elif ch == "^":
            man.direction = UP
        elif ch in "vV":
            man.direction = DOWN
        elif ch == "M":
            man.B = man.A
        elif ch == "W":
            man.A, man.B = man.B, man.A
        elif ch == "+":
            man.A = wrap64(man.A + man.B)
        elif ch == "-":
            man.A = wrap64(man.A - man.B)
        elif ch == "*":
            man.A = wrap64(man.A * man.B)
        elif ch == "N":
            man.A = wrap64(-man.A)
        elif ch == "%":
            man.A = 0 if man.B == 0 else wrap64(man.A % man.B)
        elif ch == "/":
            if man.B == 0:
                man.A, man.B = 0, man.A
            else:
                q, rem = divmod(man.A, man.B)  # python divmod is floored
                man.A, man.B = wrap64(q), wrap64(rem)
        elif ch == "&":
            man.A = wrap64(man.A & man.B)
        elif ch == "|":
            man.A = wrap64(man.A | man.B)
        elif ch == "~":
            man.A = wrap64(man.A ^ man.B)
        elif ch == "{":
            man.A = wrap64(man.A << man.B) if 0 <= man.B <= 63 else 0
        elif ch == "}":
            if man.B < 0:
                man.A = 0
            else:
                man.A = wrap64(man.A >> min(man.B, 63))
        elif ch == "X":
            if man.A > 0:
                man.direction = CLOCKWISE[man.direction]
            elif man.A < 0:
                man.direction = COUNTERCW[man.direction]
        elif ch == "s":
            pipe = self._nearest_outgoing(man)
            if pipe is None:
                return "no-pipe"
            if pipe.values[0] is not None:
                man.blocked = True
            else:
                self._pipe_put(pipe, 0, man.A)
        elif ch == "S":
            pipes = self._outgoing(man)
            if not pipes:
                return "no-pipe"
            if any(p.values[0] is not None for p in pipes):
                man.blocked = True
            else:
                for p in pipes:
                    self._pipe_put(p, 0, man.A)
        elif ch == "r":
            pipe = self._nearest_incoming(man)
            if pipe is None:
                return "no-pipe"
            if pipe.values[-1] is None:
                man.blocked = True
            else:
                man.A = self._pipe_take(pipe, -1)
        elif ch in "RU":
            pipes = self._incoming(man)
            if not pipes:
                return "no-pipe"
            ready = [p for p in pipes if p.values[-1] is not None]
            if not ready:
                man.blocked = True
            else:
                pipe = min(ready, key=lambda p: p.cells[-1])
                man.A = self._pipe_take(pipe, -1)
                if ch == "U":
                    self._turn_away(man, pipe)
        elif ch == "q":
            pipe = self._nearest_incoming(man)
            if pipe is None:
                return "no-pipe"
            man.BP = pipe.count
        elif ch == "b":
            man.BP = man.A
        elif ch == "m":
            man.BP = wrap64(man.BP - 1)
        elif ch == "d":
            if man.BP > 0:
                man.direction = CLOCKWISE[man.direction]
        elif ch == "a":
            if man.BP > 0:
                man.direction = COUNTERCW[man.direction]
        elif ch == "]":
            man.BP = man.BP >> 1
        elif ch == "x":
            if man.BP & 1:
                man.direction = CLOCKWISE[man.direction]
            else:
                man.direction = COUNTERCW[man.direction]
        else:
            return "bad-op"
        return None
