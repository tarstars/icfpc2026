"""LLM interpreter re-expressed as seven components wired by integer FIFOs.

This module decomposes the validated monolith (`littleman.llm.LLM`) along the
boundaries proposed in `docs/architecture/claude_07_llm_attack.md`'s
"netlist" section: LOADER, GEOM, PIPETRACE, BIND, INIT_FRAME (setup time),
then EXEC and DELTA_DRAW (runtime, once per round). Every edge between
components is a :class:`Q` -- a FIFO that only ever carries plain Python
``int`` -- never tuples, strings or objects. Multi-field records are packed
into single ints with bit layouts documented below and next to each pack/
unpack helper.

Why this is safe to build on top of the monolith
--------------------------------------------------
`llm.py`'s own `LLM.parse` already reuses `littleman.sim.Machine.parse` for
geometry (room + pipe discovery) rather than reimplementing a parser; this
module leans on the same allowance. GEOM calls `Machine.parse` exactly the
way `LLM.parse` does. PIPETRACE calls the lower-level `Machine._find_pipes`
directly (not the full `Machine.parse`) so that it genuinely *consumes* the
room rectangles GEOM put on the queue, rather than silently re-deriving its
own -- the whole point of the exercise is that the queues carry real
information, not decorative wiring.

EXEC and DELTA_DRAW never call `LLM.step`/`LLM.render`; they reimplement the
tick semantics from scratch against the packed CELL/PIPE/MEN state described
below, driven only by queues.

The seven components and their queues
--------------------------------------
(class name -> claude_07 name; queues listed consumed-then-produced)

* `Loader`    -> LOADER:     in                          -> cell_loader, men_init, men_exec
* `Geom`      -> GEOM:       cell_loader                 -> rooms, cell_geom
* `PipeTrace` -> PIPETRACE:  cell_geom, rooms            -> rooms_relay, pipes_bind, pipes_exec, pipe_cells, cell_pipetrace
* `Bind`      -> BIND:       cell_pipetrace, rooms_relay, pipes_bind -> cell_final_init, cell_final_exec
* `InitFrame` -> INIT_FRAME: cell_final_init, men_init    -> addr, data, swap
* `Executor`  -> EXEC:       tick, cell_final_exec(setup), pipes_exec(setup), pipe_cells(setup), men_exec(setup) -> delta
* `DeltaDraw` -> DELTA_DRAW: delta                        -> addr, data, swap

`addr`/`data`/`swap` are shared: INIT_FRAME drives them once for round 0,
DELTA_DRAW drives them once per subsequent round -- exactly like a real
16x16 display room's ADDR/DATA/SWAP ports (see `sim.Machine._display_tick`),
just fed by whichever setup/runtime component currently holds the pen.

Deviations from claude_07's sketch (reported in full to the task owner)
-------------------------------------------------------------------------
1. **No W/H queue.** The doc's netlist doesn't mention dimensions crossing
   any boundary beyond LOADER. It turns out none is needed: the display is
   always a fixed 16x16 canvas (`DISPLAY = 16`, matching `llm.py`), so
   LOADER pads the real W x H program into the full 256-cell canvas with
   space (never a geometry character), and every downstream component
   operates on the fixed canvas. Padding with space cannot be mistaken for
   a room or pipe glyph, so this is exact, not approximate -- see the
   proof sketch in `Geom`'s docstring.
2. **EXEC does not receive room rectangles.** claude_07 lists rectangles
   as BIND's input, not EXEC's -- and indeed EXEC never needs them: the
   monolith's wall-freeze test (`any(room.on_border(...) for room in
   rooms)`) is a static property of an address, so GEOM bakes a WALL bit
   directly into the CELL record. EXEC just reads that bit.
3. **The PIPE table carries no runtime *value*.** claude_07's sketch
   describes a PIPE ring row as `(grid address, occupied flag, value+9)`,
   implying pipe payloads are packed as a small 0..18 field. That packing
   is unsound in general: `s` writes whatever `A` currently holds, and `A`
   is reached only through digit literals (0-9) plus wrap64 `+`/`-`, so a
   man that loops through arithmetic cells before sending can push a value
   well outside -9..9 (empirically the public suites only ever produce
   -9..7, but nothing in the semantics bounds it -- see the corpus scan
   used to check this before writing any packing code). This module
   sidesteps the question rather than answering it riskily: the *display*
   only ever needs to know whether a pipe cell is occupied (color 6 vs
   14), never the value itself, so no queue ever carries a raw pipe value.
   The value lives purely in `Executor`'s private Python state (a bare
   list, unrestricted since it never crosses a `Q`). If this is ever used
   as a template for a real hardware PIPE ring register, the value field
   must be a full-width word, not a packed 4-bit lane.
4. **Explicit fan-out queues.** A `Q` is single-consumer (FIFO, drained by
   `get`), but several setup values are needed by more than one downstream
   component (`rooms` by both PIPETRACE and BIND; pipe descriptors by both
   BIND and EXEC; men addresses by both INIT_FRAME and EXEC; the final
   CELL ring by both INIT_FRAME and EXEC). claude_07's per-row table only
   draws adjacent pairwise edges and doesn't specify this. This module
   resolves it the way real dataflow hardware would: a producer with two
   consumers pushes the same content onto two separately-named queues
   (`*_init`/`*_exec`, `*_bind`/`*_exec`), or relays it one hop further
   when the second consumer is downstream of the first (`rooms` ->
   PIPETRACE -> `rooms_relay` -> BIND).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .llm import COLOR_MAN, COLOR_PIPE, COLOR_PIPE_FULL, COLOR_WALL, HEADINGS, op_color
from .sim import Machine, Room as SimRoom, wrap64

DISPLAY = 16                     # matches llm.py's DISPLAY: the frame is always 16x16
NCELLS = DISPLAY * DISPLAY        # 256: the fixed, addressable CELL ring size
DELTA_END = -1                    # EXEC -> DELTA_DRAW frame delimiter

# Clockwise heading order N -> E -> S -> W, identical to llm.py's `_CW`.
_CW = [(-1, 0), (0, 1), (1, 0), (0, -1)]


# --------------------------------------------------------------------- Q
class Q:
    """A FIFO integer queue connecting two pipeline components.

    ``put`` enforces that only plain ``int`` travels on the wire: no bool
    (a Python ``int`` subclass, but never a meaningful record here), no
    float, no str, no tuple, no object. ``get`` pops the oldest value.

    When constructed with ``trace=True``, every value ever pushed is kept
    in ``.trace`` -- even after ``get()`` has consumed it -- so a full
    case run can be replayed end to end afterwards. That full stream is
    exactly what a hardware acceptance test for one component would later
    be driven with and checked against.
    """

    __slots__ = ("name", "_items", "_trace")

    def __init__(self, name: str, *, trace: bool = False):
        self.name = name
        self._items: deque[int] = deque()
        self._trace: list[int] | None = [] if trace else None

    def put(self, value: int) -> None:
        if type(value) is not int:
            raise TypeError(
                f"Q({self.name!r}).put only accepts plain int, "
                f"got {type(value).__name__}: {value!r}"
            )
        self._items.append(value)
        if self._trace is not None:
            self._trace.append(value)

    def get(self) -> int:
        return self._items.popleft()

    def __len__(self) -> int:
        return len(self._items)

    def empty(self) -> bool:
        return not self._items

    @property
    def trace(self) -> list[int]:
        if self._trace is None:
            raise RuntimeError(f"Q({self.name!r}) was not created with trace=True")
        return list(self._trace)


# ------------------------------------------------------------- record layouts
# CELL record -- travels on: cell_loader, cell_geom, cell_pipetrace,
# cell_final_init, cell_final_exec. One int per grid address (address =
# r * DISPLAY + c, the 16x16 canvas is always fully populated, real program
# columns/rows beyond the actual W/H are padded with space):
#
#   bits 0-7   char   ord() of the grid character ('@' already replaced by
#                      ' ' at LOADER time -- '@' is a pure start marker and
#                      is a no-op wherever it appears, exactly like space)
#   bits 8-11  color  resting (unoccupied-by-man) display color, 0-15
#   bit  12    wall   1 if this address sits on some room's border
#   bit  13    pipe   1 if this address belongs to some pipe's cell chain
#   bits 14-15 bind   0 = unbound; 1 = pipe #0; 2 = pipe #1
#                      (meaningful only when char is 's' or 'r')
def pack_cell(char: int, color: int, wall: int, pipe: int, bind: int) -> int:
    return (
        (char & 0xFF)
        | ((color & 0xF) << 8)
        | ((wall & 0x1) << 12)
        | ((pipe & 0x1) << 13)
        | ((bind & 0x3) << 14)
    )


def unpack_cell(rec: int) -> tuple[int, int, int, int, int]:
    char = rec & 0xFF
    color = (rec >> 8) & 0xF
    wall = (rec >> 12) & 0x1
    pipe = (rec >> 13) & 0x1
    bind = (rec >> 14) & 0x3
    return char, color, wall, pipe, bind


# ROOM record -- travels on: rooms, rooms_relay. One int per room rectangle
# (coordinates are always 0..15 since the canvas is fixed 16x16):
#
#   bits 0-3   top
#   bits 4-7   left
#   bits 8-11  bottom
#   bits 12-15 right
def pack_room(top: int, left: int, bottom: int, right: int) -> int:
    return (top & 0xF) | ((left & 0xF) << 4) | ((bottom & 0xF) << 8) | ((right & 0xF) << 12)


def unpack_room(rec: int) -> tuple[int, int, int, int]:
    return rec & 0xF, (rec >> 4) & 0xF, (rec >> 8) & 0xF, (rec >> 12) & 0xF


# PIPE descriptor -- travels on: pipes_bind, pipes_exec. One int per pipe,
# in source-to-dest flow order (<= 2 pipes total):
#
#   bits 0-4   cell_count   number of cells in this pipe (<= 20 total, all pipes)
#   bits 5-6   source_room  room index (0..2) the pipe leaves from
#   bits 7-8   dest_room    room index (0..2) the pipe arrives at
#   bits 9-16  head_addr    address of cells[0] (where `s` writes)
#   bits 17-24 tail_addr    address of cells[-1] (where `r` reads)
def pack_pipe_desc(cell_count: int, source: int, dest: int, head: int, tail: int) -> int:
    return (
        (cell_count & 0x1F)
        | ((source & 0x3) << 5)
        | ((dest & 0x3) << 7)
        | ((head & 0xFF) << 9)
        | ((tail & 0xFF) << 17)
    )


def unpack_pipe_desc(rec: int) -> tuple[int, int, int, int, int]:
    cell_count = rec & 0x1F
    source = (rec >> 5) & 0x3
    dest = (rec >> 7) & 0x3
    head = (rec >> 9) & 0xFF
    tail = (rec >> 17) & 0xFF
    return cell_count, source, dest, head, tail


# DELTA record -- travels on: delta (EXEC -> DELTA_DRAW).  This is exactly
# the accepted LLLM DRAW grammar: ``addr*16 + color`` for a changed address
# and :data:`DELTA_END` after every frame.
def pack_delta(addr: int, color: int) -> int:
    return (addr & 0xFF) * 16 + (color & 0xF)


def unpack_delta(rec: int) -> tuple[int, int]:
    return divmod(rec, 16)


def addr_of(r: int, c: int) -> int:
    return r * DISPLAY + c


# ------------------------------------------------------------- 1. LOADER
class Loader:
    """LOADER: input tokens -> CELL records + men addresses.

    Consumes ``q_in``: ``W H c0 c1 ... c(W*H-1)`` (round 0's raw input,
    already converted to int by the caller).

    Produces:
    * ``q_cell_out``  -- 256 CELL records (see layout above), address
      order 0..255 over the fixed canvas; real content occupies rows
      0..H-1, cols 0..W-1, the rest is space (color/wall/pipe/bind all 0).
    * ``q_men_init``, ``q_men_exec`` -- the same content on two queues
      (fan-out to INIT_FRAME and EXEC): a count, then that many start
      addresses, in row-major discovery order (mirrors `LLM.parse`'s own
      `men` list order).
    """

    def run(self, q_in: Q, q_cell_out: Q, q_men_init: Q, q_men_exec: Q) -> None:
        width = q_in.get()
        height = q_in.get()

        chars = [ord(" ")] * NCELLS
        men_addrs: list[int] = []
        for idx in range(width * height):
            code = q_in.get()
            r, c = divmod(idx, width)
            if r >= DISPLAY or c >= DISPLAY:
                # Contract keeps W,H <= 16 (verified on all public + fuzz
                # data); this guard just mirrors render()'s own truncation
                # to DISPLAY x DISPLAY if it were ever violated.
                continue
            ch = chr(code)
            if ch == "@":
                men_addrs.append(addr_of(r, c))
                ch = " "
            chars[addr_of(r, c)] = ord(ch)

        for addr in range(NCELLS):
            ch = chr(chars[addr])
            q_cell_out.put(pack_cell(ord(ch), op_color(ch), 0, 0, 0))

        q_men_init.put(len(men_addrs))
        q_men_exec.put(len(men_addrs))
        for a in men_addrs:
            q_men_init.put(a)
            q_men_exec.put(a)


# --------------------------------------------------------------- 2. GEOM
class Geom:
    """GEOM: CELL ring -> wall flags/colors baked in, plus room rectangles.

    Reconstructs program text purely from the popped CELL characters (16
    rows of 16 chars, the fixed canvas), then calls ``Machine.parse`` --
    the same allowed reuse `LLM.parse` makes -- to find rooms.

    Padding proof sketch (why the fixed 16x16 canvas is exact, not just
    convenient): room/pipe discovery in `sim.Machine` only ever pattern-
    matches specific non-space glyphs (`+ - | < > ^ v`, etc.) at exact
    relative offsets. Padding cells are unconditionally space, which can
    never satisfy any of those patterns, so no room or pipe can ever be
    found partly or wholly in padding, regardless of how much of the
    canvas is real program vs. padding.

    Consumes ``q_cell_in`` (256 CELL records, raw from LOADER).
    Produces:
    * ``q_rooms_out`` -- a count, then that many ROOM records.
    * ``q_cell_out``  -- 256 CELL records, now with the wall bit set and
      color forced to COLOR_WALL for every address on any room's border.
    """

    def run(self, q_cell_in: Q, q_rooms_out: Q, q_cell_out: Q) -> None:
        chars = [0] * NCELLS
        colors = [0] * NCELLS
        for addr in range(NCELLS):
            char, color, _wall, _pipe, _bind = unpack_cell(q_cell_in.get())
            chars[addr] = char
            colors[addr] = color

        rows = [
            "".join(chr(chars[addr_of(r, c)]) for c in range(DISPLAY))
            for r in range(DISPLAY)
        ]
        machine = Machine.parse("\n".join(rows))
        rooms = [(rm.top, rm.left, rm.bottom, rm.right) for rm in machine.rooms]

        q_rooms_out.put(len(rooms))
        for top, left, bottom, right in rooms:
            q_rooms_out.put(pack_room(top, left, bottom, right))

        for addr in range(NCELLS):
            r, c = divmod(addr, DISPLAY)
            is_wall = any(
                top <= r <= bottom
                and left <= c <= right
                and (r in (top, bottom) or c in (left, right))
                for top, left, bottom, right in rooms
            )
            color = COLOR_WALL if is_wall else colors[addr]
            q_cell_out.put(pack_cell(chars[addr], color, 1 if is_wall else 0, 0, 0))


# ---------------------------------------------------------- 3. PIPETRACE
class PipeTrace:
    """PIPETRACE: CELL ring + rectangles -> PIPE table, pipe cells recolored.

    Consumes ``q_cell_in`` (256 CELL records from GEOM) and ``q_rooms_in``
    (GEOM's room rectangles). Calls the lower-level ``Machine._find_pipes``
    directly (not the full ``Machine.parse``) against ROOM OBJECTS
    reconstructed from ``q_rooms_in`` -- so this component genuinely
    consumes what GEOM put on the queue, rather than silently re-deriving
    its own independent rooms.

    Produces:
    * ``q_rooms_relay``            -- the same room rectangles, forwarded
      unchanged (BIND is one hop further downstream and needs them too).
    * ``q_pipes_bind``, ``q_pipes_exec`` -- a count, then that many PIPE
      descriptors, fanned out to both consumers.
    * ``q_pipe_cells``              -- every pipe's cell addresses,
      flattened in (pipe order, source-to-dest) order, no count prefix
      needed (each descriptor already carries its own cell_count).
    * ``q_cell_out``                -- 256 CELL records, now with the pipe
      bit set and color forced to COLOR_PIPE (6, the empty-pipe color) for
      every pipe-cell address.
    """

    def run(
        self,
        q_cell_in: Q,
        q_rooms_in: Q,
        q_rooms_relay: Q,
        q_pipes_bind: Q,
        q_pipes_exec: Q,
        q_pipe_cells: Q,
        q_cell_out: Q,
    ) -> None:
        chars = [0] * NCELLS
        colors = [0] * NCELLS
        walls = [0] * NCELLS
        for addr in range(NCELLS):
            char, color, wall, _pipe, _bind = unpack_cell(q_cell_in.get())
            chars[addr] = char
            colors[addr] = color
            walls[addr] = wall

        nrooms = q_rooms_in.get()
        q_rooms_relay.put(nrooms)
        rooms_rect: list[tuple[int, int, int, int]] = []
        for _ in range(nrooms):
            rec = q_rooms_in.get()
            rooms_rect.append(unpack_room(rec))
            q_rooms_relay.put(rec)

        rows = [
            "".join(chr(chars[addr_of(r, c)]) for c in range(DISPLAY))
            for r in range(DISPLAY)
        ]
        grid = [list(row) for row in rows]
        sim_rooms = [SimRoom(top, left, bottom, right) for top, left, bottom, right in rooms_rect]
        pipes = Machine._find_pipes(grid, sim_rooms)
        room_index = {id(room): i for i, room in enumerate(sim_rooms)}

        q_pipes_bind.put(len(pipes))
        q_pipes_exec.put(len(pipes))
        flat_cells: list[int] = []
        for pipe in pipes:
            addrs = [addr_of(r, c) for r, c in pipe.cells]
            desc = pack_pipe_desc(
                len(addrs),
                room_index[id(pipe.source)],
                room_index[id(pipe.dest)],
                addrs[0],
                addrs[-1],
            )
            q_pipes_bind.put(desc)
            q_pipes_exec.put(desc)
            flat_cells.extend(addrs)
        for a in flat_cells:
            q_pipe_cells.put(a)

        pipe_addr_set = set(flat_cells)
        for addr in range(NCELLS):
            if addr in pipe_addr_set:
                q_cell_out.put(pack_cell(chars[addr], COLOR_PIPE, walls[addr], 1, 0))
            else:
                q_cell_out.put(pack_cell(chars[addr], colors[addr], walls[addr], 0, 0))


# ---------------------------------------------------------------- 4. BIND
class Bind:
    """BIND: rectangles + PIPE table -> binding ids written into CELL records.

    For every 's'/'r' address, the man executing it is *at* that address
    (he must be standing on it to execute it), so the nearest-pipe lookup
    the monolith performs live (`LLM._nearest`) is a pure function of the
    cell's own position and room -- it can be precomputed once here,
    exactly the way claude_07 claims. With <= 2 pipes this is one
    Manhattan-distance comparison per s/r cell, tie-broken the same way
    `LLM._nearest` does: (distance, target_row, target_col).

    Consumes ``q_cell_in`` (256 CELL records from PIPETRACE),
    ``q_rooms_in`` (rectangles, relayed by PIPETRACE), ``q_pipes_in``
    (PIPE descriptors, from PIPETRACE).

    Produces ``q_cell_out_init``, ``q_cell_out_exec`` -- 256 CELL records
    each (fan-out), identical to the input except the bind field is now
    set for every 's'/'r' address (0 if no matching pipe exists).
    """

    def run(
        self,
        q_cell_in: Q,
        q_rooms_in: Q,
        q_pipes_in: Q,
        q_cell_out_init: Q,
        q_cell_out_exec: Q,
    ) -> None:
        chars = [0] * NCELLS
        colors = [0] * NCELLS
        walls = [0] * NCELLS
        pipe_flags = [0] * NCELLS
        for addr in range(NCELLS):
            char, color, wall, pipe, _bind = unpack_cell(q_cell_in.get())
            chars[addr] = char
            colors[addr] = color
            walls[addr] = wall
            pipe_flags[addr] = pipe

        nrooms = q_rooms_in.get()
        rooms_rect = [unpack_room(q_rooms_in.get()) for _ in range(nrooms)]

        npipes = q_pipes_in.get()
        pipe_descs = []
        for _ in range(npipes):
            _cell_count, source, dest, head, tail = unpack_pipe_desc(q_pipes_in.get())
            pipe_descs.append((source, dest, head, tail))

        def room_of_interior(r: int, c: int) -> int | None:
            for idx, (top, left, bottom, right) in enumerate(rooms_rect):
                if top < r < bottom and left < c < right:
                    return idx
            return None

        for addr in range(NCELLS):
            bind_id = 0
            ch = chr(chars[addr])
            if ch in "sr":
                r, c = divmod(addr, DISPLAY)
                room_idx = room_of_interior(r, c)
                if room_idx is not None:
                    outgoing = ch == "s"
                    candidates = []
                    for pno, (source, dest, head, tail) in enumerate(pipe_descs):
                        if (source if outgoing else dest) == room_idx:
                            target_addr = head if outgoing else tail
                            tr, tc = divmod(target_addr, DISPLAY)
                            dist = abs(tr - r) + abs(tc - c)
                            candidates.append((dist, tr, tc, pno))
                    if candidates:
                        candidates.sort()
                        bind_id = candidates[0][3] + 1
            rec = pack_cell(chars[addr], colors[addr], walls[addr], pipe_flags[addr], bind_id)
            q_cell_out_init.put(rec)
            q_cell_out_exec.put(rec)


# ----------------------------------------------------------- 5. INIT_FRAME
class InitFrame:
    """INIT_FRAME: CELL ring + men -> the round-0 display frame.

    Consumes ``q_cell_in`` (256 final CELL records from BIND) and
    ``q_men_in`` (start addresses from LOADER).

    Produces ``q_addr``/``q_data`` -- 256 (address, color) pairs in
    address order (the resting color already bakes in wall/pipe
    precedence), then one more pair per man (address, COLOR_MAN) to draw
    him over everything -- then ``q_swap`` = 1 to commit the frame.
    """

    def run(self, q_cell_in: Q, q_men_in: Q, q_addr: Q, q_data: Q, q_swap: Q) -> None:
        for addr in range(NCELLS):
            _char, color, _wall, _pipe, _bind = unpack_cell(q_cell_in.get())
            q_addr.put(addr)
            q_data.put(color)

        nmen = q_men_in.get()
        for _ in range(nmen):
            addr = q_men_in.get()
            q_addr.put(addr)
            q_data.put(COLOR_MAN)

        q_swap.put(1)


# ---------------------------------------------------------------- man state
@dataclass
class _ManState:
    """EXEC's private per-man state. Never touches a Q; free-form Python."""

    r: int
    c: int
    heading: tuple[int, int] = (0, 1)   # men always start facing east
    A: int = 0
    B: int = 0
    halted: bool = False
    on_wall: bool = False


# -------------------------------------------------------------------- 6. EXEC
class Executor:
    """EXEC: per interpreted tick, pipe shift -> per-man fetch/execute/move
    -> delta records out.

    ``setup`` consumes the fully-annotated CELL ring (``q_cell``), the
    PIPE descriptors (``q_pipes``) and flattened pipe cell addresses
    (``q_pipe_cells``), and the men start addresses (``q_men``) -- run
    exactly once, right after BIND/LOADER, before the first tick.

    ``run`` consumes ``q_tick`` (a single int ``k``, the round's step
    count) and executes up to ``k`` ticks (fewer if the program halts or
    freezes on a wall first), reproducing `LLM.step`'s tick order exactly:
    pipes shift, every man executes the op under him (using the
    precomputed ``bind`` id instead of `LLM._nearest`), then every
    non-blocked man advances one cell against a live occupancy map. A
    wall freezes everything, but only after the tick completes in full.

    It never calls `LLM.step`/`LLM.render`; the state below (``char``,
    ``static_color``, ``wall``, ``bind``, ``pipe_cells``, ``pipe_values``,
    ``men``) is this component's own reimplementation, driven only by what
    arrived on its queues.

    Produces ``q_delta``: for every tick, every address whose display
    color changed (a pipe cell's occupancy flipped 6<->14, or a man
    entered/vacated a cell) is pushed at most once, packed via
    :func:`pack_delta`. Candidates are exactly the addresses claude_07
    bounds the frame delta by: all pipe cells (<= 20) plus every man's
    pre- and post-tick address (<= 3 men, <= 6 addresses) -- nothing else
    can change color in one tick.
    """

    def setup(self, q_cell: Q, q_pipes: Q, q_pipe_cells: Q, q_men: Q) -> None:
        self.char = [0] * NCELLS
        self.static_color = [0] * NCELLS
        self.wall = [False] * NCELLS
        self.bind = [0] * NCELLS
        for addr in range(NCELLS):
            char, color, wall, _pipe, bind = unpack_cell(q_cell.get())
            self.char[addr] = char
            self.static_color[addr] = color
            self.wall[addr] = bool(wall)
            self.bind[addr] = bind

        npipes = q_pipes.get()
        self.pipe_cells: list[list[int]] = []
        self.pipe_values: list[list[int | None]] = []
        self._pipe_index_of: dict[int, tuple[int, int]] = {}
        for pno in range(npipes):
            cell_count, _source, _dest, _head, _tail = unpack_pipe_desc(q_pipes.get())
            addrs = [q_pipe_cells.get() for _ in range(cell_count)]
            self.pipe_cells.append(addrs)
            self.pipe_values.append([None] * cell_count)
            for cno, a in enumerate(addrs):
                self._pipe_index_of[a] = (pno, cno)
        self._all_pipe_addrs = [a for cells in self.pipe_cells for a in cells]

        nmen = q_men.get()
        self.men = [_ManState(*divmod(q_men.get(), DISPLAY)) for _ in range(nmen)]
        self.over = False

        men_positions = {addr_of(m.r, m.c) for m in self.men}
        self._last_color = [self._color_at(addr, men_positions) for addr in range(NCELLS)]

    def halted(self) -> bool:
        return self.over or all(m.halted or m.on_wall for m in self.men)

    def run(self, q_tick: Q, q_delta: Q) -> None:
        k = q_tick.get()
        for _ in range(k):
            if self.halted():
                break
            self._step(q_delta)
        q_delta.put(DELTA_END)

    def _color_at(self, addr: int, men_positions: set[int]) -> int:
        if addr in men_positions:
            return COLOR_MAN
        idx = self._pipe_index_of.get(addr)
        if idx is not None:
            pno, cno = idx
            if self.pipe_values[pno][cno] is not None:
                return COLOR_PIPE_FULL
        return self.static_color[addr]

    def _step(self, q_delta: Q) -> None:
        # 1. pipes shift one cell toward their destination, if free.
        for vals in self.pipe_values:
            for i in range(len(vals) - 1, 0, -1):
                if vals[i] is None and vals[i - 1] is not None:
                    vals[i] = vals[i - 1]
                    vals[i - 1] = None

        old_positions = [addr_of(m.r, m.c) for m in self.men]

        # 2. every man executes the op under him.
        moving: list[_ManState] = []
        for man in self.men:
            if man.halted or man.on_wall:
                continue
            addr = addr_of(man.r, man.c)
            ch = chr(self.char[addr])
            if ch == "H":
                man.halted = True
                continue
            if ch in HEADINGS:
                man.heading = HEADINGS[ch]
            elif ch.isdigit():
                man.A = int(ch)
            elif ch == "M":
                man.B = man.A
            elif ch == "+":
                man.A = wrap64(man.A + man.B)
            elif ch == "-":
                man.A = wrap64(man.A - man.B)
            elif ch == "X":
                if man.A:
                    turn = 1 if man.A > 0 else -1
                    man.heading = _CW[(_CW.index(man.heading) + turn) % 4]
            elif ch == "s":
                pid = self.bind[addr]
                if pid == 0:
                    continue
                pvals = self.pipe_values[pid - 1]
                if pvals[0] is not None:
                    continue
                pvals[0] = man.A
            elif ch == "r":
                pid = self.bind[addr]
                if pid == 0:
                    continue
                pvals = self.pipe_values[pid - 1]
                if pvals[-1] is None:
                    continue
                man.A = pvals[-1]
                pvals[-1] = None
            moving.append(man)

        # 3. every non-blocked man advances, against a live occupancy map:
        # stepping into a cell another man currently occupies stops both
        # (the mover stays put); stepping into a cell vacated earlier in
        # this same phase is legal. Mirrors `LLM.step` exactly.
        occupied = {(m.r, m.c): m for m in self.men}
        for man in moving:
            if man.halted:
                continue
            dr, dc = man.heading
            nr, nc = man.r + dr, man.c + dc
            other = occupied.get((nr, nc))
            if other is not None:
                man.halted = True
                other.halted = True
                continue
            del occupied[(man.r, man.c)]
            man.r, man.c = nr, nc
            occupied[(nr, nc)] = man

        # 4. a wall freezes everything, but only after the tick completes.
        for man in self.men:
            if man.halted or man.on_wall:
                continue
            if self.wall[addr_of(man.r, man.c)]:
                man.on_wall = True
                self.over = True

        new_positions = [addr_of(m.r, m.c) for m in self.men]
        men_position_set = set(new_positions)
        candidates = list(self._all_pipe_addrs)
        candidates.extend(old_positions)
        candidates.extend(new_positions)
        for addr in candidates:
            color = self._color_at(addr, men_position_set)
            if color != self._last_color[addr]:
                self._last_color[addr] = color
                q_delta.put(pack_delta(addr, color))


# ---------------------------------------------------------- 7. DELTA_DRAW
class DeltaDraw:
    """DELTA_DRAW: DELTA queue -> ADDR/DATA pairs + SWAP=1.

    Reads one explicitly delimited frame, forwards each nonnegative record
    as an (address, color) pair, then commits with ``q_swap.put(1)``.
    Queue emptiness is deliberately irrelevant: in the physical machine a
    temporarily empty pipe cannot mean end-of-frame.
    """

    def run(self, q_delta: Q, q_addr: Q, q_data: Q, q_swap: Q) -> None:
        while True:
            rec = q_delta.get()
            if rec == DELTA_END:
                break
            addr, color = unpack_delta(rec)
            q_addr.put(addr)
            q_data.put(color)
        q_swap.put(1)


# ------------------------------------------------------------- the pipeline
class LLMPipeline:
    """Wires the seven components together and drives one case's rounds.

    ``run_case(rounds)`` mirrors `tests/test_llm.py::replay`: ``rounds[0]``
    is the program load (``in`` = ``W H c0 c1 ...``), each subsequent round
    is one step command (``in`` = ``[k]``); one 16-row hex-string frame is
    returned per round, in round order.

    With ``trace=True``, every queue's full lifetime token stream is kept
    (see :class:`Q`) and retrievable via :meth:`traces` after a run --
    reflecting the most recent ``run_case`` call.
    """

    def __init__(self, trace: bool = False):
        self._trace = trace
        self._queues: dict[str, Q] = {}

    def _mk(self, name: str) -> Q:
        q = Q(name, trace=self._trace)
        self._queues[name] = q
        return q

    def traces(self) -> dict[str, list[int]]:
        if not self._trace:
            raise RuntimeError("LLMPipeline(trace=True) is required for traces()")
        return {name: q.trace for name, q in self._queues.items()}

    def run_case(self, rounds: list[dict]) -> list[list[str]]:
        self._queues = {}
        tokens = [int(v) for v in rounds[0]["in"]]

        q_in = self._mk("in")
        for t in tokens:
            q_in.put(t)

        q_cell_loader = self._mk("cell_loader")
        q_men_init = self._mk("men_init")
        q_men_exec = self._mk("men_exec")
        Loader().run(q_in, q_cell_loader, q_men_init, q_men_exec)

        q_rooms = self._mk("rooms")
        q_cell_geom = self._mk("cell_geom")
        Geom().run(q_cell_loader, q_rooms, q_cell_geom)

        q_rooms_relay = self._mk("rooms_relay")
        q_pipes_bind = self._mk("pipes_bind")
        q_pipes_exec = self._mk("pipes_exec")
        q_pipe_cells = self._mk("pipe_cells")
        q_cell_pipetrace = self._mk("cell_pipetrace")
        PipeTrace().run(
            q_cell_geom, q_rooms, q_rooms_relay,
            q_pipes_bind, q_pipes_exec, q_pipe_cells, q_cell_pipetrace,
        )

        q_cell_final_init = self._mk("cell_final_init")
        q_cell_final_exec = self._mk("cell_final_exec")
        Bind().run(q_cell_pipetrace, q_rooms_relay, q_pipes_bind, q_cell_final_init, q_cell_final_exec)

        q_addr = self._mk("addr")
        q_data = self._mk("data")
        q_swap = self._mk("swap")
        InitFrame().run(q_cell_final_init, q_men_init, q_addr, q_data, q_swap)

        display = [0] * NCELLS
        frames = [self._drain_frame(q_addr, q_data, q_swap, display)]

        executor = Executor()
        executor.setup(q_cell_final_exec, q_pipes_exec, q_pipe_cells, q_men_exec)

        q_tick = self._mk("tick")
        q_delta = self._mk("delta")
        for rnd in rounds[1:]:
            k = int(rnd["in"][0])
            q_tick.put(k)
            executor.run(q_tick, q_delta)
            DeltaDraw().run(q_delta, q_addr, q_data, q_swap)
            frames.append(self._drain_frame(q_addr, q_data, q_swap, display))

        return frames

    @staticmethod
    def _drain_frame(q_addr: Q, q_data: Q, q_swap: Q, display: list[int]) -> list[str]:
        while not q_addr.empty():
            addr = q_addr.get()
            color = q_data.get()
            display[addr] = color
        swap = q_swap.get()
        assert swap == 1
        return [
            "".join(f"{display[addr_of(r, c)]:x}" for c in range(DISPLAY))
            for r in range(DISPLAY)
        ]
