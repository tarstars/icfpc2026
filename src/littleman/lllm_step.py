"""LLLM STEP station: the interpreter half of EXEC (work order claude_11b).

STEP knows *nothing* about world layout.  It speaks three frozen interfaces:

* ``claude_09`` in  -- 64 packed world tokens then ``man_addr`` from LOADER,
* ``claude_11a``    -- the FETCH request grammar (``0..255`` op fetch,
  ``256..511`` colour fetch, ``-1`` full colour stream),
* ``claude_10`` out -- packed DRAW deltas (``addr*16+colour``, negative =
  commit).

This module is the MODEL-FIRST deliverable: :class:`StepModel` is a
restricted-subset model of the STEP room in the style of
``littleman.snake.CycleModel`` (host ``A``/``B``/``BP`` discipline, one
method per machine step), and :class:`ScriptedFetch` is a scripted stand-in
for the 11a station so the model can be validated with nothing else landed.
"""

from __future__ import annotations

from .sim import wrap64

# ------------------------------------------------------- claude_09 grammar
CLASS_SPACE = 0
CLASS_WALL = 1
CLASS_HEADING = 2
CLASS_DIGIT = 3
CLASS_M = 4
CLASS_ADD = 5
CLASS_SUB = 6
CLASS_BRANCH = 7
CLASS_HALT = 8

# interior glyph -> (class, value, colour)
GLYPH = {
    " ": (CLASS_SPACE, 0, 0),
    "^": (CLASS_HEADING, 0, 3),
    ">": (CLASS_HEADING, 1, 3),
    "v": (CLASS_HEADING, 2, 3),
    "V": (CLASS_HEADING, 2, 3),
    "<": (CLASS_HEADING, 3, 3),
    "M": (CLASS_M, 0, 12),
    "+": (CLASS_ADD, 0, 10),
    "-": (CLASS_SUB, 0, 10),
    "X": (CLASS_BRANCH, 0, 3),
    "H": (CLASS_HALT, 0, 3),
}
for _d in "0123456789":
    GLYPH[_d] = (CLASS_DIGIT, int(_d), 8)

WALL_REC = 4 | (CLASS_WALL << 4) | (1 << 12)   # colour 4, class 1, wall bit

# canvas is always 16 wide: heading 0..3 = N, E, S, W
STEP_DELTA = (-16, 1, 16, -1)

MAN_COLOR = 9
DISPLAY = 16


# --------------------------------------------------------- LOADER stand-in
def pack_world(rows: list[str]) -> tuple[list[int], int]:
    """Local stand-in for the LOADER: 64 packed tokens plus ``man_addr``.

    Exactly the claude_09 contract -- padding is space, the PROGRAM
    perimeter is wall regardless of glyph, ``@`` is space and yields
    ``man_addr``.  Replaced by ``lllm_loader.reference_stream`` once that
    module lands (:func:`loader_stream` cross-checks it when present).
    """
    height, width = len(rows), len(rows[0])
    recs: list[int] = []
    man_addr = 0
    for addr in range(256):
        y, x = divmod(addr, DISPLAY)
        if y >= height or x >= width:
            recs.append(0)
        elif x in (0, width - 1) or y in (0, height - 1):
            recs.append(WALL_REC)
        else:
            ch = rows[y][x]
            if ch == "@":
                man_addr, ch = addr, " "
            cls, val, col = GLYPH.get(ch, (CLASS_SPACE, 0, 0))
            recs.append(col | (cls << 4) | (val << 8))
    tokens = [
        sum(recs[4 * j + i] << (13 * i) for i in range(4)) for j in range(64)
    ]
    return tokens, man_addr


def loader_stream(rows: list[str]) -> list[int]:
    """The claude_09 prefix STEP consumes: 64 world tokens then man_addr."""
    tokens, man_addr = pack_world(rows)
    return tokens + [man_addr]


class ScriptedFetch:
    """Scripted stand-in for the claude_11a FETCH station.

    Phase-split by count exactly like the real one: the first 64 tokens are
    the packed world, every token after that is a request.  ``send`` returns
    the response tokens (empty during SETUP).
    """

    def __init__(self) -> None:
        self.records: list[int] = []
        self.requests: list[int] = []
        self.setup_left = 64

    def send(self, token: int) -> list[int]:
        if self.setup_left:
            self.setup_left -= 1
            rec = token
            for _ in range(4):
                self.records.append(rec & 8191)
                rec >>= 13
            return []
        self.requests.append(token)
        if token < 0:                                   # full colour stream
            return [r & 15 for r in self.records]
        if token >= 256:                                # colour fetch
            return [self.records[token - 256] & 15]
        rec = self.records[token]                       # op fetch
        return [(((rec >> 4) & 15) << 4) | ((rec >> 8) & 15)]


class StepModel:
    """Restricted-subset model of the STEP room (snake ``CycleModel`` style).

    Two register families, kept strictly apart:

    * ``A`` / ``B`` / ``BP`` -- the STEP man's *own* registers.  ``B`` is
      written only by ``M``, ``W``, ``/`` (corrected cookbook rule), so it
      survives arithmetic and relays; ``BP`` counts the round's ``k`` ticks
      and round 1's 256 pixels.
    * the private scratch loop -- a 2-pipe ring of four tokens holding the
      *interpreted* man's state: ``ADDR``, ``CTRL``, ``A_i``, ``B_i``.
      ``CTRL = 4*halted + heading`` (heading 0..3 = N, E, S, W), so one
      token carries both control bits and the halt/wall freeze flag.

    The loop is read by rotation: every access walks the ring one full lap
    so slot order is invariant across machine steps -- the choreography a
    ``r``/``s`` racetrack in the room performs literally.  Four slots rather
    than the work order's minimum of three, because ``ADDR`` must also
    survive the FETCH round trip; reported as the one design refinement.
    """

    RING = ("ADDR", "CTRL", "AI", "BI", "OLD")

    def __init__(self, fetch) -> None:
        self.fetch = fetch
        self.A = 0            # host accumulator
        self.B = 0            # host B (written only by M / W / /)
        self.BP = 0           # host backpack: loop counter
        self.ring: list[int] = []
        self.deltas: list[int] = []
        self.ticks = 0        # interpreted LLLM ticks actually executed
        self.msteps = 0       # modelled machine steps of the STEP man
        self.trace: list[tuple] = []

    # -- private scratch loop: one `r` / one `s` per call ------------------
    def _pull(self) -> int:
        """``r``: A <- head of the scratch loop."""
        self.A = self.ring.pop(0)
        self.msteps += 1
        return self.A

    def _push(self, value: int | None = None) -> None:
        """``s``: tail of the scratch loop <- A."""
        if value is not None:
            self.A = value
        self.ring.append(self.A)
        self.msteps += 1

    def _relay(self, laps: int) -> None:
        """Move ``laps`` slots along without disturbing their values."""
        for _ in range(laps):
            self._push(self._pull())

    def _read(self, name: str) -> int:
        """Bring one named slot into A; ring order is restored on exit."""
        i = self.RING.index(name)
        self._relay(i)
        value = self._pull()
        self._push()
        self._relay(len(self.RING) - 1 - i)
        return value

    def _write(self, name: str, value: int) -> None:
        """Replace one named slot; ring order is restored on exit."""
        i = self.RING.index(name)
        self._relay(i)
        self._pull()
        self._push(value)
        self._relay(len(self.RING) - 1 - i)

    # -- SETUP ------------------------------------------------------------
    def setup(self, stream: list[int]) -> None:
        """claude_09 in: relay 64 world tokens to FETCH, seed the ring.

        The world is forwarded verbatim -- STEP never inspects it.  The
        65th token is ``man_addr``; heading starts East, halted 0, and both
        interpreted registers start at 0.
        """
        for token in stream[:64]:
            self.A = token
            self.msteps += 2                      # r then s, per token
            self.fetch.send(token)
        self.A = stream[64]
        # ADDR, CTRL(East, live), A_i, B_i, OLD
        self.ring = [self.A, 1, 0, 0, self.A]
        self.msteps += 5

    # -- one interpreted tick ---------------------------------------------
    def _op_fetch(self, addr: int) -> int:
        """Request grammar 0..255: send addr, receive ``class<<4|value``."""
        self.A = addr
        (rec,) = self.fetch.send(addr)
        self.A = rec
        self.msteps += 2
        return rec

    def _dispatch(self, rec: int) -> None:
        """The claude_09 class table: one arm per class, CTRL/A_i/B_i only."""
        cls, val = rec >> 4, rec & 15
        ctrl = self._read("CTRL")
        if cls in (CLASS_WALL, CLASS_HALT):
            self._write("CTRL", ctrl | 4)         # freeze in place, no move
        elif cls == CLASS_HEADING:
            self._write("CTRL", (ctrl & 4) | val)
        elif cls == CLASS_DIGIT:
            self._write("AI", val)
        elif cls == CLASS_M:
            self._write("BI", self._read("AI"))
        elif cls == CLASS_ADD:
            self.B = self._read("BI")
            self._write("AI", wrap64(self._read("AI") + self.B))
        elif cls == CLASS_SUB:
            self.B = self._read("BI")
            self._write("AI", wrap64(self._read("AI") - self.B))
        elif cls == CLASS_BRANCH:
            sign = self._read("AI")
            if sign > 0:
                self._write("CTRL", (ctrl & 4) | ((ctrl + 1) & 3))
            elif sign < 0:
                self._write("CTRL", (ctrl & 4) | ((ctrl + 3) & 3))
        # CLASS_SPACE (and any unknown class): nop

    def _move(self) -> None:
        """Blind step by heading -- the NEXT fetch discovers a wall."""
        ctrl = self._read("CTRL")
        if ctrl & 4:
            return
        self._write("ADDR", self._read("ADDR") + STEP_DELTA[ctrl & 3])

    def _tick(self) -> None:
        """fetch -> dispatch -> blind move.  No-op once frozen."""
        if self._read("CTRL") & 4:
            return
        rec = self._op_fetch(self._read("ADDR"))
        self._dispatch(rec)
        self._move()
        self.ticks += 1

    # -- DRAW side (claude_10) --------------------------------------------
    def _emit(self, token: int) -> None:
        """One packed delta token out to DRAW."""
        self.deltas.append(token)
        self.msteps += 1

    def _commit(self) -> None:
        """Negative sentinel: DRAW swaps the buffer."""
        self.deltas.append(-1)
        self.msteps += 1

    # -- rounds -----------------------------------------------------------
    def round_one(self) -> None:
        """ROUND 1: FETCH ``-1`` -> 256 colours, own counter formats addrs."""
        colors = self.fetch.send(-1)
        self.BP = 0
        for color in colors:
            self._emit(self.BP * 16 + color)
            self.BP += 1
        self._emit(self._read("ADDR") * 16 + MAN_COLOR)
        self._commit()
        self.trace.append(("round1", len(colors)))

    def round(self, k: int) -> None:
        """A later round: k ticks, then restore-old / draw-new / commit."""
        old = self._read("ADDR")
        # `old` cannot live in host B: the interpreted add/sub arms clobber
        # it mid-round.  It rides the scratch loop instead.
        self._write("OLD", old)
        before = self.ticks
        self.BP = k
        while self.BP:
            self._tick()
            self.BP -= 1
        old = self._read("OLD")
        (color,) = self.fetch.send(old + 256)     # colour fetch of round start
        self._emit(old * 16 + color)
        self._emit(self._read("ADDR") * 16 + MAN_COLOR)
        self._commit()
        self.trace.append(("round", k, self.ticks - before, old, self._read("ADDR")))


# ------------------------------------------------------------- DRAW oracle
def frames_from_deltas(deltas: list[int]) -> list[list[str]]:
    """claude_10 DRAW semantics: paint ``t//16 <- t%16``, negative commits."""
    buf = [0] * (DISPLAY * DISPLAY)
    frames = []
    for token in deltas:
        if token < 0:
            frames.append(
                [
                    "".join("%x" % buf[r * DISPLAY + c] for c in range(DISPLAY))
                    for r in range(DISPLAY)
                ]
            )
        else:
            buf[token // 16] = token % 16
    return frames


# ------------------------------------------------------------------ driver
def run_case(rows: list[str], ks: list[int], *, fetch=None) -> StepModel:
    """Drive one whole case: SETUP, round 1, then a round per ``k``."""
    model = StepModel(ScriptedFetch() if fetch is None else fetch)
    model.setup(loader_stream(rows))
    model.round_one()
    for k in ks:
        model.round(int(k))
    return model


def case_rounds(case: dict) -> tuple[list[str], list[int], list[list[str]]]:
    """Split a judge-shaped case into (program rows, ks, expected frames)."""
    from .llm import program_grid

    rows = program_grid([int(v) for v in case["rounds"][0]["in"]])
    ks = [int(rd["in"][0]) for rd in case["rounds"][1:]]
    frames = [rd["frames"][0] for rd in case["rounds"]]
    return rows, ks, frames


class ReferenceFetch:
    """Adapter putting the real claude_11a ``fetch_reference`` behind the
    scripted stub's ``send`` interface.  Activates only once
    ``littleman.lllm_fetch`` lands; until then :class:`ScriptedFetch` is the
    model's counterparty."""

    def __init__(self) -> None:
        from .lllm_fetch import fetch_reference

        self._fetch = fetch_reference
        self.world: list[int] = []
        self.requests: list[int] = []

    def send(self, token: int) -> list[int]:
        if len(self.world) < 64:
            self.world.append(token)
            return []
        self.requests.append(token)
        return list(self._fetch(self.world, [token]))


# ------------------------------------------------------------ STEP layout
# Six ports (the scratch loop is a real pipe pair, so 3 in / 3 out -- the
# work order's 2-in/2-out count omits it).  Nearest-pipe resolution is made
# tractable by a strict Voronoi split: the two scratch ports sit on the
# RIGHT wall and the four external ones on the LEFT, separated vertically
# into a top zone (LOAD in / DRAW out) and a bottom zone (RESP in / REQ
# out).  Every r/s cell therefore lives in exactly one of three regions.
STEP_ROWS, STEP_COLS = 96, 72

# The hot path is the per-tick FETCH transaction, so REQ and RESP share the
# TOP zone; LOAD (once a round) and DRAW (twice a round) share the BOTTOM.
REQ_ROW = 2         # left wall,  outgoing -> FETCH
# RESP takes the TOP wall: two pipes running in opposite directions between
# the same pair of rooms on the same side always cross, and the parser
# rejects that.  Top-wall entry also puts RESP's Voronoi region exactly over
# the tick loop, where every response is read.
RESP_COL = 8        # top wall,   incoming <- FETCH
DRAW_ROW = 20       # left wall,  outgoing -> DRAW
LOAD_ROW = 21       # left wall,  incoming <- LOADER
SCR_OUT_ROW = 30    # right wall, outgoing -> scratch relay
SCR_IN_ROW = 33     # right wall, incoming <- scratch relay


def build_step_relay():
    """The scratch loop's relay: 6 ticks per token (memory_04 pattern)."""
    from .lllm_fetch import Room

    room = Room(2, 4)
    room.put(1, 1, "@>rv")
    room.put(2, 2, "^s<")
    return room


def _step_setup(room) -> None:
    """SETUP: relay the 64 world tokens LOADER -> FETCH, verbatim.

    The relay straddles both left-wall zones -- ``r`` sits low (row 17, in
    LOAD's region) and ``s`` high (row 2, in REQ's) -- so one lap is a tall
    round trip.  64 laps cost ~2.3k ticks, paid once.
    """
    # The prologue descends column 3 OFF the lap, seeding BP from a VERTICAL
    # literal, and rejoins the lap at its `r` -- the one cell every lap also
    # enters heading east, so no prologue cell is ever re-executed.
    room.put(1, 1, "@ v")
    for r, ch in zip(range(2, 7), "`64`b"):
        room.put(r, 3, ch)
    for r in range(7, 17):
        room.put(r, 3, "v")
    room.put(17, 3, ">")
    room.put(17, 9, ">r ^")              # LOAD read, then back up
    room.put(2, 9, "ams<")               # return row: count, send, turn down
    for r in range(3, 17):               # down-leg and up-leg
        room.put(r, 9, "v")
        room.put(r, 12, "^")
    room.put(2, 2, "v")                  # BP exhausted: fall out of the lap
    for r in range(3, 21):
        room.put(r, 2, "v")
    room.put(21, 2, ">")


def _step_round1(room) -> None:
    """ROUND 1: man_addr into the ring, FETCH ``-1``, then 257 pixels.

    The pixel counter rides in ``B``: ``r + s`` emits ``p + colour`` and
    ```16` + M`` re-forms ``B = p + 16``, so the whole 256-pixel
    loop needs no ring access at all -- man_addr simply parks in the scratch
    loop while it runs.
    """
    room.put(21, 9, "r")                 # man_addr from LOADER
    room.put(21, 46, "s")                # park it in the scratch loop
    room.put(21, 60, "^")
    for r in range(5, 21):
        room.put(r, 60, "^")
    room.put(4, 60, "<")
    room.put(4, 13, "vb`652`M0s N1<")    # BP=256, B=0, send -1 to FETCH
    room.put(5, 13, ">v")
    room.put(6, 14, ">r+v")              # colour -> p+colour, then south
    for r in range(7, 18):
        room.put(r, 17, "v")
        room.put(r, 26, "^")
    room.put(5, 26, "<")
    room.put(18, 17, ">s`16`+Mma")       # emit, p += 16, count, loop up
    # 257th pixel: the man, then the commit sentinel.
    room.put(18, 46, "rsM`16`*M9+v")
    room.put(19, 14, "sN1s")             # man pixel, then commit (walked west)
    room.put(19, 13, "H")                # TODO: round loop entry (see notes)
    room.put(19, 57, "<")


TAPE_LO, TAPE_HI = 42, 60   # the scratch-loop tape zone (rows 22+)
# Vertical highways live in columns 61..71, the only band no horizontal
# walkway in the room ever crosses; every phase-to-phase jump uses one.
HW = dict(live=71, split=70, tick=69, frozen=68, arm=67, move=66,
          loop=65, emit=64, round=63)
SEED_ROW, ROUND_ROW = 23, 30
TICK_ROW = 36
SCR_COL = 42        # first column whose r/s binds the scratch loop (rows 22+)
REQ_MAX_ROW = 11    # last row whose left-wall s reaches REQ rather than DRAW


class Tape:
    """A boustrophedon opcode tape: straight-line code that snakes in place.

    The interpreter is mostly straight-line register choreography, and laying
    that out by hand is where littleman rooms go wrong.  A tape takes a list
    of tokens -- a one-character opcode, or ``"#N"`` for the literal ``N`` --
    and places them, reversing literal digits on right-to-left laps and
    stepping around the vertical-backtick-pairing rule automatically.
    """

    def __init__(self, room, row: int, col: int, lo: int, hi: int):
        self.room, self.row, self.col, self.lo, self.hi = room, row, col, lo, hi
        self.dir = 1

    def _cells(self, token: str) -> str:
        if not token.startswith("#"):
            return token
        digits = str(token[1:])
        return "`" + (digits if self.dir > 0 else digits[::-1]) + "`"

    def _backtick_clash(self, text: str, col: int) -> bool:
        start = col if self.dir > 0 else col - len(text) + 1
        for i, ch in enumerate(text):
            if ch != "`":
                continue
            c = start + i
            if any(k[1] == c and v == "`" for k, v in self.room.cells.items()):
                return True
        return False

    def _turn(self) -> None:
        """Drop one row and reverse: `v` at the edge, then the new heading."""
        self.room.put(self.row, self.col, "v")
        self.dir = -self.dir
        self.row += 1
        self.room.put(self.row, self.col, ">" if self.dir > 0 else "<")
        self.col += self.dir

    def emit(self, *tokens: str) -> "Tape":
        for token in tokens:
            text = self._cells(token)
            while True:
                end = self.col + self.dir * (len(text) - 1)
                if self.lo <= end <= self.hi and not self._backtick_clash(
                    text, self.col
                ):
                    break
                if not (self.lo <= end <= self.hi):
                    self._turn()
                    text = self._cells(token)
                else:                       # backtick column clash: shift on
                    self.col += self.dir
            start = self.col if self.dir > 0 else self.col - len(text) + 1
            self.room.put(self.row, start, text)
            self.col += self.dir * len(text)
        return self

    def down_at(self, col: int, row: int) -> "Tape":
        """Leave the tape: walk on to ``col``, then descend to ``row``."""
        while (col - self.col) * self.dir < 0:
            self._turn()
        for r in range(self.row, row):
            self.room.put(r, col, "v")
        self.row, self.col, self.dir = row, col, 1
        return self


# ---------------------------------------------------------------- BLOCKER
# The round loop below is register-correct (its tape drives the ring to
# exactly [CTRL=1, ADDR=man_addr, BI=0, AI=0, OLD=man_addr, K=k], verified
# in the rig) but CANNOT YET BE PLACED, for a purely geometric reason:
#
#   * ROUND 1's man_addr walkway occupies row 21, columns 2..60, so no
#     vertical corridor may cross row 21 anywhere in that span; and
#   * its ascent back to row 4 occupies column 60, rows 5..21, so no
#     horizontal run in rows 5..20 may cross column 60.
#
# Together those leave no path from the ROUND 1 finish (rows 18-19, columns
# <= 57) down to rows 23+: reaching a column > 60 at row 21 requires a
# horizontal run that must first cross column 60.  Every variant tried --
# exit on row 19, on row 20, ascent moved to columns 27/45/47/62, walkway
# moved to row 22 -- reproduces the same crossing under a different name.
#
# THE FIX, for whoever picks this up: re-lay `_step_round1`'s post-pixel
# path so the man_addr park and ascent live entirely inside the highway
# band (columns 61..71), leaving rows 19..22 clear across columns 1..60.
# Then `_step_seed` places unchanged and `HW` wires the rest.
def _highway(room, col: int, top: int, bottom: int) -> None:
    """Fill one vertical highway segment (exclusive of ``bottom``)."""
    for r in range(top, bottom):
        room.put(r, col, "v")


def _enter_tape(room, col: int, row: int) -> "Tape":
    """Arrive down a highway, run west to the tape zone, start a tape east."""
    room.put(row, col, "<")
    room.put(row, TAPE_LO - 1, "v")
    room.put(row + 1, TAPE_LO - 1, ">")
    return Tape(room, row + 1, TAPE_LO, TAPE_LO, TAPE_HI)


def _leave_tape(room, tape: "Tape", col: int, row: int) -> None:
    """Run the tape out to a highway column and descend to ``row``."""
    tape.down_at(col, row)


def _step_seed(room) -> None:
    """Seed the six-slot ring, then read the round's k and stamp OLD/K.

    Ring after the seed tape is ``[CTRL, ADDR, BI, AI, OLD, K]`` with CTRL
    live-and-East (1) and every other slot 0.  ROUND-IN holds k in B across
    five relays to write ``K = k``, then holds ADDR in B to write
    ``OLD = ADDR``; both exploit B surviving r/s.
    """
    seed = _enter_tape(room, 61, SEED_ROW)
    seed.emit("r", "M", "#1", "s", "W", "s", "#0", "s", "s", "s", "s")
    _leave_tape(room, seed, HW["round"], ROUND_ROW)
    _step_round_in(room)


def _step_round_in(room) -> None:
    """Per round: k from LOADER into BP-free B, then K and OLD stamped."""
    room.put(ROUND_ROW, HW["round"], "<")
    room.put(ROUND_ROW, 7, "Mr")          # walked west: r first, then M
    room.put(ROUND_ROW, 5, "v")
    room.put(ROUND_ROW + 1, 5, ">")
    tape = Tape(room, ROUND_ROW + 1, TAPE_LO, TAPE_LO, TAPE_HI)
    tape.emit(*"rs" * 5, "r", "W", "s")                    # K = k
    tape.emit(*"rs", "r", "M", "s", *"rs" * 2, "r", "W", "s", *"rs")
    _leave_tape(room, tape, HW["tick"], TICK_ROW)
    room.put(TICK_ROW, HW["tick"], "H")   # TODO: tick loop starts here


def build_step_room():
    """The STEP station as a :class:`lllm_fetch.Room`.

    Transcribed and rig-verified against :class:`StepModel`: SETUP (the 64
    world tokens relayed LOADER -> FETCH) and ROUND 1 (FETCH ``-1``, 256
    static pixels, the man pixel, the commit sentinel) -- byte-exact on all
    ten public cases through the real claude_11a station.

    The per-round tick interpreter is NOT transcribed yet; the room halts
    after round 1's sentinel.  Its design is fixed and recorded in
    :data:`RING_ORDER` / :func:`_step_main_plan`, and :class:`Tape` is the
    layout tool it is written with.
    """
    from .lllm_fetch import Room

    room = Room(STEP_ROWS, STEP_COLS)
    _step_setup(room)
    _step_round1(room)
    return room


# The six-slot scratch loop the tick interpreter runs on.  Six, not the
# model's five: `K` (the round's remaining tick count) cannot stay in BP,
# because BP is what decodes the op class (`b` then an `m`/`d` staircase),
# and that decode is the only way to branch nine ways while leaving `value`
# untouched in B.  Head slot at the start of every tick is CTRL.
RING_ORDER = ("CTRL", "ADDR", "BI", "AI", "OLD", "K")


def _step_main_plan() -> dict[str, str]:
    """The tick interpreter's register choreography, phase by phase.

    Each value is the opcode tape for that phase (``#N`` = literal N),
    written against :data:`RING_ORDER` with the head slot named in the key.
    Kept as data so the transcription is reviewable before it is placed.
    """
    return {
        "seed[-]": "r M #1 s W s #0 s s s s",
        "round-in[CTRL]": "r M | rs rs rs rs rs | r W s"
                          " | rs | r M s | rs rs | r W s | rs",
        "tick-halt[CTRL]": "r s M #4 W - X",          # <0 live, >=0 frozen
        "tick-fetch[ADDR]": "r s ->REQ s | <-RESP r | M #16 W /",
        "class[.]": "b, then an m/d staircase, one row per class 0..8",
        "space[BI]": "",
        "wall/halt[BI]": "rs rs rs rs | r M #4 + s | rs rs rs rs rs",
        "heading[BI]": "rs rs rs rs | r W s | rs rs rs rs rs",
        "digit[BI]": "rs | r W s | rs rs",
        "M[BI]": "r r s s | rs rs",
        "add[BI]": "r M s r + s | rs rs",
        "sub[BI]": "r M s r - s | rs rs",
        "branchX[BI]": "rs | r s | rs rs | X | r M #1 + M #4 W % s | rs rs rs rs rs",
        "move[CTRL]": "r s b | staircase 0..3 | r M #16N|#1|#16|#1N + s | rs rs rs rs",
        "kcount[CTRL]": "rs rs rs rs rs | r M #1 W - s X",
        "emit[CTRL]": "rs rs rs rs | r s | rs | M #256 + ->REQ s"
                      " | #16 * M <-RESP r + ->DRAW s"
                      " | rs | r s | rs rs rs rs | M #16 * M #9 + s | #1 N s",
    }


# Canvas placement: FETCH on top with its ring relay, STEP below it, the two
# scratch pipes off STEP's right wall, and the four left-wall corridors in
# four dedicated columns (9 = REQ, 7 = RESP, 5 = DRAW, 3 = LOAD) so no two
# ever cross.
STEP_AT = (28, 14)
FETCH_AT = (0, 20)


def build_step_rig() -> str:
    """I -> STEP <-> FETCH+RELAY, STEP -> O capturing the delta stream."""
    from .canvas import Canvas
    from .lllm_fetch import build_fetch, build_relay

    cv = Canvas()
    sr, sc = STEP_AT
    fr, fc = FETCH_AT
    cv.put(fr, fc, build_fetch().render())
    cv.put(sr, sc, build_step_room().render())
    cv.put(fr + 20, fc + 50, build_relay().render())          # FETCH's ring
    cv.put(sr + SCR_OUT_ROW - 1, sc + 80, build_step_relay().render())
    orow, irow = sr + DRAW_ROW - 6, sr + LOAD_ROW + 3
    cv.put(irow - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(orow - 1, 0, ["+-+", "|O|", "+-+"])

    left, right = sc - 1, sc + STEP_COLS + 2
    fleft = fc - 1
    cv.pipe([(sr + REQ_ROW, left), (sr + REQ_ROW, 9), (fr + 2, 9), (fr + 2, fleft)])
    cv.pipe([(fr + 13, fleft), (fr + 13, fleft - 1), (sr - 1, fleft - 1),
             (sr - 1, sc + RESP_COL)])
    cv.cells[(sr - 1, sc + RESP_COL)] = "v"   # terminal bend (cookbook 4)
    cv.pipe([(sr + DRAW_ROW, left), (sr + DRAW_ROW, 5), (orow, 5), (orow, 3)])
    cv.pipe([(irow, 3), (irow, 4), (sr + LOAD_ROW, 4), (sr + LOAD_ROW, left)])
    # FETCH's ring, same shape as build_fetch_rig, shifted with the room.
    cv.pipe([(fr + 2, fc + 47), (fr + 2, fc + 67), (fr + 21, fc + 67),
             (fr + 21, fc + 56)])
    cv.pipe([(fr + 21, fc + 49), (fr + 21, fc + 48), (fr + 5, fc + 48),
             (fr + 5, fc + 47)])
    # STEP's scratch loop: two short legs, so read-after-write latency stays
    # near the relay lap rather than dominating every ring rotation.
    cv.pipe([(sr + SCR_OUT_ROW, right), (sr + SCR_OUT_ROW, sc + 79)])
    cv.pipe([(sr + SCR_OUT_ROW + 1, sc + 86), (sr + SCR_OUT_ROW + 1, sc + 87),
             (sr + SCR_IN_ROW, sc + 87), (sr + SCR_IN_ROW, right)])
    return cv.render()


def oracle_frames(rows: list[str], ks: list[int]) -> list[list[str]]:
    """Frames straight from the ``littleman.llm`` reference interpreter."""
    from .llm import LLM

    machine = LLM.parse(rows)
    out = [machine.render()]
    for k in ks:
        machine.run(int(k))
        out.append(machine.render())
    return out
