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


def build_step_room() -> str:
    """The STEP room as littleman ASCII -- phase 2, not yet transcribed.

    Blocked by design, not by effort: the integration rig this transcription
    is validated against needs ``littleman.lllm_fetch`` (claude_11a), which
    is absent.  :class:`StepModel` is the finished, gate-passing spec of
    what this room must do.
    """
    raise NotImplementedError(
        "phase 2 not reached: src/littleman/lllm_fetch.py (claude_11a) absent"
    )


def oracle_frames(rows: list[str], ks: list[int]) -> list[list[str]]:
    """Frames straight from the ``littleman.llm`` reference interpreter."""
    from .llm import LLM

    machine = LLM.parse(rows)
    out = [machine.render()]
    for k in ks:
        machine.run(int(k))
        out.append(machine.render())
    return out
