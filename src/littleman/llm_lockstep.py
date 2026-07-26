"""Lockstep model of full LLM semantics: multi-man + pipes + global freeze.

ONE interpreter, ONE tick loop, round-robin over men inside the tick — the
exact shape the littleman machine will run. ``littleman.llm.LLM`` is the
oracle; this module re-derives room AND pipe discovery from the raw grid
(the machine's SCAN must do the same) and keeps all mutable state in plain
integers so every line maps onto machine scratch slots.

Tick (one ``step``):
  1. every pipe shifts one cell toward dest (tail-first gap fill)
  2. men in index order execute the op under them; H halts that man only;
     s/r blocked (no pipe / full head / empty tail) records no move intent
  3. men with a move intent advance in index order against a live
     occupancy map: stepping onto an occupied cell halts BOTH men (mover
     stays put); a cell vacated earlier in this same phase is free
  4. any never-halted man now on a room border freezes the WHOLE program
     (over=1) — but only after the tick completed in full for everyone.

State budget for the machine (constraints: <=3 rooms/men, <=2 pipes,
<=20 pipe cells total, pipe values -9..9, 4 <= W,H <= 16, <=100 ticks):
  per man   : r,c (4+4 bits) + heading (2) + halted,on_wall (2) = 12 bits;
              all 3 men fit ONE 64-bit slot as 21-bit fields
              (memory_packed.py pattern); A and B need full slots -> 6.
  per pipe  : static descriptor from SCAN — cells as 8-bit r,c pairs,
              20 cells = 160 bits -> 3 slots, + len/src/dst per pipe in
              one shared slot; dynamic — 20 presence bits for both pipes
              in one slot + values 5 bits signed -> 2 slots.
  global    : freeze flag + man index + tick counter -> 1 slot.
  total     : ~13 scratch slots beyond the program grid itself.
"""

from __future__ import annotations

from .lllm_scan import MEN, WALL_BIT, scan_reference_v2

FIELD = 13       # world packing: 4 cell tokens per word (CLASSIFY layout)
CELL_FIELD = 21  # descriptor packing: 3 cell addrs per word (memory_packed)
DESC_WORDS = 8   # fixed descriptor width: 1 header word + 7 cell words
M64 = (1 << 64) - 1
DISPLAY = 16
DR = (-1, 0, 1, 0)  # heading index 0=N 1=E 2=S 3=W (clockwise order)
DC = (0, 1, 0, -1)
ARROW = {"^": 0, ">": 1, "v": 2, "<": 3}


def wrap64(v: int) -> int:
    v &= M64
    return v - (1 << 64) if v >= (1 << 63) else v


def _contains(rm, r, c):
    return rm[0] <= r <= rm[2] and rm[1] <= c <= rm[3]


def _on_border(rm, r, c):
    return _contains(rm, r, c) and (r in (rm[0], rm[2]) or c in (rm[1], rm[3]))


def find_rooms(grid):
    """Row-major scan for +--+/| frames; drop candidates nested in another.

    Mirrors sim.Machine._find_rooms for plain rooms (LLM has no displays).
    Room order = scan order of the top-left corner, which fixes room
    indices, pipe order and man->room assignment downstream.
    """
    h = len(grid)
    w = len(grid[0]) if h else 0
    cand = []
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
            if not all(grid[r2][x] == "-" for x in range(c + 1, c2)):
                continue
            if not all(grid[y][c2] == "|" for y in range(r + 1, r2)):
                continue
            cand.append((r, c, r2, c2))
    rooms = []
    for i, a in enumerate(cand):
        nested = any(
            j != i
            and b[0] <= a[0] and b[1] <= a[1]
            and b[2] >= a[2] and b[3] >= a[3]
            for j, b in enumerate(cand)
        )
        if not nested:
            rooms.append(a)
    return rooms


def find_pipes(grid, rooms):
    """(cells, src, dst) per pipe, cells ordered source -> dest.

    Mirrors sim.Machine._find_pipes: for each room in index order, scan its
    border (top row, then left/right sides, then bottom row, left to right)
    for an adjacent outside cell holding an arrow that points AWAY from the
    room (probe order N,S,W,E) — that cell is a pipe head. Trace from there.
    Head/tail cells sit OUTSIDE both rooms, next to their walls.
    """
    h = len(grid)
    w = len(grid[0]) if h else 0
    used, pipes = set(), []
    for si, rm in enumerate(rooms):
        starts = []
        for r in range(rm[0], rm[2] + 1):
            cols = (
                range(rm[1], rm[3] + 1)
                if r in (rm[0], rm[2])
                else (rm[1], rm[3])
            )
            for c in cols:
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    gr, gc = r + dr, c + dc
                    if not (0 <= gr < h and 0 <= gc < w):
                        continue
                    if _contains(rm, gr, gc) or (gr, gc) in used:
                        continue
                    d = ARROW.get(grid[gr][gc])
                    if d is not None and (DR[d], DC[d]) == (dr, dc):
                        starts.append((gr, gc, d))
        for gr, gc, d in starts:
            if (gr, gc) in used:
                continue
            traced = _trace(grid, rooms, si, gr, gc, d)
            used.update(traced[0])
            pipes.append(traced)
    return pipes


def _trace(grid, rooms, si, r, c, d):
    """Follow arrows/body glyphs until one cell ahead is another room's wall."""
    h, w = len(grid), len(grid[0])
    cells = [(r, c)]
    while True:
        ch = grid[r][c]
        if ch in ARROW:
            nd = ARROW[ch]
            if len(cells) > 1 and (DR[nd], DC[nd]) == (-DR[d], -DC[d]):
                raise ValueError(f"pipe reverses at {(r, c)}")
            d = nd
            fr, fc = r + DR[d], c + DC[d]
            if 0 <= fr < h and 0 <= fc < w:
                ti = next(
                    (
                        i
                        for i, rm in enumerate(rooms)
                        if _on_border(rm, fr, fc)
                    ),
                    -1,
                )
                if ti >= 0 and ti != si:
                    return (cells, si, ti)
        r, c = r + DR[d], c + DC[d]
        if not (0 <= r < h and 0 <= c < w):
            raise ValueError("pipe runs off grid")
        ch = grid[r][c]
        body = "-" if d in (1, 3) else "|"
        if ch in ARROW or ch == body:
            cells.append((r, c))
        else:
            raise ValueError(f"bad pipe glyph {ch!r} at {(r, c)}")


class LockstepLLM:
    """Parsed LLM program plus machine-shaped integer running state."""

    def __init__(self, rows):
        """Discovery attrs from the grid, but the RUNTIME state is loaded
        from ``machine_stream`` output — so every rows-built interpreter
        proves stream completeness on every case it passes."""
        self.rows = list(rows)
        w = max((len(r) for r in self.rows), default=0)
        grid = [list(r.ljust(w)) for r in self.rows]
        self.rooms = find_rooms(grid)
        traced = find_pipes(grid, self.rooms)
        self.pipe_src = [t[1] for t in traced]
        self.pipe_dst = [t[2] for t in traced]
        self._load_stream(machine_stream(self.rows))

    @classmethod
    def parse(cls, rows):
        return cls(rows)

    @classmethod
    def from_stream(cls, stream):
        """Build a runnable interpreter from machine_stream output alone."""
        obj = cls.__new__(cls)
        obj.rows = None  # discovery attrs absent: stream is all it gets
        obj._load_stream(list(stream))
        return obj

    def _load_stream(self, stream):
        cells = [
            word >> (FIELD * k) & ((1 << FIELD) - 1)
            for word in stream[:64]
            for k in range(4)
        ]
        self.chars = [
            "".join(chr(cells[y * 16 + x] & 0xFF) for x in range(16))
            for y in range(16)
        ]
        self.wallmask = sum(
            1 << addr for addr in range(256) if cells[addr] & WALL_BIT
        )
        self.man_r, self.man_c = [], []
        for addr in reversed(stream[64 : 64 + MEN]):
            if addr:
                self.man_r.append(addr // 16)
                self.man_c.append(addr % 16)
        n = len(self.man_r)
        self.man_h = [1] * n  # every man starts facing east
        self.man_a = [0] * n
        self.man_b = [0] * n
        self.man_halt = [0] * n
        self.man_wall = [0] * n
        count = stream[64 + MEN]
        self.pipe_cells, self.pipe_out, self.pipe_in = [], [], []
        for p in range(count):
            base = 65 + MEN + p * DESC_WORDS
            head = stream[base]
            self.pipe_out.append(head >> 21 & 7)
            self.pipe_in.append(head >> 24 & 7)
            addrs = [
                stream[base + 1 + w] >> (CELL_FIELD * k)
                & ((1 << CELL_FIELD) - 1)
                for w in range(7)
                for k in range(3)
            ]
            self.pipe_cells.append(
                [divmod(a, 16) for a in addrs[: head & 31]]
            )
        self.pipe_mask = [0] * count
        self.pipe_vals = [[0] * len(c) for c in self.pipe_cells]
        self.over = 0

    def _at(self, r, c):
        return self.chars[r][c]  # canvas chars: `@` already reads as space

    def _nearest(self, mi, outgoing):
        """Nearest usable pipe arrowhead index for man ``mi``, or -1.

        Candidates come from the descriptor masks (bit mi of out/in), key =
        (Manhattan distance to head for s / tail for r, head row, head
        col): ties break in reading order of the arrowhead cell.
        """
        best, key = -1, None
        for pi in range(len(self.pipe_cells)):
            mask = self.pipe_out[pi] if outgoing else self.pipe_in[pi]
            if not mask >> mi & 1:
                continue
            r, c = self.pipe_cells[pi][0 if outgoing else -1]
            k = (abs(r - self.man_r[mi]) + abs(c - self.man_c[mi]), r, c)
            if key is None or k < key:
                best, key = pi, k
        return best

    def halted(self):
        return bool(self.over) or all(
            h or w for h, w in zip(self.man_halt, self.man_wall)
        )

    def run(self, ticks):
        for _ in range(ticks):
            if self.halted():
                return
            self.step()

    def step(self):
        """One tick: pipes shift -> men execute -> men move -> wall check."""
        if self.halted():
            return
        for pi in range(len(self.pipe_cells)):  # phase 1: pipes shift
            mask, vals = self.pipe_mask[pi], self.pipe_vals[pi]
            for i in range(len(vals) - 1, 0, -1):
                if not mask >> i & 1 and mask >> (i - 1) & 1:
                    vals[i] = vals[i - 1]
                    mask ^= 3 << (i - 1)  # set bit i, clear bit i-1
            self.pipe_mask[pi] = mask
        move = [0] * len(self.man_r)
        for mi in range(len(self.man_r)):  # phase 2: round-robin execute
            if self.man_halt[mi] or self.man_wall[mi]:
                continue
            ch = self._at(self.man_r[mi], self.man_c[mi])
            if ch == "H":
                self.man_halt[mi] = 1  # halts this man only, no move
                continue
            if ch in ARROW:
                self.man_h[mi] = ARROW[ch]
            elif ch.isdigit():
                self.man_a[mi] = int(ch)
            elif ch == "M":
                self.man_b[mi] = self.man_a[mi]
            elif ch == "+":
                self.man_a[mi] = wrap64(self.man_a[mi] + self.man_b[mi])
            elif ch == "-":
                self.man_a[mi] = wrap64(self.man_a[mi] - self.man_b[mi])
            elif ch == "X":
                if self.man_a[mi]:
                    turn = 1 if self.man_a[mi] > 0 else -1
                    self.man_h[mi] = (self.man_h[mi] + turn) % 4
            elif ch == "s":
                pi = self._nearest(mi, True)
                if pi < 0 or self.pipe_mask[pi] & 1:
                    continue  # blocked: stays on the s, no move intent
                self.pipe_vals[pi][0] = self.man_a[mi]
                self.pipe_mask[pi] |= 1
            elif ch == "r":
                pi = self._nearest(mi, False)
                last = len(self.pipe_vals[pi]) - 1 if pi >= 0 else 0
                if pi < 0 or not self.pipe_mask[pi] >> last & 1:
                    continue  # blocked: stays on the r, no move intent
                self.man_a[mi] = self.pipe_vals[pi][last]
                self.pipe_mask[pi] &= ~(1 << last)
            move[mi] = 1
        self._advance(move)

    def _advance(self, move):
        """Phases 3+4: apply moves against live occupancy, then wall freeze."""
        occ = {(self.man_r[i], self.man_c[i]): i for i in range(len(move))}
        for mi in range(len(move)):
            if not move[mi] or self.man_halt[mi]:
                continue  # blocked, or halted by a collision this phase
            nr = self.man_r[mi] + DR[self.man_h[mi]]
            nc = self.man_c[mi] + DC[self.man_h[mi]]
            oi = occ.get((nr, nc))
            if oi is not None:  # collision: mover stays put, both halt
                self.man_halt[mi] = 1
                self.man_halt[oi] = 1
                continue
            del occ[(self.man_r[mi], self.man_c[mi])]
            self.man_r[mi], self.man_c[mi] = nr, nc
            occ[(nr, nc)] = mi
        for mi in range(len(move)):  # wall freeze only after the full tick
            if self.man_halt[mi] or self.man_wall[mi]:
                continue
            addr = self.man_r[mi] * 16 + self.man_c[mi]
            if self.wallmask >> addr & 1:
                self.man_wall[mi] = 1
                self.over = 1

    def render(self):
        """The 16x16 display frame as 16 rows of hex digits."""
        frame = [[0] * DISPLAY for _ in range(DISPLAY)]
        for y in range(DISPLAY):
            for x in range(DISPLAY):
                if self.wallmask >> (y * 16 + x) & 1:
                    frame[y][x] = 4
                else:
                    frame[y][x] = _op_color(self.chars[y][x])
        for pi, cells in enumerate(self.pipe_cells):  # pipes override grid
            for i, (r, c) in enumerate(cells):
                if r < DISPLAY and c < DISPLAY:
                    frame[r][c] = 14 if self.pipe_mask[pi] >> i & 1 else 6
        for mi in range(len(self.man_r)):  # men are drawn over everything
            if 0 <= self.man_r[mi] < DISPLAY and 0 <= self.man_c[mi] < DISPLAY:
                frame[self.man_r[mi]][self.man_c[mi]] = 9
        return ["".join(f"{v:x}" for v in row) for row in frame]


def machine_stream(rows: list[str]) -> list[int]:
    """Everything the STEP room consumes, in the order it consumes it.

    stream[0:64]    world: 4 scan-v2 cell tokens per word, token k at bits
                    13k..13k+12. Cell token: bits 0-7 ASCII char (the `@`
                    cell carries 32), bit 8 WALL, bit 9 PADDING. The WALL
                    bit is PATCHED to the true room-border bit: scan v2's
                    left-run heuristic is wrong on 4/14 public LLM cases
                    (side-by-side rooms, the forced addr-0 parking bit,
                    pipe `-` cells right of a border row), so SCAN v3 must
                    implement real border detection. Addr = y*16 + x.
    stream[64:67]   3 man addrs, scan-v2 order (most-recently-found first,
                    i.e. reverse reading order), 0 = absent (a real man
                    can never sit at addr 0: interiors start at y,x >= 1).
    stream[67]      pipe count P (0..2).
    stream[68+8p:76+8p]  pipe p, fixed 8 words:
      word 0:  bits 0-4   length L (1..20)
               bits 5-12  head addr = cells[0], the arrowhead leaving the
                          source room (where `s` writes)
               bits 13-20 tail addr = cells[-1], the arrowhead entering
                          the dest room (where `r` reads)
               bits 21-23 out_mask: bit i set = reading-order man i may
                          `s` into this pipe (his room is the source)
               bits 24-26 in_mask: bit i set = man i may `r` from it
      words 1..7: cell addrs source->dest, 3 per word in 21-bit fields
               (field j of word t = cells[3t+j]), 0-filled past L.

    Total length 68 + 8P. Deterministic in rows. Contract: SCAN must EMIT
    exactly this stream; STEP must CONSUME it and nothing else.
    """
    width = max(len(r) for r in rows)
    grid = [list(r.ljust(width)) for r in rows]
    tokens = [width, len(rows)] + [ord(ch) for row in grid for ch in row]
    v2 = scan_reference_v2(tokens)
    cells, men = v2[:256], v2[256 : 256 + MEN]
    rooms = find_rooms(grid)
    for addr in range(256):
        y, x = divmod(addr, 16)
        cells[addr] &= ~WALL_BIT
        if any(_on_border(rm, y, x) for rm in rooms):
            cells[addr] |= WALL_BIT
    world = [
        sum(cells[base + k] << (FIELD * k) for k in range(4))
        for base in range(0, 256, 4)
    ]
    man_rooms = [  # reading order, matching LockstepLLM man indices
        next(
            i
            for i, rm in enumerate(rooms)
            if rm[0] < a // 16 < rm[2] and rm[1] < a % 16 < rm[3]
        )
        for a in reversed(men)
        if a
    ]
    return world + men + _pipe_block(grid, rooms, man_rooms)


def _pipe_block(grid, rooms, man_rooms):
    """[count] then one fixed-width descriptor per discovered pipe."""
    pipes = find_pipes(grid, rooms)
    out = [len(pipes)]
    for cells, src, dst in pipes:
        addrs = [r * 16 + c for r, c in cells]
        out_mask = sum(1 << i for i, rm in enumerate(man_rooms) if rm == src)
        in_mask = sum(1 << i for i, rm in enumerate(man_rooms) if rm == dst)
        out.append(
            len(addrs)
            | addrs[0] << 5
            | addrs[-1] << 13
            | out_mask << 21
            | in_mask << 24
        )
        for base in range(0, 21, 3):
            word = 0
            for k in range(3):
                if base + k < len(addrs):
                    word |= addrs[base + k] << (CELL_FIELD * k)
            out.append(word)
    return out


def _op_color(ch):
    if ch in "<>^vXH":
        return 3
    if ch.isdigit():
        return 8
    if ch == "M":
        return 12
    if ch in "+-":
        return 10
    if ch in "sr":
        return 13
    return 0
