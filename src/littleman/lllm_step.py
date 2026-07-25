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
STEP_ROWS, STEP_COLS = 150, 72

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
    for r in range(3, 20):
        room.put(r, 2, "v")
    room.put(20, 2, ">")


def _step_round1(room) -> None:
    """ROUND 1: man_addr into the ring, FETCH ``-1``, then 257 pixels.

    The pixel counter rides in ``B``: ``r + s`` emits ``p + colour`` and
    ```16` + M`` re-forms ``B = p + 16``, so the whole 256-pixel
    loop needs no ring access at all -- man_addr simply parks in the scratch
    loop while it runs.
    """
    room.put(20, 5, "r")                 # man_addr from LOADER
    room.put(20, 46, "s")                # park it in the scratch loop
    room.put(20, 47, "v")                # jog to row 21 for the run east, so
    room.put(21, 47, ">")                # column 3 stays blank at rows 20-22
    # Two-stage ascent.  A single column from row 21 to row 4 would cross the
    # FETCH band (row 10, columns 28..65) and pull every tick's response walk
    # back into ROUND 1; so climb column 60 only as far as row 12, cross west
    # UNDER the band to column 27 -- the one column free for rows 4..21 that
    # lies west of the band -- and finish the climb there.
    room.put(21, 60, "^")
    for r in range(13, 21):
        room.put(r, 60, "^")
    room.put(12, 60, "<")
    room.put(12, 27, "^")
    for r in range(5, 12):
        room.put(r, 27, "^")
    room.put(4, 27, "<")
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
    room.put(19, 3, "v")                 # exit: column 3 is blank at rows
    room.put(SEED_ROW, 3, ">")           # 20..22, so it crosses both walkways
    room.put(19, 57, "<")


TAPE_LO, TAPE_HI = 42, 60   # the scratch-loop tape zone (rows 22+)
# Vertical highways live in columns 61..71, the only band no horizontal
# walkway in the room ever crosses; every phase-to-phase jump uses one.
HW = dict(arm=69, move=66, emit=64, round=63)
# The live arm's ascent back to the FETCH band, and the band's descent to the
# class staircase, are the room's two long vertical wires.  They cannot simply
# be adjacent columns: the ascent spans rows 11..41 and the descent rows
# 12..43, so whichever is further east is cut by the other's feeder run.  The
# descent therefore DOG-LEGS west on row 34 -- above the tick block -- and
# finishes in column 40, which no eastward run in rows 35..43 reaches.
# The resolution is an ORDERING one, not a routing one: the tick block is
# placed BELOW the class staircase, so its two eastward feeders (live and
# frozen) run under the descent instead of through it.  Then the descent can
# be a single straight wire and the ascent the single column east of it.
ASC_COL = 70        # live arm: rows 11..TICK_ROW+5, north to the FETCH band
# The band exit sits as far EAST as the ascent allows, because it is also the
# class staircase's first rung: the staircase steps two columns west per rung,
# so every column it borrows is one the nine arms cannot turn off in.  At 65
# the eight rungs reach column 49 and leave only seven arm columns for eight
# arms; at 67 they reach 51 and leave nine.
DESC_COL = 67       # band exit: rows 12..43, south to the class staircase
ROUND_EXIT_COL = 41  # round-in -> tick: west of the tape zone, so no
                     # staircase rung (columns 42..60) ever crosses it
SEED_ROW, ROUND_ROW = 23, 30
# ROUND-IN's tape is 27 tokens wide, so it wraps to row 33; the tick must
# start strictly below that (see Tape.down_at, which now refuses to "descend"
# upwards rather than dropping the man into the next phase's westward lane).
TICK_ROW = 140
SCR_COL = 42        # first column whose r/s binds the scratch loop (rows 22+)
REQ_MAX_ROW = 11    # last row whose left-wall s reaches REQ rather than DRAW
FROZEN_COL = 67     # frozen tick -> MOVE: clear of every wire below row 44


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
        """Leave the tape: walk on to ``col``, then descend to ``row``.

        ``row`` must lie strictly BELOW the tape's last line.  When it does
        not, the descent is empty and the man runs straight along the target
        row into whatever the next phase placed there -- the characteristic
        silent infinite loop of this room, so it is an error, not a no-op.
        """
        while (col - self.col) * self.dir < 0:
            self._turn()
        if row <= self.row:
            raise ValueError(
                "tape reached row %d; cannot descend to %d" % (self.row, row)
            )
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
    seed = Tape(room, SEED_ROW, TAPE_LO, TAPE_LO, TAPE_HI)
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
    _leave_tape(room, tape, ROUND_EXIT_COL, TICK_ROW)
    _step_tick_halt(room)


def _step_tick_halt(room) -> None:
    """Start of a tick: split the frozen man from the live one.

    ``r s M #4 W -`` leaves ``A = CTRL - 4`` (CTRL = 4*halted + heading), so
    one X separates live (A < 0) from frozen (A >= 0), and the ring is left
    rotated by one with ADDR at the head.
    """
    # ROUND-IN's exit column IS the tape's western margin, so the man drops
    # straight into the tick tape with no westward run to be crossed.
    room.put(TICK_ROW, TAPE_LO - 1, "v")
    room.put(TICK_ROW + 1, TAPE_LO - 1, ">")
    tape = Tape(room, TICK_ROW + 1, TAPE_LO, TAPE_LO, TAPE_HI)
    tape.emit("r", "s", "M", "#4", "W", "-")
    tape.down_at(64, TICK_ROW + 3)
    room.put(TICK_ROW + 3, 64, "<")
    room.put(TICK_ROW + 3, 50, "X")       # west: A<0 -> south, A>0 -> north
    # Frozen (A >= 0): the north arm and the A==0 straight arm converge on
    # column 49 and drop to the countdown; the man does not move this tick.
    room.put(TICK_ROW + 2, 50, "<")
    room.put(TICK_ROW + 2, 49, "v")
    for r in range(TICK_ROW + 3, TICK_ROW + 6):
        room.put(r, 49, "v")
    # The frozen arm crosses BELOW the live arm's ascent, so it must leave on
    # a row the ascent no longer occupies -- hence TICK_ROW + 6, not + 4.
    # ... and rejoins the round at MOVE, not after it: the tick-halt tape
    # already leaves ADDR at the head, which is exactly what MOVE's align tape
    # wants, and MOVE's rung 4 (no ``a``) is the catch-all every frozen CTRL
    # falls through without moving.  The climb is a BLANK corridor: column
    # FROZEN_COL is crossed by five MOVE arms and by kcount, and a man keeps
    # his heading over empty floor, so only the two turns are drawn.
    room.put(TICK_ROW + 6, 49, ">")
    room.put(TICK_ROW + 6, FROZEN_COL, "^")
    room.put(MOVE_ROW, FROZEN_COL, "<")
    # Live (A < 0): east to the northbound fetch highway, which is the LAST
    # column before the wall so no eastward run can be cut short by it.
    room.put(TICK_ROW + 5, 50, ">")
    for r in range(11, TICK_ROW + 6):
        room.put(r, ASC_COL, "^")
    _step_fetch(room)


CLASS_ROW = 44      # first rung of the op-class staircase


def _step_fetch(room) -> None:
    """Op fetch and class decode, on row 11 -- the only band that reaches
    both FETCH ports.

    Walked WEST: read ADDR from the ring and put it straight back, send it
    to FETCH, block on the response, then ``M `16` W /`` splits the frozen
    ``class<<4 | value`` into ``A = class`` and ``B = value``.  ``b`` moves
    the class into BP so the staircase can branch nine ways while `value`
    stays untouched in B for the heading and digit arms.
    """
    room.put(10, ASC_COL, "<")
    room.put(10, 52, "sr")               # walked west: r(ADDR) then s(ADDR)
    room.put(10, 37, "rs")               # walked west: s(REQ) then r(RESP)
    room.put(10, 29, "b/W`61`M")         # walked west: M `16` W / b
    room.put(10, 28, "v")
    room.put(11, 28, ">")
    for r in range(11, CLASS_ROW):
        room.put(r, DESC_COL, "v")
    _step_class(room)


CLASS_RUNGS = 8     # rung r fires on class r+1; rung 0 also catches class 0
ARM_LO = 42         # arms may not run west of the tape zone


def _step_class(room) -> None:
    """The op-class staircase: nine ways out of ``BP``, walked WEST.

    ``b`` has already put the class in ``BP`` and left ``value`` in ``B``,
    which no rung disturbs -- that is the whole reason the decode goes
    through the backpack instead of through ``A``.

    Each rung is ``m a``: decrement, then turn counter-clockwise (west ->
    south) while ``BP`` is still positive.  After rung ``r`` the backpack
    holds ``class - (r+1)``, so the man falls through westward at the first
    rung with ``class <= r+1`` -- rung ``r`` for class ``r+1``, and rung 0
    for classes 0 and 1 together, which the arm splits again on ``A``.

    Rungs step two columns west per row so the southward turn lands exactly
    on the next rung's ``<``; the room is 8 rungs deep and 16 columns wide.
    """
    room.put(CLASS_ROW, DESC_COL, "<")
    for r in range(CLASS_RUNGS):
        row, col = CLASS_ROW + r, DESC_COL - 1 - 2 * r
        room.put(row, col - 1, "am")      # walked west: m at col, a at col-1
        if r + 1 < CLASS_RUNGS:
            room.put(row + 1, col - 1, "<")
    _step_arms(room)


# Every arm leaves the ring rotated FIVE slots on from the staircase's head
# (``BI``), i.e. with ``ADDR`` at the head: five is the cheapest rotation that
# both reaches ``CTRL`` and writes it, and paying the remaining lap once in
# the shared MOVE row is far cheaper than paying it in every arm.
MERGE_COL, MOVE_ROW = 62, 70
ARM_MERGE = 68              # the class arms' own merge, east of MOVE's
ARM_HI = 66                 # ... so their tapes get the width class 7 needs
_R = list("rs")             # one ring relay
# rung -> (turn column, tape row, opcode tape).  Rung r fires on class r+1
# (rung 0 also on class 0).  EVERY tape must leave the ring rotated five slots
# on from the staircase's head (BI), i.e. with ADDR at the head, because MOVE's
# align tape is shared and starts from there.  ``value`` rides in B untouched.
ARM_SPEC = {
    0: (42, 69, []),                                      # space AND wall
    1: (43, 67, _R * 4 + ["r", "W", "s"]),                # heading: CTRL=value
    2: (44, 65, _R + ["r", "W", "s"] + _R * 3),           # digit:   AI=value
    3: (45, 63, list("rrss") + _R * 3),                   # M:  BI=AI, AI=AI
    4: (46, 61, list("rMsr+s") + _R * 3),                 # add: AI=AI+BI
    5: (47, 59, list("rMsr-s") + _R * 3),                 # sub: AI=AI-BI
    6: (48, 57, []),                                      # branch X: TODO
    7: (49, 55, _R * 4 + ["r", "M", "4", "+", "s"]),      # halt: CTRL |= 4
}


def _step_arms(room) -> None:
    """The class arms, and their merge into the shared MOVE row.

    Column order is the whole trick: the arm that turns off FURTHEST WEST
    gets the DEEPEST tape row.  A tape only ever runs east, so it can never
    meet a descent that is west of its own column, and a descent can never
    meet a tape that is below its own foot.  That one rule makes all four
    arms planar without a single jog.
    """
    for rung, (col, arm_row, tokens) in ARM_SPEC.items():
        for r in range(CLASS_ROW + rung, arm_row):
            room.put(r, col, "v")
        room.put(arm_row, col, ">")
        if tokens:
            Tape(room, arm_row, col + 1, col + 1, ARM_HI).emit(*tokens)
        elif rung:
            _step_branch(room, arm_row, col + 1)
        else:
            _step_wall(room, arm_row, col + 1)
    for r in range(min(s[1] for s in ARM_SPEC.values()), MOVE_ROW):
        room.put(r, ARM_MERGE, "v")
    room.put(MOVE_ROW, ARM_MERGE, "<")    # west, on to MOVE's own merge
    _step_move(room)


def _step_wall(room, row: int, col: int) -> None:
    """Rung 0 carries TWO classes -- 0 (space) and 1 (wall) -- so it splits.

    ``b``/``m``/``a`` never touch A, so A is still the class here; ``N`` makes
    it 0 or -1 and one ``X`` separates them.  Negated deliberately: rung 0 is
    the DEEPEST arm, so the spare row is the one ABOVE it, and only a negative
    A turns an eastbound man north.

    Wall is the LLLM freeze: the man has already been moved onto the wall cell
    by the previous tick's blind step, so setting the halt bit is the whole of
    it -- he stays drawn there, on the wall, in every later frame.
    """
    room.put(row, col, "N")                   # A = -class
    room.put(row, col + 1, "X")
    room.put(row, col + 2, "rs" * 5)          # class 0: a bare lap, no write
    room.put(row - 1, col + 1, ">")           # class 1: north onto the spare
    room.put(row - 1, col + 2, "rs" * 4)      # row, then CTRL |= 4 as class 8
    room.put(row - 1, col + 10, "rM4+s")


def _step_branch(room, row: int, col: int) -> None:
    """Class 7 (``X``): turn the interpreted man by ``sign(AI)``.

    The only arm that is not a straight tape.  ``AI`` is read into A and left
    in place, then one ``X`` fans three ways; because the ROWS BETWEEN the
    arms are empty (each arm owns an odd row, so the even ones are spare),
    the two sign arms simply step off onto the row above and the row below
    and run east on their own, rejoining at the shared merge column.

    A frozen man never ticks, so ``CTRL`` is 0..3 here and the halt bit needs
    no masking: ``(CTRL + 1) % 4`` and ``(CTRL + 3) % 4`` are the whole job.
    """
    room.put(row, col, "rsrs")                # relay to AI, read it, keep it
    xcol = col + 4
    room.put(row, xcol, "X")
    room.put(row, xcol + 1, "rsrsrs")         # AI == 0: no turn, just the lap
    for drow, step in ((row - 1, "3"), (row + 1, "1")):
        room.put(drow, xcol, ">")             # <0 counter-clockwise (north),
        room.put(drow, xcol + 1, "rsrs")      # >0 clockwise (south)
        room.put(drow, xcol + 5, "rM" + step + "+M4W%s")


MOVE_CLASS_ROW = 76         # first rung of the heading staircase
MOVE_MERGE, KCOUNT_ROW = 69, 132
# Below row 70 the only wires east of the tape zone are MERGE_COL and
# MOVE_MERGE, so the arm tapes may run out to column 64 -- they need the slack
# because Tape shifts every literal off any column that already holds a
# backtick, and by this depth the room has a lot of them.
MOVE_HI = 68                # one clear column between the tapes and the merge
# rung -> (turn column, tape row, the delta tape).  Rung r fires on CTRL == r
# because the align tape leaves ``BP = CTRL + 1``; rung 4 has no ``a``, so
# every frozen CTRL (4..7) falls through it and the man does not move.
MOVE_SPEC = {
    # The align tape leaves B = 1, so E and W need no literal at all -- which
    # matters because rung order fixes the turn columns west-to-east, and the
    # later rungs have the least tape left to shift a literal into.
    0: (42, 122, ["r", "M", "#16", "N", "+", "s"]),     # N: ADDR - 16
    1: (43, 112, ["r", "+", "s"]),                      # E: ADDR + 1
    2: (44, 102, ["r", "M", "#16", "+", "s"]),          # S: ADDR + 16
    3: (45, 92, ["r", "-", "s"]),                       # W: ADDR - 1
    4: (46, 82, list("rs")),                            # frozen: no move
}
# Each arm makes exactly ONE ring pull, and the four that finish the lap back
# to CTRL are paid once on the shared KCOUNT row -- keeping them in the arms
# pushed every literal past the room's crowded backtick columns and wrapped
# the tapes westward across their own descents.
MOVE_TAIL = list("rs") * 4


def _free_literal(room, digits: str, start: int, hi: int) -> int:
    """First column at or after ``start`` where ``\\`digits\\`` may sit.

    A literal's two backticks must each land in a column that holds no other
    backtick, or the parser pairs them vertically with the wrong partner.
    :class:`Tape` shifts for this too, but by MOVE's depth the room is dense
    enough that its shift-then-wrap loop thrashes; a straight-line phase is
    better served by choosing the column up front.
    """
    used = {c for (_, c), v in room.cells.items() if v == "`"}
    width = len(digits) + 2
    for col in range(start, hi - width + 2):
        if col not in used and col + width - 1 not in used:
            return col
    raise ValueError("no room for `%s` in %d..%d" % (digits, start, hi))


def _emit_row(room, row: int, col: int, tokens, hi: int) -> int:
    """Place a straight-line opcode run on one row; ``#N`` is the literal N."""
    for token in tokens:
        if token.startswith("#"):
            digits = token[1:]
            col = _free_literal(room, digits, col, hi)
            room.put(row, col, "`" + digits + "`")
            col += len(digits) + 2
        else:
            room.put(row, col, token)
            col += 1
    return col


def _step_move(room) -> None:
    """Blind step by heading -- the NEXT fetch is what discovers a wall.

    ``r s M #1 + b`` leaves ``BP = CTRL + 1``, which is exactly the offset
    the ``m a`` staircase needs: rung ``r`` fires on ``CTRL == r`` with no
    off-by-one and no merged pair, unlike the class staircase's rung 0.
    """
    room.put(MOVE_ROW, MERGE_COL, "<")
    room.put(MOVE_ROW, TAPE_LO, "v")
    room.put(MOVE_ROW + 1, TAPE_LO, ">")
    tape = Tape(room, MOVE_ROW + 1, TAPE_LO + 1, TAPE_LO + 1, MOVE_HI)
    tape.emit(*list("rs") * 5, "r", "s", "M", "#1", "+", "b", "-", "M")
    tape.down_at(MERGE_COL, MOVE_CLASS_ROW)
    room.put(MOVE_CLASS_ROW, MERGE_COL, "<")
    for r in range(4):                        # rung 4 needs no cells at all
        row, col = MOVE_CLASS_ROW + r, MERGE_COL - 1 - 2 * r
        room.put(row, col - 1, "am")
        room.put(row + 1, col - 1, "<")
    for r, (col, arm_row, tokens) in MOVE_SPEC.items():
        room.put(MOVE_CLASS_ROW + r, col, "v")
        for rr in range(MOVE_CLASS_ROW + r + 1, arm_row):
            room.put(rr, col, "v")
        room.put(arm_row, col, ">")
        _emit_row(room, arm_row, col + 1, tokens, MOVE_HI)
    for r in range(min(s[1] for s in MOVE_SPEC.values()), KCOUNT_ROW):
        room.put(r, MOVE_MERGE, "v")
    _step_kcount(room)


KLOOP_COL, KLOOP_ROW = 68, 138      # X's "more ticks" exit, back to the tick


def _step_kcount(room) -> None:
    """Count the round's ticks down and either loop or finish.

    ``r M #1 W - s X`` leaves ``A = K - 1`` with the decremented count
    already back in the ring, so one X both branches and commits.  Walked
    EAST: ``A > 0`` turns clockwise (south, another tick), ``A == 0`` runs
    straight on to EMIT.  The leading ``rs`` runs are MOVE's shared tail --
    see :data:`MOVE_TAIL` -- plus the five that reach ``K``.
    """
    room.put(KCOUNT_ROW, MOVE_MERGE, "<")
    room.put(KCOUNT_ROW, TAPE_LO, "v")
    room.put(KCOUNT_ROW + 1, TAPE_LO, ">")
    # Two rows: the pure rotation first, then the arithmetic.  One row cannot
    # hold both once the literal has been shifted clear of the room's used
    # backtick columns.
    _emit_row(room, KCOUNT_ROW + 1, TAPE_LO + 1,
              MOVE_TAIL + list("rs") * 5, MOVE_HI)
    room.put(KCOUNT_ROW + 1, MOVE_MERGE, "v")
    room.put(KCOUNT_ROW + 2, MOVE_MERGE, "<")
    room.put(KCOUNT_ROW + 2, TAPE_LO, "v")
    room.put(KCOUNT_ROW + 3, TAPE_LO, ">")
    end = _emit_row(room, KCOUNT_ROW + 3, TAPE_LO + 1,
                    ["r", "M", "#1", "W", "-", "s", "X"], MOVE_HI)
    # A > 0: south, west along a clear row, and back onto ROUND-IN's own
    # descent wire, which already runs all the way down to the tick tape.
    xcol = end - 1                        # the X itself is the branch point
    for r in range(KCOUNT_ROW + 4, KLOOP_ROW):
        room.put(r, xcol, "v")
    room.put(KLOOP_ROW, xcol, "<")
    room.put(KCOUNT_ROW + 3, end, "v")    # A == 0: drop to EMIT's floor
    _step_emit(room, end)


# EMIT is three segments because its colour fetch is a REQ/RESP pair (row
# <= REQ_MAX_ROW) while all three DRAW sends must sit BELOW the REQ/DRAW
# Voronoi midpoint (row 11).  Getting from the kcount block at row 135 up to
# the REQ band and back down is the room's longest journey, and exactly three
# corridors survive every existing wire and every existing WALK:
#
#   * column ``EMIT_HW`` -- no run in the room reaches past column 70, so it
#     is the one column that is neither occupied nor crossed at any row;
#   * ``EMIT_FLOOR``/+1 -- below the tick block, the only clear east-west rows;
#   * column ``EMIT_DESC_COL`` -- east of row 12's ROUND 1 crossing (which
#     ends at column 60) and west of DESC_COL, clear from row 9 to row 30.
#
# The long legs are deliberately left BLANK: a man keeps his heading across
# empty floor, so a blank corridor crosses every horizontal walkway it meets
# without diverting either man.  Only the turns are drawn.
EMIT_FLOOR = 147            # emit-a: below every wire, so the ring lap is free
EMIT_HW = 71                # the one column no run in the room ever reaches
EMIT_REQ_ROW = 8            # <= REQ_MAX_ROW, and clear of the row-10 band
EMIT_DESC_COL = 61          # REQ band -> the DRAW rows
EMIT_DRAW_ROW = 24          # first of four rows nothing else uses
EMIT_SCR_LO = 42            # SCR_COL: r/s east of it reach the scratch loop
EMIT_PORT_HI = 41           # ... and west of it, REQ/RESP/DRAW


def _step_emit(room, col: int) -> None:
    """K == 0: colour-fetch OLD, draw old and new, commit, next round."""
    _emit_a(room, col)
    _emit_b(room)
    _emit_c(room)


def _emit_a(room, col: int) -> None:
    """Ring lap to OLD, then ``A = old + 256`` with ``old`` parked in B.

    Walked WEST on the room's floor, where the whole width is free, so the
    literal picks unused backtick columns instead of fighting for them.
    """
    room.put(EMIT_FLOOR, col, "<")
    room.put(EMIT_FLOOR, 45, "srsrsrsrsr")   # walked west: (r s) x 5 -> OLD
    room.put(EMIT_FLOOR, 44, "M")            # B = old
    room.put(EMIT_FLOOR, 23, "`652`")        # walked west: the literal 256
    room.put(EMIT_FLOOR, 22, "+")            # A = old + 256
    room.put(EMIT_FLOOR, 21, "v")
    room.put(EMIT_FLOOR + 1, 21, ">")        # the floor's return leg, east to
    room.put(EMIT_FLOOR + 1, EMIT_HW, "^")   # the one uncrossed column
    room.put(EMIT_REQ_ROW, EMIT_HW, "<")


def _emit_b(room) -> None:
    """The colour fetch: ``old`` becomes ``old*16`` while RESP is in flight.

    ``W`` recovers ``old`` from B the moment the request is away, so the ring
    is read once for the whole of EMIT rather than once per DRAW send.
    """
    room.put(EMIT_REQ_ROW, 39, "MWs")        # walked west: s(REQ) W M
    room.put(EMIT_REQ_ROW, 34, "`61`")       # walked west: the literal 16
    room.put(EMIT_REQ_ROW, 32, "M*")         # walked west: * M -> B = old*16
    room.put(EMIT_REQ_ROW, 31, "v")
    room.put(EMIT_REQ_ROW + 1, 31, ">")
    room.put(EMIT_REQ_ROW + 1, 32, "r+")     # r(RESP) = colour, A = old*16 + c
    room.put(EMIT_REQ_ROW + 1, EMIT_DESC_COL, "v")


def _emit_c(room) -> None:
    """Restore-old, draw-new, commit -- then hand back to ROUND-IN.

    Four rows, alternating west (the three DRAW sends, all at columns < 42 so
    they cannot reach for the scratch loop) and east (the ring laps, all at
    columns >= 42 so they cannot reach for DRAW).  The exit runs east into
    SEED's own descent wire, which already lands on ROUND-IN's row.
    """
    row = EMIT_DRAW_ROW
    room.put(row, EMIT_DESC_COL, "<")
    room.put(row, 30, "s")                   # DRAW: old pixel repainted
    room.put(row, 29, "v")
    room.put(row + 1, 29, ">")
    room.put(row + 1, 42, "rsrsrs")          # ring lap to ADDR, and read it
    room.put(row + 1, 48, "v")
    room.put(row + 2, 48, "<")
    room.put(row + 2, 47, "M")
    room.put(row + 2, 30, "`61`")            # walked west: the literal 16
    room.put(row + 2, 26, "+9M*")            # walked west: * M 9 + -> addr*16+9
    room.put(row + 2, 22, "sN1s")            # walked west: DRAW man, DRAW -1
    room.put(row + 2, 21, "v")
    room.put(row + 3, 21, ">")
    room.put(row + 3, 42, "rsrsrsrs")        # finish the lap: head back at CTRL


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
    _step_seed(room)
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
        # CORRECTED, and the only phase still unplaced.  The colour fetch is
        # a REQ/RESP pair, so it MUST sit on a row <= REQ_MAX_ROW while every
        # DRAW send MUST sit on a row above it -- EMIT is therefore three
        # segments, not one row.  B carries `old` across the round trip and
        # is re-shaped into `old*16` while the response is still in flight,
        # so the ring is read once, not twice.
        "emit-a[CTRL] rows>11": "rs rs rs rs | r s | M #256 +",
        "emit-b[K] rows<=11": "->REQ s | W M #16 * M | <-RESP r | +",
        "emit-c[K] rows>11": "->DRAW s | rs rs | r s | M #16 * M #9 +"
                             " | ->DRAW s | #1 N ->DRAW s | rs rs rs rs",
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
