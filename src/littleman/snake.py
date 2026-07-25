"""Snake (slug ``snake``): reference simulator + machine design.

Problem recap
-------------
Simulate Snake on a 16x16 grid and draw it on a 16x16 LM-75 display, in
rounds.  Round 1 is ``sx sy`` (head cell, direction right) and commits a
frame.  Later rounds are ``1 fx fy`` (fruit spawn: commit a frame, no
tick), ``2/3/4/5`` (direction up/right/down/left: no frame, no tick) or
``0`` (tick: commit a frame).  Scoring is footprint-tick, tickCap 15e6.

:func:`simulate` below is a pure-Python reference; it reproduces every
expected frame of all five public cases (see ``tests/test_snake.py``).
The rest of this docstring is the machine design, worked out to the
instruction level; ``build()`` is not implemented yet.

===========================================================================
VERIFIED FACT THAT CHANGES MACHINE DESIGN
===========================================================================
``docs/littleman-cookbook.md`` section 1 claims "B is DESTROYED by:
M W + - * / % N & | ~ { }".  That is WRONG for everything except
``M``, ``W`` and ``/``.  In ``littleman.sim`` the arithmetic and bitwise
ops write only A; and the server agrees, proven by experiment:

    submissions/brackets/brackets_00.man scores 26/26 live, and locally
    passes 9/9; monkey-patching Machine._execute to zero B after every
    "+-*%N&|~{}" drops it to 3/9.

So a machine that relies on B surviving arithmetic still works on the
server.  This matters a lot here: a room can hold one value in B and
compare it against a whole stream (``r x`` then ``-`` leaves B intact),
which removes any need to duplicate the comparand into the ring.

===========================================================================
STATE REPRESENTATION
===========================================================================
Cell code ``c = 16*y + x + 1`` (so 1..256; 0 and negatives are free for
markers).  One ring (a FIFO loop through pipes) holds the whole state as
a packet, in this fixed order:

    [DR, ROW, DC, COL, FCODE, b1, b2, ..., bL, MARK]

* DR, DC in {-1,0,1}  - direction row/col deltas (raw, never sign-tested)
* ROW, COL            - head position, 0..15
* FCODE               - fruit cell code, or 0 when there is no fruit
* b1..bL              - body cell codes, **head first, tail last**
* MARK = -1           - terminator; every body value is >= 1, so a body
                        relay loop is a clean two-way sign test (0 never
                        occurs, so no three-way X merge is needed)

Head-first storage is the key choice: the new head is *prepended* (the
controller knows it before the body streams by) and the tail is the
*last* item, so the tail can be dropped at the end of a pass, by which
time the self-collision verdict is known.  Tail-first storage forces
either a second lap or a parking pipe.

===========================================================================
ROOMS AND PIPE TOPOLOGY
===========================================================================
The ring is a cycle of rooms; the controller has exactly ONE incoming
and ONE outgoing pipe, which removes every nearest-pipe audit from the
big room (cookbook section 4 is the usual source of bugs):

    I -> READER -> [serpentine] -> CTRL -> TAP -> READER   (ring)
                                            \\-> ADDRDRV -> DATADRV -> SWAPDRV
                                                 |            |          |
                                                ADDR         DATA       SWAP
                                                     (LM-75 16x16)

* CTRL   - one man, one in, one out.  All logic lives here.
* TAP    - pulls display tokens out of the ring and feeds the driver
           chain; relays everything else.  1 in, 2 out.
* READER - relays the packet; when the controller asks for input, reads
           one value from I and injects it into the ring.  2 in, 1 out.
* driver chain - copy of ``littleman.plotter`` (proven): ADDRDRV sends
           ADDR and forwards, DATADRV sends DATA and forwards, SWAPDRV
           sends SWAP.  Each room is 1 in / 2 out.

Ring capacity must exceed the packet length (else the cycle deadlocks
with every man blocked on send).  L can reach ~50 (100 rounds, 2 rounds
per fruit), so budget >= 70 cells of pipe, as a serpentine in dead space
(``littleman.memory.build_memory`` shows the pattern).

Wire protocols
--------------
CTRL -> TAP, in-band on the ring:

    -5, cell, color   pixel: TAP computes cell*16 + color and sends the
                      token down the driver chain
    -6                commit: TAP sends token 0
    -1                MARK (relayed)
    -2 / -3           "send me an input value" / "no input wanted"
                      (relayed to READER, which consumes it)

TAP dispatch, given a value x: ``M`` (B=x); ``X`` on A: >=0 relay.  Else
load 5, ``+`` -> A = x+5: ==0 pixel, <0 commit (x=-6), >0 relay after
``W`` restores A=x.  Driver-chain token = cell*16 + color, 0 = commit,
exactly the ``littleman.plotter`` protocol with a variable colour.

READER: relay until MARK, relay the MARK, then read the control value:
-2 -> read I, emit that value; -3 -> emit nothing.  Loop.

===========================================================================
CONTROLLER PASSES
===========================================================================
Every pass reads the packet once and re-emits it.  ``r``/``s`` are ring
ops; B survives both, so one value can be carried across a whole pass.
Each pass ends by emitting MARK then the control value (-2 when the next
thing the controller wants is an input word, -3 otherwise).

INIT (runs once, at startup; input is ``sx sy``)
    r sx; s (park sx in the ring - it is empty, so it just comes back);
    s again (park a second copy); r sy; M (B=sy)
    0 s          -> DR = 0
    W  s         -> ROW = sy      (A=sy, B=0)
    1 s          -> DC = 1
    r  s         -> COL = sx      (first parked copy)
    `16` * M     -> B = 16*sy     (A=sx*... see note)  [see note 1]
    0 s          -> FCODE = 0
    r  + M 1 +   -> A = 16*sy + sx + 1 = hcode        (second copy)
    M s          -> b1 = hcode, B = hcode
    1 N s        -> MARK
    W s(-5) ...  -> pixel token (hcode, 10); then -6 commit; then -2
    note 1: with A=sx, B=sy, ``16`` loads A=16 leaving B=sy, ``*`` gives
    A=16*sy with B untouched, ``M`` parks it in B.

DISPATCH (between rounds; the input word is delivered by READER as the
last value of the previous pass, so the controller reads it with a plain
``r`` after the MARK)
    Binary tree on c in {0,1,2,3,4,5} using three X tests:
        c-2:  <0 -> {0,1}   =0 -> DIR-UP    >0 -> {3,4,5}
        c-1:  <0 -> TICK    =0 -> FRUIT
        c-4:  <0 -> DIR-RIGHT  =0 -> DIR-DOWN  >0 -> DIR-LEFT

DIR (four near-identical corridors, ~14 cells each)
    r (drop DR); <lit> s; r s (ROW); r (drop DC); <lit> s; r s (COL);
    r s (FCODE); relay body; MARK; -3? no: -2 (next round wants input).
    Literals: up (-1,0) right (0,1) down (1,0) left (0,-1); -1 is ``1 N``.

FRUIT (two passes; the dispatcher has already read fx into the ring)
    dispatch tail: r fx; s (park fx after the MARK); r fy; M; `16`; *;
                   M   -> B = 16*fy
    F1: relay DR ROW DC COL FCODE and the whole body, emit MARK, then
        r (the parked fx) ; + ; M ; 1 ; + -> A = fcode ; M (B=fcode) ;
        emit -3 (no input yet).
    F2: relay DR ROW DC COL; r (drop old FCODE); W; s (FCODE=fcode); M;
        relay body; MARK; then W -> A=fcode; pixel token (fcode, 9);
        commit -6; control -2.

TICK pass A - move and bounds check
    r s M           DR      (B = dr)
    r + s           ROW  <- nrow = row+dr, emitted
    M `16` W - X    nrow-16: ==0 -> OOB (up), <0 -> ok    [>0 impossible]
    + M 1 + X       nrow+1:  ==0 -> OOB, >0 -> ok
    r s M           DC      (B = dc)
    r + s           COL  <- ncol, emitted
    ...same two checks on ncol...
    relay FCODE, body, MARK; control -3.
    OOB exits jump to a corridor that finishes relaying this pass and
    then runs DEAD.  Two such corridors are needed (one for a row-check
    exit, which still has DC/COL/FCODE to relay, one for a col-check
    exit).  The bogus ROW/COL values written before the exit are
    harmless: the case ends.

TICK pass B - head cell, eat test, prepend, self-collision scan
    r s             DR
    r s M `16` * M  ROW: B = 16*nrow
    r s             DC
    r s + M 1 +     COL: A = 16*nrow + ncol + 1 = n
    M               B = n
    r - X           FCODE - n:  ==0 EAT, else MOVE
  EAT:  0 s         FCODE <- 0
        W M s       prepend n (A=n, B=n)
        relay body; MARK; W -> A=n; pixel (n,10); commit -6; ctl -2.
        (No scan: fruit only ever spawns on an empty cell, so eating
        can never collide, and the tail must stay put.)
  MOVE: + s         FCODE restored (A was FCODE-n, B=n) and re-emitted
        W s M       prepend n, keep B = n
        pixel (n,10) may be emitted here already: if the scan later
        finds a hit, DEAD repaints that same cell red, so it is safe.
        SCAN loop, B = n throughout:
            r  X   x<0 -> MARK -> LEGAL (emit MARK)
               s   emit x
               -   A = x-n  (B still n!)
               X   ==0 -> PENDING, else loop
        PENDING (the previous item matched; it is legal only if it was
        the tail, i.e. only if the MARK comes next):
            r  X   x<0 -> MARK -> LEGAL
               s   emit x -> HIT: relay the rest, then DEAD
        LEGAL -> pass C.  HIT -> DEAD (the body still holds every cell
        plus a duplicate n, so the red repaint draws exactly the correct
        pre-tick body).

TICK pass C - drop the tail, finish the frame
    relay DR ROW DC COL FCODE
    r M                       B = b1
    loop: r X   x<0 -> MARK: s (emit MARK); W -> A = tail;
                     pixel (tail, 0); commit -6; control -2; done
                else: W s W M  (emit the held item, hold x)  and loop
    One-item lookahead: the item is only emitted once a successor is
    seen, so the last item (the tail) is dropped.

DEAD - repaint the body red and park
    relay DR ROW DC COL FCODE
    loop: r X   x<0 -> MARK: s; commit -6; control -3; park on ``r``
                else: s (relay) and pixel (x, 9)
    After the losing frame the judge sends nothing more, so parking on a
    blocking ``r`` forever is correct and free (cookbook section 9).

===========================================================================
CORRECTNESS NOTES (the traps this design is built around)
===========================================================================
* The tail moves before the head, so moving into the cell the tail just
  vacated is legal.  Here that falls out for free: a match on the LAST
  body item is legal, a match on any earlier item is a loss.  The
  "PENDING" corridor is the one-item delay that distinguishes them, and
  it costs no register - the man's position IS the flag.
* A direction change commits NO frame; only INIT, fruit spawn and tick
  rounds do.  The round controller withholds the next round's input
  until the current round's frames commit, so direction rounds arrive
  batched with the following round - the controller must not assume one
  input word per frame.
* The losing frame is the PRE-tick body in red.  The design never
  removes anything from the body before the verdict is known, and a
  speculative green pixel for the new head is safe because the red
  repaint overwrites it before the commit.
* Fruit is red 9, snake green 10, dead snake red 9, everything else 0.
  Incremental drawing (2-3 pixels per frame, SWAP=1 keeping the buffer)
  is far cheaper than redrawing 256 pixels; a losing frame costs L
  pixels once.
* Never emit an integer to an output room: frame-judged problems fail on
  any integer output.  This machine has no O room at all.

===========================================================================
BEFORE SUBMITTING (gates)
===========================================================================
* ``littleman.server_compat.validate_layout(text)`` - no shared walls.
* ``littleman.alexey_pipecheck.check(text)`` - no pipe shorter than 2.
* ``littleman.server_compat.judge_problem(text, problem)`` - never a bare
  ``Machine.run``: a server machine never halts and would burn the cap.
"""

from __future__ import annotations

from .canvas import Canvas

W = 16
H = 16
GREEN = 10
RED = 9

# direction code -> (dx, dy); codes come straight from the input alphabet.
DIRS = {2: (0, -1), 3: (1, 0), 4: (0, 1), 5: (-1, 0)}


def cell_code(x: int, y: int) -> int:
    """Ring encoding of a grid cell: 1..256, leaving 0/negatives free."""
    return 16 * y + x + 1


def render(body, fruit, over):
    """Render one frame: ``body`` is a list of (x, y), tail first."""
    grid = [[0] * W for _ in range(H)]
    color = RED if over else GREEN
    for x, y in body:
        grid[y][x] = color
    if fruit is not None:
        grid[fruit[1]][fruit[0]] = RED
    return ["".join("%x" % v for v in row) for row in grid]


def simulate(rounds):
    """Replay a test case's rounds, returning the list of committed frames.

    ``rounds`` is a list of round dicts (as in ``publicTestData``); only the
    ``in`` values are used.  Validated against all five public cases.
    """
    values = []
    for rd in rounds:
        values.extend(int(v) for v in rd["in"])

    frames = []
    idx = 0
    sx, sy = values[idx], values[idx + 1]
    idx += 2
    body = [(sx, sy)]  # tail first, head last
    direction = 3  # right
    fruit = None
    over = False
    frames.append(render(body, fruit, over))

    while idx < len(values) and not over:
        cmd = values[idx]
        idx += 1
        if cmd == 1:
            fruit = (values[idx], values[idx + 1])
            idx += 2
            frames.append(render(body, fruit, over))
        elif cmd in DIRS:
            direction = cmd
            # no tick, no frame
        elif cmd == 0:
            dx, dy = DIRS[direction]
            hx, hy = body[-1]
            nx, ny = hx + dx, hy + dy
            if not (0 <= nx < W and 0 <= ny < H):
                over = True
            elif fruit is not None and (nx, ny) == fruit:
                body.append((nx, ny))  # grow: tail stays put
                fruit = None
            else:
                occupied = set(body[1:])  # tail moves before the head
                if (nx, ny) in occupied:
                    over = True
                else:
                    body.pop(0)
                    body.append((nx, ny))
            frames.append(render(body, fruit, over))
        else:
            raise ValueError("unknown round command %r" % cmd)
    return frames


# ---------------------------------------------------------------------------
# Validated building blocks for the controller (see the design above).
# ---------------------------------------------------------------------------


class Box:
    """Cell-level room builder that refuses conflicting overwrites.

    Corridor layout is where these machines actually break: two code paths
    silently sharing a cell is a bug that only shows up as a wrong value ten
    thousand ticks later.  ``put`` asserts instead.
    """

    def __init__(self):
        self.cells: dict[tuple[int, int], str] = {}

    def put(self, row: int, col: int, text: str, vertical: bool = False):
        for i, ch in enumerate(text):
            pos = (row + i, col) if vertical else (row, col + i)
            old = self.cells.get(pos)
            if old is not None and old != ch:
                raise ValueError("cell conflict at %r: %r vs %r" % (pos, old, ch))
            self.cells[pos] = ch
        return self

    def room(self) -> list[str]:
        """Wrap the placed cells in ``+``/``-``/``|`` walls."""
        height = max(r for r, _ in self.cells) + 1
        width = max(c for _, c in self.cells) + 1
        rows = []
        for r in range(height + 1):
            line = []
            for c in range(width + 1):
                if r in (0, height) and c in (0, width):
                    line.append("+")
                elif r in (0, height):
                    line.append("-")
                elif c in (0, width):
                    line.append("|")
                else:
                    line.append(self.cells.get((r, c), " "))
            rows.append("".join(line))
        return rows


def build_row_pass_room() -> list[str]:
    """One validated controller pass: the row half of TICK pass A.

    Reads ``[DR, ROW, rest..., MARK]`` from its single incoming pipe and
    writes ``[DR, ROW+DR, rest..., MARK, -3]`` to its single outgoing pipe,
    or bails out with ``-9`` when ``ROW+DR`` leaves 0..15.

    Three idioms the whole Snake design rests on are exercised here:

    * ``M `16` W - X``  upper-bound test.  A = nrow-16 is <=0 for every
      reachable nrow, so the X is a clean two-way branch (==0 out of bounds,
      <0 fine) with no three-way merge.  The following ``+`` restores
      A = nrow **because B is still 16** - arithmetic does not clobber B.
    * ``M 1 + X``  lower-bound test, likewise two-way (==0 means nrow=-1).
    * ``> r s X`` + a loop-back row: relay until the negative MARK.  Body
      values are cell codes >= 1, so 0 never reaches the X.
    """
    box = Box()
    # row 3: DR (relay + park in B), ROW+DR emitted, then nrow-16 test
    box.put(3, 1, ">@rsMr+sM`16`W-X")          # X at col 16
    box.put(3, 17, "vv", vertical=True)        # out-of-bounds: drop to row 5
    box.put(5, 17, ">")
    box.put(5, 18, "        9NsH")
    box.put(2, 16, ">")                        # in bounds: turn east on row 2
    # row 2: restore A=nrow, then the nrow+1 test
    box.put(2, 17, "+M1+X")                    # X at col 21
    box.put(2, 22, "^")                        # out of bounds: up and over
    box.put(1, 22, ">")
    box.put(1, 23, "              v")
    box.put(4, 37, ">")
    box.put(4, 38, "9NsH")
    box.put(3, 21, ">")                        # in bounds: back down to row 3
    # row 3: relay the rest of the packet, then emit the -3 control word
    box.put(3, 22, "  >rsX")                   # entry '>' col 24, X col 27
    box.put(4, 24, "^  <")                     # loop back to the entry
    box.put(2, 27, ">")
    box.put(2, 28, "3NsH")
    return box.room()


def build_row_pass_rig() -> str:
    """``I -> build_row_pass_room() -> O``: harness for the pass above."""
    canvas = Canvas()
    room = build_row_pass_room()
    canvas.put(0, 6, room)
    bottom = len(room) - 1
    canvas.put(2, 0, ["+-+", "|I|", "+-+"])
    canvas.pipe([(3, 3), (3, 5)])                     # I -> room, left wall
    canvas.put(bottom + 3, 6, ["+-+", "|O|", "+-+"])
    canvas.pipe([(bottom + 1, 8), (bottom + 2, 8)])   # room bottom -> O
    return canvas.render()


# ---------------------------------------------------------------------------
# Station-cycle protocol model (the machine's blueprint, executable).
#
# Ring cycle: IN -> TICKA -> TICKB -> TICKC -> DRAW -> IN.  One state packet
# circulates; each station acts when the packet's MODE is in its act-set and
# relays otherwise.  Display tokens leave DRAW for the ADDR/DATA/SWAP driver
# chain.  Verdicts discovered mid-packet are carried in the acting man's BP
# across one extra rotation (modes 2->3 and 6->7), because MODE is emitted
# before the data that decides it arrives.
#
# Packet layouts (MARK = -1 terminates; body is head-first, cell codes 1..256):
#   standard    [mode, DR, ROW, DC, COL, FC, b1..bL, -1]
#   mode 4      [4, fy, fx, DR, ROW, DC, COL, FC, body..., -1]   fruit spawn
#   mode 5      [5, sy, sx, -1]                                  init build
#   mode 10/11  [mode, M2, DR, ROW, DC, COL, FC, body..., -1, P, C]
#               pixel request as TRAILERS after MARK (P = cell code, C =
#               color); 10 commits the frame after the pixel, 11 does not.
#               M2 = mode to stamp on the packet after drawing.
#
# MODES: 1 IN-dispatch; 2 TICKA bounds-check (flag); 3 TICKA apply/route;
# 4 TICKA fruit-apply; 5 TICKA init-build; 6 TICKB eat/scan (flag);
# 7 TICKB apply; 8 TICKC tail-drop; 9 DRAW dead-sweep; 10 pixel+commit;
# 11 pixel, no commit; 12 repaint-head+commit.  Mode 12 fixes the
# tail-into-vacated-cell frame: TICKC erases the tail first (mode 11 with
# M2=12), then DRAW repaints body[0] green and commits, so a head landing
# on the old tail cell ends green, not black.
# Act-sets: IN {1}; TICKA {2,3,4,5}; TICKB {6,7}; TICKC {8}; DRAW {9..12}.
# Mode numbering is chosen so every station's X-test chain is monotone.
# The only trailered mode any station relays is 10 (TICKB and TICKC check
# for it after the MARK); mode 11 travels only TICKC->DRAW, adjacent.
# Generic relay corridors count SIX values after the mode: for standard
# packets that is DR ROW DC COL FC b1 (b1 >= 1 always exists), for
# trailered ones M2 DR ROW DC COL FC -- either way the following sign
# loop only ever sees body values (>= 1) and the MARK, never a 0.
# ---------------------------------------------------------------------------

MARK = -1


class CycleModel:
    """Packet-level model of the machine.  Mirrors, station by station,
    exactly what the littleman rooms will do -- used to validate the design
    against :func:`simulate` and to generate per-station test vectors."""

    def __init__(self, values):
        self.inputs = list(values)  # flat input word stream
        self.tokens = []  # driver-chain tokens ((cell-1)*16+color+1, or -1)
        self.frames = []
        self.next_buf = [[0] * W for _ in range(H)]
        self.flag_a = 0  # TICKA's BP between modes 2 and 3
        self.flag_b = 0  # TICKB's BP between modes 6 and 7
        self.trace = []  # (station, packet-in, packet-out) triples

    # -- display / driver chain ------------------------------------------
    def _token(self, cell, color):
        self.tokens.append((cell - 1) * 16 + color + 1)
        self.next_buf[(cell - 1) // 16][(cell - 1) % 16] = color

    def _commit(self):
        self.tokens.append(-1)
        self.frames.append(["".join("%x" % v for v in row) for row in self.next_buf])

    # -- stations ---------------------------------------------------------
    def station_in(self, p):
        assert p[0] == 1
        c = self.inputs.pop(0)
        hdr, rest = p[1:6], p[6:]
        if c == 0:
            return [2, *hdr, *rest]
        if c == 1:
            fx = self.inputs.pop(0)
            fy = self.inputs.pop(0)
            return [4, fy, fx, *hdr, *rest]
        dr, dc = {2: (-1, 0), 3: (0, 1), 4: (1, 0), 5: (0, -1)}[c]
        _, row, _, col, fc = hdr
        return [1, dr, row, dc, col, fc, *rest]

    def station_ticka(self, p):
        m = p[0]
        if m == 2:  # bounds check: flag only, packet unchanged but mode
            dr, row, dc, col = p[1], p[2], p[3], p[4]
            self.flag_a = 0 if (0 <= row + dr < H and 0 <= col + dc < W) else 1
            return [3, *p[1:]]
        if m == 3:
            dr, row, dc, col = p[1], p[2], p[3], p[4]
            if self.flag_a:
                return [9, *p[1:]]
            return [6, dr, row + dr, dc, col + dc, *p[5:]]
        if m == 4:  # fruit apply: [4, fy, fx, hdr..., body, -1]
            fy, fx = p[1], p[2]
            fcode = 16 * fy + fx + 1
            hdr, rest = p[3:8], p[8:]
            hdr[4] = fcode
            return [10, 1, *hdr, *rest, fcode, 9]
        if m == 5:  # init build: [5, sy, sx, -1]
            sy, sx = p[1], p[2]
            h = 16 * sy + sx + 1
            return [10, 1, 0, sy, 1, sx, 0, h, MARK, h, GREEN]
        raise AssertionError(m)

    def station_tickb(self, p):
        m = p[0]
        if m == 6:  # eat / self-collision scan; ROW,COL already moved
            row, col, fc = p[2], p[4], p[5]
            n = 16 * row + col + 1
            body = p[6:-1]
            if fc == n:
                self.flag_b = 2
            else:
                hit = any(b == n for b in body[:-1])  # tail cell is legal
                self.flag_b = 1 if hit else 0
            return [7, *p[1:]]
        if m == 7:
            row, col, fc = p[2], p[4], p[5]
            n = 16 * row + col + 1
            hdr4, body = p[1:5], p[6:-1]
            if self.flag_b == 1:  # collision
                return [9, *p[1:]]
            if self.flag_b == 2:  # eat: clear FC, prepend, draw+commit
                return [10, 1, *hdr4, 0, n, *body, MARK, n, GREEN]
            return [8, *hdr4, fc, n, *body, MARK]
        raise AssertionError(m)

    def station_tickc(self, p):
        assert p[0] == 8
        hdr, body = p[1:6], p[6:-1]
        tail = body[-1]
        return [11, 12, *hdr, *body[:-1], MARK, tail, 0]

    def station_draw(self, p):
        m = p[0]
        if m == 9:  # dead sweep: body red, commit, park via mode 1
            for b in p[6:-1]:
                self._token(b, RED)
            self._commit()
            return [1, *p[1:]]
        if m in (10, 11):
            m2 = p[1]
            pix_p, pix_c = p[-2], p[-1]
            self._token(pix_p, pix_c)
            if m == 10:
                self._commit()
            return [m2, *p[2:-2]]
        if m == 12:  # repaint head (first body item) green, commit
            self._token(p[6], GREEN)
            self._commit()
            return [1, *p[1:]]
        raise AssertionError(m)

    OWNERS = {
        1: "station_in", 2: "station_ticka", 3: "station_ticka",
        4: "station_ticka", 5: "station_ticka", 6: "station_tickb",
        7: "station_tickb", 8: "station_tickc", 9: "station_draw",
        10: "station_draw", 11: "station_draw", 12: "station_draw",
    }

    def run(self, max_steps=100000):
        """Prologue emits [5, sy, sx, -1]; then route by mode until IN would
        block on an empty input stream (the parked steady state)."""
        sx = self.inputs.pop(0)
        sy = self.inputs.pop(0)
        packet = [5, sy, sx, MARK]
        for _ in range(max_steps):
            if packet[0] == 1 and not self.inputs:
                return packet  # parked on the input r
            name = self.OWNERS[packet[0]]
            before = list(packet)
            packet = getattr(self, name)(packet)
            self.trace.append((name, before, list(packet)))
        raise AssertionError("model did not park")


def run_model(rounds):
    """Frames produced by the station-cycle model for a test case."""
    values = [int(v) for rd in rounds for v in rd["in"]]
    model = CycleModel(values)
    model.run()
    return model.frames


# ---------------------------------------------------------------------------
# Station rooms.  Shared conventions (see CycleModel for the protocol):
#   * ring-in on the LEFT wall row 2, ring-out on the RIGHT wall row 2 --
#     one in, one out, so every r/s resolves without audits (except IN and
#     DRAW, which have a second pipe and are audited in tests).
#   * entry at (2,1) '>' (2,2) '@' (2,3) 'r'; X-test chain eastward.
#     Dispatch tests are monotone in the mode number, so the ccw (A<0)
#     branch only ever fires for modes below the first test, which are
#     routed via the catch row 1 down the col-2 bypass (over the '@', a
#     nop) to the relay corridor; the cw (A>0) branch drops straight down
#     the test column to the same merge '>' -- both restore A with '+'.
#   * relay corridor: '+ M s' (restore mode, hold it in B, emit), '4b' +
#     a BP relay loop for the 5 header values, then a sign relay loop for
#     the body, MARK, and (where mode 10 can pass) a trailer check using
#     the mode held in B.
#   * home: every corridor ends on the bottom row heading west, up col 1,
#     back into (2,1).
# ---------------------------------------------------------------------------


def build_tickc() -> list[str]:
    """TICKC (act mode 8): drop the tail, request its erase.

    [8, DR, ROW, DC, COL, FC, b1..bL, -1]
      -> [11, 12, DR, ROW, DC, COL, FC, b1..b(L-1), -1, tail, 0]
    Relays modes {1, 3, 7} (ccw side) and {9, 10, 12} (cw side); mode 10
    carries two trailers, checked for after the MARK.
    """
    b = Box()
    cells = {
        (1, 2): "v", (1, 8): "<",
        (2, 1): ">", (2, 2): "@", (2, 3): "r", (2, 4): "M", (2, 5): "8",
        (2, 6): "W", (2, 7): "-", (2, 8): "X",
        # act corridor: emit 11 then 12, relay 5 header values
        (2, 9): "`", (2, 10): "1", (2, 11): "1", (2, 12): "`", (2, 13): "s",
        (2, 14): "M", (2, 15): "1", (2, 16): "+", (2, 17): "s",
        (2, 18): "4", (2, 19): "b",
        (2, 20): ">", (2, 21): "r", (2, 22): "s", (2, 23): "v",
        (3, 20): "^", (3, 22): "m", (3, 23): "d",
        # act body: one-item lookahead; MARK exit emits [-1, tail, 0]
        (3, 31): ">", (3, 32): "s", (3, 33): "W", (3, 34): "s", (3, 35): "0",
        (3, 36): "s", (3, 37): "v",
        (4, 23): ">", (4, 24): "r", (4, 25): "M", (4, 26): ">",
        (4, 29): ">", (4, 30): "r", (4, 31): "X",
        (6, 26): "^", (6, 27): "M", (6, 28): "W", (6, 29): "s", (6, 30): "W",
        (6, 31): "<",
        # relay corridor (merge of both non-act branches)
        (7, 2): ">", (7, 8): ">", (7, 9): "+", (7, 10): "M", (7, 11): "s",
        (7, 12): "5", (7, 13): "b",
        (7, 14): ">", (7, 15): "r", (7, 16): "s", (7, 17): "v",
        (8, 14): "^", (8, 16): "m", (8, 17): "d",
        # relay body loop; the loop's own s already emitted the MARK, so
        # the exit chain must not re-send it -- W just recovers A = mode.
        (8, 20): ">", (8, 21): "W", (8, 22): "M", (8, 23): "9", (8, 24): "W",
        (8, 25): "-", (8, 26): "M", (8, 27): "1", (8, 28): "W", (8, 29): "-",
        (8, 30): "X",
        (8, 31): "r", (8, 32): "s", (8, 33): "r", (8, 34): "s", (8, 35): "v",
        (9, 17): ">", (9, 18): "r", (9, 19): "s", (9, 20): "X",
        (10, 17): "^", (10, 20): "<",
        (7, 30): ">", (7, 45): "v",
        (11, 1): "^", (11, 30): "<", (11, 35): "<", (11, 37): "<",
        (11, 45): "<",
    }
    for (r, c), ch in cells.items():
        b.put(r, c, ch)
    b.put(11, 44, " ")  # ensure interior width through col 45
    return b.room()


def build_station_rig(room_rows: list[str]) -> str:
    """``I -> station -> O`` harness: ring-in left row 2, ring-out right row 2."""
    canvas = Canvas()
    canvas.put(0, 6, room_rows)
    width = len(room_rows[0])
    canvas.put(1, 0, ["+-+", "|I|", "+-+"])
    canvas.pipe([(2, 3), (2, 5)])
    canvas.put(1, 6 + width + 3, ["+-+", "|O|", "+-+"])
    canvas.pipe([(2, 6 + width), (2, 6 + width + 2)])
    return canvas.render()


def build_draw() -> list[str]:
    """DRAW (act modes 9-12), 1-in/1-out.

    Display tokens are emitted IN-BAND on the ring as -(t+10) -- pixel
    t = 16*(P-1)+C+1 in 1..4096 encodes to -11..-4106, commit t=-1 to -9;
    every real ring value is >= -1, so TOKENSPLIT can separate them with
    one sign test.  This keeps DRAW single-pipe and audit-free.

      9: [9, hdr5, body, -1]        -> [1, hdr5, body, -1] + red sweep + commit
     10: [10, M2, hdr5, body, -1, P, C] -> [M2, hdr5, body, -1] + pixel + commit
     11: same as 10 without the commit token
     12: [12, hdr5, b1.., -1]      -> [1, hdr5, b1.., -1] + (b1, green) + commit
    Relays modes {1, 3, 7} (all below 9, ccw side of the first test).
    """
    b = Box()
    cells = {}

    def put(r, c, text):
        for i, ch in enumerate(text):
            if ch != "~":
                cells[(r, c + i)] = ch

    # dispatch chain: X at (2,8), (5,13), (8,18), (11,23)
    put(2, 1, ">@rM9W-X")
    put(5, 8, ">M1W-X")
    put(8, 13, ">M1W-X")
    put(11, 18, ">M1W-X")
    # ccw catch (modes 1,3,7) -> col 2 bypass -> relay corridor row 14
    put(1, 2, "v"); put(1, 8, "<")
    put(14, 2, ">+Ms5b>rsv")
    put(15, 8, "^ md")
    put(16, 11, ">^")
    put(15, 12, ">rsX")
    put(16, 13, "~~<")   # (16,15) '<'
    put(14, 15, ">")     # MARK exit (already relayed by loop s)
    put(14, 70, "v")
    # SWEEP (mode 9), rows 2-4: emit mode 1, relay 5, per-item token loop
    put(2, 9, "1s4b>rsv")
    put(3, 13, "^ md")
    put(4, 16, "> ^")                 # relay exit joins the loop's return col
    put(3, 18, ">                 >rX")   # return east run; loop head at 36
    # chain row 4, executed right-to-left (W): s M 1 W - M `16` * M `21` + N s
    put(4, 18, "^sN+`02`M*`61`M-W1Ms<")  # W-walked: s M 1 W - M `16` * M `20` + N s
    put(2, 38, ">s9Ns")               # MARK exit: send MARK, commit -9
    put(2, 66, "v")
    # PC (mode 10), rows 5-7: M2, relay 5, body loop, trailer pixel, commit
    put(5, 14, "rs4b>rsv")
    put(6, 18, "^ md")
    put(7, 21, ">^")
    put(6, 22, ">rsX")
    put(7, 25, "<")
    put(5, 25, ">rM1W-M`16`*Mr+M`11`+Ns9Ns")
    put(5, 67, "v")
    # PIX (mode 11), rows 8-10: same as PC minus commit
    put(8, 19, "rs4b>rsv")
    put(9, 23, "^ md")
    put(10, 26, ">^")
    put(9, 27, ">rsX")
    put(10, 30, "<")
    put(8, 30, ">rM1W-M`16`*Mr+M`11`+Ns")
    put(8, 68, "v")
    # RP (mode 12), rows 11-13: emit 1, relay 5, hold b1 in B, repaint+commit
    put(11, 24, "1s4b>rsv")
    put(12, 28, "^ md")
    put(13, 31, ">rsM^")
    put(12, 35, ">rsX")
    put(13, 36, "~~<")   # (13,38) '<'
    put(11, 38, ">WM1W-M`16`*M`21`+Ns9Ns")
    put(11, 69, "v")
    # home row 17, return col 1
    put(17, 66, "<<<<<")
    put(17, 1, "^")

    for (r, c), ch in cells.items():
        b.put(r, c, ch)
    b.put(1, 70, " ")  # width through col 70
    return b.room()


def build_tokensplit() -> list[str]:
    """TOKENSPLIT: ring values (>= -1) forward to the ring; encoded tokens
    (<= -9) decode to t = -v-10 and leave on the token pipe (top wall)."""
    b = Box()
    for (r, c), ch in {
        # token branch arrives with A = v+2 (the sign test added 2), so
        # decode t = -(v+2) - 8 = -v - 10.
        (1, 7): ">", (1, 8): "N", (1, 9): "M", (1, 10): "8", (1, 11): "W",
        (1, 12): "-", (1, 13): "s", (1, 14): "v",
        (2, 1): ">", (2, 2): "@", (2, 3): "r", (2, 4): "M", (2, 5): "2",
        (2, 6): "+", (2, 7): "X",
        (3, 7): "W", (4, 7): "s",
        (5, 7): "<", (5, 14): "<", (5, 1): "^",
    }.items():
        b.put(r, c, ch)
    return b.room()


def build_addrdrv() -> list[str]:
    """ADDR driver: forward every token, send addr=(t-1)/16 for t>0."""
    b = Box()
    for (r, c), ch in {
        # The home run is 8 ticks longer than strictly needed (the eastward
        # detour to col 22) so ADDRDRV's lap (46) exceeds DATADRV's (40):
        # the chain is then rate-limited by ADDR and the per-pixel DATA lag
        # stays constant instead of growing 2 ticks per pixel until DATA
        # slips past the next pixel's ADDR.
        (1, 1): "v", (1, 5): "<", (1, 22): "<",
        (2, 1): ">", (2, 2): "@", (2, 3): "r", (2, 4): "s", (2, 5): "X",
        (3, 5): ">", (3, 6): "M", (3, 7): "1", (3, 8): "W", (3, 9): "-",
        (3, 10): "M", (3, 11): "`", (3, 12): "1", (3, 13): "6", (3, 14): "`",
        (3, 15): "W", (3, 16): "/", (3, 17): "s", (3, 18): ">", (3, 22): "^",
    }.items():
        b.put(r, c, ch)
    return b.room()


def build_datadrv() -> list[str]:
    """DATA driver: forward every token, send color=(t-1)%16 for t>0."""
    b = Box()
    for (r, c), ch in {
        (1, 1): "v", (1, 5): "<", (1, 19): "<",
        (2, 1): ">", (2, 2): "@", (2, 3): "r", (2, 4): "s", (2, 5): "X",
        (3, 5): ">", (3, 6): "M", (3, 7): "1", (3, 8): "W", (3, 9): "-",
        (3, 10): "M", (3, 11): "`", (3, 12): "1", (3, 13): "6", (3, 14): "`",
        (3, 15): "W", (3, 16): "/", (3, 17): "W", (3, 18): "s", (3, 19): "^",
    }.items():
        b.put(r, c, ch)
    return b.room()


def build_swapdrv() -> list[str]:
    """SWAP driver: t<0 -> send 1 (commit, keep buffer); t>0 -> discard."""
    b = Box()
    for (r, c), ch in {
        (1, 1): "v", (1, 2): "s", (1, 3): "1", (1, 4): "<",
        (2, 1): ">", (2, 2): "@", (2, 3): "r", (2, 4): "X",
        (3, 1): "^", (3, 4): "<",
    }.items():
        b.put(r, c, ch)
    return b.room()


def encode_token(t: int) -> int:
    """Ring encoding of a display token (pixel t>=1 or commit t=-1)."""
    return -(t + 10)


def pixel_token(cell: int, color: int) -> int:
    """Driver-chain token for painting ``cell`` (1..256) with ``color``."""
    return (cell - 1) * 16 + color + 1


def place_display_block(canvas: Canvas, row: int, col: int) -> None:
    """TOKENSPLIT + driver chain + 16x16 display, TOKENSPLIT top-left at
    (row, col).  Requires row >= 10 (the driver stack extends 9 rows up).

    External connections:
      * ring-in:  TOKENSPLIT LEFT wall row (row+2)
      * ring-out: TOKENSPLIT BOTTOM col (col+7), heading down from row+7
    Block bounding box: rows row-9 .. row+16, cols col .. col+63.
    """
    R, C = row, col
    canvas.put(R, C, build_tokensplit())        # rows R..R+6, cols C..C+18
    canvas.put(R - 7, C + 18, build_addrdrv())  # rows R-7..R-3, cols C+18..C+37
    canvas.put(R, C + 19, build_datadrv())      # rows R..R+4,  cols C+19..C+39
    canvas.put(R + 7, C + 20, build_swapdrv())  # rows R+7..R+11, cols C+20..C+29
    display = (
        ["+" + "=" * 16 + "+"]
        + [":" + " " * 16 + ":" for _ in range(16)]
        + ["+" + "=" * 16 + "+"]
    )
    canvas.put(R - 3, C + 46, display)          # rows R-3..R+14, cols C+46..C+63
    # token stream: TOKENSPLIT top col 13 -> ADDRDRV left row 2
    canvas.pipe([(R - 1, C + 13), (R - 5, C + 13), (R - 5, C + 17)])
    # forward chain: ADDRDRV bottom col 4 -> DATADRV top col 3
    canvas.pipe([(R - 2, C + 22), (R - 1, C + 22)])
    # forward chain: DATADRV bottom col 4 -> SWAPDRV top col 3
    canvas.pipe([(R + 5, C + 23), (R + 6, C + 23)])
    # ADDR: ADDRDRV right row 3 -> over the top -> display top wall
    canvas.pipe([(R - 4, C + 42), (R - 4, C + 44), (R - 9, C + 44),
                 (R - 9, C + 50), (R - 4, C + 50)])
    # DATA: DATADRV right row 3 -> display left wall, via a delay detour
    # so pixel i's DATA always lands after its ADDR (cookbook section 8:
    # the display prefers ADDR in a same-tick race, which would shift
    # every pixel one cell left).  Detour length tuned in tests.
    canvas.pipe([(R + 3, C + 40), (R + 3, C + 41), (R + 15, C + 41),
                 (R + 15, C + 44), (R + 5, C + 44), (R + 5, C + 45)])
    # SWAP: SWAPDRV right row 1 -> under the display -> display bottom wall
    canvas.pipe([(R + 8, C + 26), (R + 8, C + 27), (R + 16, C + 27),
                 (R + 16, C + 50), (R + 15, C + 50)])


def build_ticka() -> list[str]:
    """TICKA (act modes 2, 3, 4, 5); relays {1, 7, 8, 12} (no trailers).

    mode 2 (bounds check): relay everything unchanged as mode 3; flag BP=1
      when ROW+DR or COL+DC leaves 0..15.  The check is one-sided:
      A=(v>>4), A=A*A is 0 for v in 0..15 and positive otherwise.
    mode 3 (apply): BP=0 -> [6, DR, ROW+DR, DC, COL+DC, FC, body];
      BP=1 -> [9, unchanged].
    mode 4 (fruit): [4, fy, fx, ...] -> [10, 1, hdr(FC=fcode), body, -1,
      fcode, 9].
    mode 5 (init): [5, sy, sx, -1] -> [10, 1, 0, sy, 1, sx, 0, h, -1, h, 10].
    """
    b = Box()

    def put(r, c, text, vertical=False):
        b.put(r, c, text) if not vertical else None
        if vertical:
            for i, ch in enumerate(text):
                if ch != "~":
                    b.put(r + i, c, ch)

    # dispatch chain: m-1 (rel), m-2, m-3, m-4, m-5, else -> relay
    b.put(2, 1, ">@rM1W-X")
    b.put(5, 8, ">M1W-X")
    b.put(10, 13, ">M1W-X")
    b.put(16, 18, ">M1W-X")
    b.put(21, 23, ">M1W-X")
    # mode-1 relay pre-corridor (emit 1) -> transit col 90 -> merge row 27
    b.put(2, 9, "1s")
    b.put(2, 90, "v")
    # else relay pre-corridor (restore m, emit) down col 28
    for i, ch in enumerate("M5+s"):
        b.put(22 + i, 28, ch)
    b.put(27, 28, "<")
    b.put(27, 90, "<")
    b.put(27, 2, "v")
    # shared relay-rest, rows 28-30
    b.put(28, 2, ">")
    b.put(28, 3, "5b>rsv")
    b.put(29, 5, "^ md")
    b.put(30, 8, ">^")
    b.put(29, 9, ">rsX")
    b.put(30, 12, "<")
    b.put(28, 12, ">")
    b.put(28, 90, "v")
    # ---- act2 (mode 2): rows 4-8
    b.put(5, 14, "3srsMrs+M4W}M*X")            # X at (5,28)
    b.put(5, 29, "rsMrs+M4W}M*X")              # X at (5,41)
    b.put(5, 42, "rs")
    b.put(5, 44, ">rsX")                        # body loop rows 5-6
    b.put(6, 44, "^  <")
    b.put(4, 47, ">0b")                         # legal: BP=0, home
    b.put(4, 78, "v")
    # OOB corridors: merge row 7, flag BP=1, universal relay to MARK
    b.put(7, 28, ">")
    b.put(7, 41, ">")
    b.put(7, 43, "1b>rsM1+X")                   # X at (7,51)
    b.put(8, 45, "^     <")                     # loop-back row 8
    b.put(7, 80, "v")                           # =0 exit continues east
    # ---- act3 (mode 3): rows 9-14
    b.put(10, 19, "d")
    b.put(10, 20, "6srsMr+srsMr+srs")           # legal, ends col 35
    b.put(10, 36, ">rsX")                       # body loop rows 10-11
    b.put(11, 36, "^  <")
    b.put(9, 39, ">")
    b.put(9, 82, "v")
    b.put(11, 19, ">9s4b>rsv")                  # dead: emit 9, relay 5
    b.put(12, 24, "^ md")
    b.put(13, 27, ">")
    b.put(13, 28, ">rsX")                       # body loop rows 13-14
    b.put(14, 28, "^  <")
    b.put(12, 31, ">")
    b.put(12, 84, "v")
    # ---- act4 (mode 4, fruit): rows 16-19
    b.put(16, 24, "`10`s1srM`16`*Mr+M1+M3b>rsv")  # ends (16,50)
    b.put(17, 47, "^ md")
    b.put(18, 50, ">rWsM")                      # drop FC, emit fcode, hold
    b.put(18, 55, ">rsX")                       # body loop rows 18-19
    b.put(19, 55, "^  <")
    b.put(17, 58, ">Ws9s")                      # trailers: P=fcode, C=9
    b.put(17, 86, "v")
    # ---- act5 (mode 5, init): row 21
    b.put(21, 29, "`10`s1s0srsM`16`*M1srs+M1+M0sWsM1NsWs`10`sr")  # final r eats the MARK
    b.put(21, 88, "v")
    # home row 33
    b.put(33, 1, "^")
    for c in (78, 80, 82, 84, 86, 88, 90):
        b.put(33, c, "<")
    return b.room()


def build_tickb() -> list[str]:
    """TICKB (act modes 6, 7); relays {1, 3, 8, 9, 10, 12}; 10 has trailers.

    mode 6 (scan): compute n = 16*ROW+COL+1 (ROW/COL already moved by
    TICKA), relay the packet unchanged as mode 7, and flag in BP:
      2 = FC == n (eat), 1 = n hits body[:-1] (collision), 0 = legal.
    A hit on the very last body item is the tail cell being vacated this
    tick, which is legal: the one-item PENDING corridor recognises it by
    seeing the MARK right after the match.
    mode 7 (apply, BP from mode 6 via d/x):
      legal -> [8, hdr, n, body, -1]; collision -> [9, unchanged];
      eat -> [10, 1, hdr with FC=0, n, body, -1, n, 10].
    """
    b = Box()
    # dispatch: m-1 (rel 1), m-3 (rel 3), m-6 (act), m-7 (act), else rel
    b.put(2, 1, ">@rM1W-X")
    b.put(5, 8, ">M2W-X")
    b.put(8, 13, ">M3W-X")
    b.put(20, 18, ">M1W-X")
    # relay pre-corridors: emit mode, hold it in B, join merge row 33
    b.put(2, 9, "1Ms")
    b.put(2, 92, "v")
    b.put(5, 14, "3Ms")
    b.put(5, 94, "v")
    for i, ch in enumerate("M7+Ms"):        # else: restore m, emit (col 23)
        b.put(21 + i, 23, ch)
    b.put(26, 23, "<")                       # reroute west of the eat lane
    b.put(26, 3, "v")
    b.put(33, 3, "<")
    b.put(33, 92, "<")
    b.put(33, 94, "<")
    b.put(33, 2, "v")
    # shared relay rest, rows 34-36, with mode-10 trailer check
    b.put(34, 2, ">")
    b.put(34, 3, "5b>rsv")
    b.put(35, 5, "^ md")
    b.put(36, 8, ">^")
    b.put(35, 9, ">rsX")
    b.put(36, 12, "<")
    b.put(34, 12, ">WM9W-M1W-X")            # X at (34,22)
    b.put(34, 23, "rsrs")                    # trailers when m == 10
    b.put(34, 92, "v")
    # m < 10 exit: the ccw walker heads north from (34,22) straight through
    # the empty (33,22) -- no glyph there, so merge-row walkers pass too.
    b.put(32, 22, ">")
    b.put(32, 96, "v")
    b.put(39, 96, "<")
    b.put(36, 22, ">")                       # m = 12: east on row 36
    b.put(36, 94, "v")
    b.put(39, 94, "<")
    # ---- act6 (mode 6): main row 8, scan rows 10-18
    b.put(8, 19, "7srsrsM`16`*Mrsrs+M1+Mrs-X")   # X at (8,44)
    b.put(8, 46, ">rsX")                     # eat: body relay loop rows 8-9
    b.put(9, 46, "^  <")
    b.put(7, 49, ">2b")                      # eat flag
    b.put(7, 78, "v")
    b.put(7, 44, ">v")                       # FC-test merge: north path
    b.put(10, 44, ">>")                      # merge row
    b.put(10, 46, ">  rX")                   # scan entry; X1 at (10,50)
    b.put(9, 50, ">s0b")                     # MARK first: all legal
    b.put(9, 80, "v")
    b.put(11, 50, "s")
    b.put(12, 50, "-")
    b.put(13, 50, "X")                       # X2 (heading south)
    b.put(13, 46, "^")                       # X2>0 loop-back west lane
    b.put(13, 52, "v")                       # X2<0 loop-back east lane
    b.put(14, 52, "<")
    b.put(14, 46, "^")
    b.put(15, 50, ">")                       # X2=0: PENDING row
    b.put(15, 54, "rX")                      # X3 at (15,55)
    b.put(14, 55, ">s0b")                    # tail match + MARK: legal
    b.put(14, 82, "v")
    b.put(16, 55, "s")                       # collision: emit the item
    b.put(17, 55, ">rsX")                    # flush loop rows 17-18
    b.put(18, 55, "^  <")
    b.put(16, 58, ">1b")                     # collision flag
    b.put(16, 84, "v")
    # ---- act7 (mode 7): d/x branch; legal row 20; coll 23-26; eat 28-31
    b.put(20, 26, "d")
    b.put(20, 27, "8srsrsM`16`*Mrsrs+M1+MrsWs")   # ends (20,52)
    b.put(20, 53, ">rsX")                    # body loop rows 20-21
    b.put(21, 53, "^  <")
    b.put(19, 56, ">")
    b.put(19, 86, "v")
    b.put(21, 26, "x")
    b.put(21, 25, "v")                       # x cw (BP=1): collision
    b.put(23, 25, ">9s4b>rsv")
    b.put(24, 30, "^ md")
    b.put(25, 33, ">>rsX")                   # exit + body loop rows 25-26
    b.put(26, 34, "^  <")
    b.put(24, 37, ">")
    b.put(24, 88, "v")
    b.put(21, 44, "v")                       # x ccw (BP=2): eat lane east
    b.put(28, 44, "<")                       # then west across row 28
    b.put(28, 4, "v")
    b.put(30, 4, ">")
    b.put(30, 5, "`10`s1srsrsM`16`*Mrsrs+M1+Mr0sWsM")  # ends (30,37)
    b.put(30, 38, ">rsX")                    # body loop rows 30-31
    b.put(31, 38, "^  <")
    b.put(29, 41, ">Ws`10`s")                # trailers P=n, C=10
    b.put(29, 90, "v")
    b.put(39, 90, "<")
    # home row 39
    b.put(39, 1, "^")
    for c in (78, 80, 82, 84, 86, 88, 92):
        b.put(39, c, "<")
    return b.room()


def build_in() -> list[str]:
    """IN (act mode 1; the only 2-in station).

    Walls: INPUT pipe TOP col 4, ring-in BOTTOM col 40, ring-out RIGHT.
    Every input-read r sits in the top-left corner (rows 1-2, cols 6-19)
    and every ring r in the bottom half right of col 30, so nearest-pipe
    resolution has margins >= 10 (asserted in tests).

    Prologue (once): read sx sy, emit [5, sy, sx, -1] (TICKA builds the
    packet).  Mode 1: read command c; c=0 -> [2, ...]; c=1 -> read fx fy,
    emit [4, fy, fx, ...]; c=2..5 -> rewrite DR/DC, emit [1, ...].
    Relays {3, 7, 8, 12} (no trailers).
    """
    b = Box()
    # prologue row 1 (@ runs once), east of the fruit-read block so its
    # exit path does not walk through it; parks via col 74 to the home row
    b.put(1, 30, "@5srMrsWs1Ns")
    b.put(1, 74, "v")
    b.put(63, 74, "<")
    # entry row 58 + dispatch
    b.put(58, 2, ">")
    b.put(58, 40, "rM1W-X")                  # X at (58,45)
    b.put(58, 72, "^")                        # act: up the east side
    b.put(2, 72, "<")                         # west along row 2
    b.put(2, 6, "r")                          # read command c
    b.put(2, 5, "v")                          # down col 5
    b.put(26, 5, ">")
    # c-dispatch chain: X(c) at (26,6); then -1 per level
    b.put(26, 6, "X")
    b.put(31, 6, ">M1W-X")                    # X2 at (31,11): c-1 fruit
    b.put(38, 11, ">M1W-X")                   # X3 at (38,16): c-2 up
    b.put(43, 16, ">M1W-X")                   # X4 at (43,21): c-3 right
    b.put(48, 21, ">M1W-X")                   # X5 at (48,26): c-4 down
    b.put(53, 26, ">")                        # else: c=5 left
    # TICK (c=0): rows 26-29
    b.put(26, 7, "2s")
    b.put(26, 30, "4b>rsv")
    b.put(27, 32, "^ md")
    b.put(28, 35, ">>rsX")
    b.put(29, 36, "^  <")
    b.put(27, 39, ">")
    b.put(27, 66, "v")
    b.put(63, 66, "<")
    # FRUIT (c=1): rows 31-36; input reads up top on row 1
    b.put(31, 12, "4s")
    b.put(31, 16, "^")
    b.put(1, 16, ">rMrsWs")
    b.put(1, 23, "v")
    b.put(33, 23, ">")
    b.put(33, 30, "4b>rsv")
    b.put(34, 32, "^ md")
    b.put(35, 35, ">>rsX")
    b.put(36, 36, "^  <")
    b.put(34, 39, ">")
    b.put(34, 67, "v")
    b.put(63, 67, "<")
    # UP (c=2): rows 37-39
    b.put(38, 30, "1sr1Nsrsr0srsrs")
    b.put(38, 45, ">rsX")
    b.put(39, 45, "^  <")
    b.put(37, 48, ">")
    b.put(37, 68, "v")
    b.put(63, 68, "<")
    # RIGHT (c=3): rows 42-44
    b.put(43, 30, "1sr0srsr1srsrs")
    b.put(43, 44, ">rsX")
    b.put(44, 44, "^  <")
    b.put(42, 47, ">")
    b.put(42, 69, "v")
    b.put(63, 69, "<")
    # DOWN (c=4): rows 47-49
    b.put(48, 30, "1sr1srsr0srsrs")
    b.put(48, 44, ">rsX")
    b.put(49, 44, "^  <")
    b.put(47, 47, ">")
    b.put(47, 70, "v")
    b.put(63, 70, "<")
    # LEFT (c=5): rows 52-54
    b.put(53, 30, "1sr0srsr1Nsrsrs")
    b.put(53, 45, ">rsX")
    b.put(54, 45, "^  <")
    b.put(52, 48, ">")
    b.put(52, 71, "v")
    b.put(63, 71, "<")
    # relay corridor (modes 3, 7, 8, 12): rows 59-62
    b.put(59, 45, "<")
    b.put(59, 3, "v")
    b.put(60, 3, ">+s5b>rsv")
    b.put(61, 8, "^ md")
    b.put(62, 11, ">^")
    b.put(61, 12, ">rsX")
    b.put(62, 15, "<")
    b.put(60, 15, ">")
    b.put(60, 65, "v")
    b.put(63, 65, "<")
    # home row 63, up col 2 to the entry row
    b.put(63, 2, "^")
    b.put(62, 2, " ")
    return b.room()


def build_feeder() -> list[str]:
    """Test-rig room: one I feeds both of IN's pipes.  Values >= 1000 are
    input words (forwarded minus 1000 to the top pipe); everything else is
    ring traffic (forwarded unchanged to the bottom... top ring pipe)."""
    b = Box()
    b.put(1, 12, "<")
    b.put(1, 11, "+")
    b.put(1, 10, "s")
    b.put(1, 9, "v")
    b.put(2, 1, ">@rM`999`W-X")
    b.put(3, 12, "+")
    b.put(4, 12, "M")
    for i, ch in enumerate("`1000`"):
        b.put(5 + i, 12, ch)
    b.put(11, 12, "W")
    b.put(12, 12, "-")
    b.put(13, 12, "s")
    b.put(14, 12, "<")
    b.put(14, 9, "<")
    b.put(14, 1, "^")
    return b.room()


def build_in_rig() -> str:
    """Feeder-driven harness for IN: I -> FEEDER -> (ring + input) -> IN -> O."""
    cv = Canvas()
    IN_R, IN_C = 3, 8
    in_rows = build_in()
    cv.put(IN_R, IN_C, in_rows)
    h, w = len(in_rows), len(in_rows[0])
    F_R, F_C = IN_R + h + 3, IN_C + 20
    feeder = build_feeder()
    cv.put(F_R, F_C, feeder)
    fh = len(feeder)
    cv.put(F_R + 1, 0, ["+-+", "|I|", "+-+"])
    cv.pipe([(F_R + 2, 3), (F_R + 2, F_C - 1)])
    cv.pipe([(F_R - 1, F_C + 10), (IN_R + h + 1, F_C + 10),
             (IN_R + h + 1, IN_C + 40), (IN_R + h, IN_C + 40)])
    cv.pipe([(F_R + fh, F_C + 12), (F_R + fh + 1, F_C + 12),
             (F_R + fh + 1, IN_C + w + 8), (1, IN_C + w + 8),
             (1, IN_C + 4), (2, IN_C + 4)])
    cv.put(IN_R + 1, IN_C + w + 3, ["+-+", "|O|", "+-+"])
    cv.pipe([(IN_R + 2, IN_C + w), (IN_R + 2, IN_C + w + 2)])
    return cv.render()


def build_snake() -> str:
    """The full Snake machine.

    Vertical station stack (IN, TICKA, TICKB, TICKC, DRAW, display block)
    with ring wrap pipes: down the right side (col 102-108), across a gap
    row, down the left lane (col 4), into the next station's left wall.
    The display block's TOKENSPLIT returns the ring up the far-left lane
    (col 2) to IN's bottom wall.  No output room: frames only.
    """
    cv = Canvas()
    cv.put(0, 11, ["+-+", "|I|", "+-+"])
    cv.pipe([(3, 12), (5, 12)])                    # I -> IN top col 4

    cv.put(6, 8, build_in())                       # rows 6-70, cols 8-84
    cv.put(74, 8, build_ticka())                   # rows 74-108, cols 8-99
    cv.put(112, 8, build_tickb())                  # rows 112-152, cols 8-105
    cv.put(156, 8, build_tickc())                  # rows 156-168, cols 8-54
    cv.put(172, 8, build_draw())                   # rows 172-190, cols 8-79
    place_display_block(cv, 206, 8)                # rows 197-222, cols 8-71

    # ring wraps
    cv.pipe([(8, 84), (8, 102), (72, 102), (72, 4), (76, 4), (76, 7)])
    cv.pipe([(76, 100), (76, 104), (110, 104), (110, 4), (114, 4), (114, 7)])
    cv.pipe([(114, 106), (114, 108), (154, 108), (154, 4), (158, 4),
             (158, 7)])
    cv.pipe([(158, 55), (158, 108), (170, 108), (170, 4), (174, 4),
             (174, 7)])
    cv.pipe([(174, 80), (174, 108), (194, 108), (194, 4), (208, 4),
             (208, 7)])
    # TOKENSPLIT ring-out -> up the far left -> IN bottom col 40 (abs 48)
    cv.pipe([(213, 15), (216, 15), (216, 2), (71, 2), (71, 48)])
    cv.cells[(71, 48)] = "^"                       # terminal bend into IN
    return cv.render()
