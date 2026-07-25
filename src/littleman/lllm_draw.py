"""LLLM DRAW subsystem: packed delta tokens -> LM-75 frames (claude_10).

Frozen EXEC -> DRAW interface (one dedicated pipe, one token per value):

* ``t in [0, 4095]``  paint: ``addr = t // 16`` (canvas/display address,
  row-major 0..255), ``color = t % 16``.
* ``t < 0``           COMMIT: SWAP=1 (commit the frame, keep the buffer).

DRAW is a pure stream transducer -- it knows nothing about rounds.  Its
Python oracle is ``lllm_step.frames_from_deltas``.

Structure (the block the assembler lifts is DIST + the three drivers)::

    EXEC ->(deltas)-> [DIST] -> [ADDRDRV] -> display TOP    (addr)
                                     |
                                     +----> [DATADRV] -> display LEFT (color)
                                                 |
                                                 +-> [SWAPDRV] -> BOTTOM

ADDRDRV/DATADRV/SWAPDRV and :func:`place_display_block` are copied from
``littleman.snake`` (live on the server at 17/17); their race tuning is
load bearing and is NOT touched: ADDRDRV's lap (46 ticks) exceeds
DATADRV's (40), so the chain is rate limited by ADDR and pixel i's DATA
stays ahead of pixel i+1's ADDR instead of drifting two ticks per pixel;
the DATA pipe's detour and the long SWAP pipe under the display keep
every commit strictly behind the frame's last DATA.

ONE DOCUMENTED DEVIATION from the work order's prose.  The order sketches
DIST as a three-pipe splitter ("send addr, W, send color") *and* requires
the Snake drivers verbatim.  Those two cannot both hold: the Snake
drivers are a serial demux **chain** -- each one forwards the whole token
to the next (``s`` at rel (2,4)) and extracts only its own field with its
own ``M `16` W /`` -- so ADDRDRV fed a bare ``addr`` would emit
``(addr-1)//16``, and a driver with a single outgoing pipe would push the
raw token onto the display's ADDR pipe.  The split therefore stays where
it is proven, inside the drivers, and DIST is the adapter that makes the
frozen interface meet them: Snake's drivers want ``T = 16*addr+color+1``,
i.e. exactly ``t + 1``, with negatives passed through untouched.  DIST
consequently has one outgoing pipe, and the binding audit is *widened*
rather than dropped: every ``s``/``r`` in DIST and in all three drivers is
asserted against ``ir_export.machine_ir``'s resolution map (7 sends /
4 reads), which is the property the work order was buying.
"""

from __future__ import annotations

from .canvas import Canvas
from .snake import Box

DISPLAY = 16
MAN_COLOR = 9

# rig placement of the lifted block: row >= 10 (the driver stack rises 9
# rows above DIST), col 6 leaves room for the 3x3 I room and its pipe.
DRAW_ROW = 10
DRAW_COL = 6


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


def build_dist() -> list[str]:
    """DIST: the frozen EXEC token stream -> the Snake driver chain.

    ``r`` then a sign ``X``.  ``t`` is a *packed* token so ``t = 0`` is a
    legal pixel (addr 0, colour 0): the X is a genuine three-way split and
    the zero arm (straight, then ``v``) merges into the paint lane one row
    down, the standard cookbook section 3 merge.

    * paint arm  (t >= 0): ``M 1 +`` -> send ``t+1``.  The drivers undo the
      +1 with their own ``M 1 W -`` and split it with ``M `16` W /``, so
      addr = t//16 and colour = t%16 exactly as frozen.
    * commit arm (t < 0): send ``t`` unchanged; ADDRDRV and DATADRV relay
      negatives on their short arms and SWAPDRV turns it into SWAP=1.

    One outgoing pipe (the chain head), one incoming (from EXEC / the rig's
    I room), so both ``s`` cells and the ``r`` are unambiguous -- asserted
    against the engine's own resolution map, never by hand.
    """
    b = Box()
    for (r, c), ch in {
        # commit arm: X ccw (up) -> west along row 1, send, drop home
        (1, 4): "<", (1, 3): "s", (1, 1): "v",
        # head: read, sign test.  t>0 cw (down) -> (3,4); t==0 straight -> v
        (2, 1): ">", (2, 2): "@", (2, 3): "r", (2, 4): "X", (2, 5): "v",
        # paint arm: merge, +1, send, return west along row 4 and up col 1
        (3, 4): ">", (3, 5): ">", (3, 6): "M", (3, 7): "1", (3, 8): "+",
        (3, 9): "s", (3, 10): "v",
        (4, 10): "<", (4, 1): "^",
        # pad the room out to the width Snake's token pipe leaves from
        (1, 14): " ",
    }.items():
        b.put(r, c, ch)
    return b.room()


def place_display_block(canvas: Canvas, row: int, col: int) -> None:
    """DIST + driver chain + 16x16 display, DIST top-left at (row, col).

    Copied from ``snake.place_display_block``; the ONLY change is that
    DIST stands where Snake's ring-side TOKENSPLIT stood (same 16-column
    width, so every pipe below is byte-identical, including the two tuned
    detours).  Requires row >= 10 (the driver stack extends 9 rows up).

    External connections:
      * token in: DIST LEFT wall row (row+2)
    Block bounding box: rows row-9 .. row+16, cols col .. col+63.
    """
    R, C = row, col
    canvas.put(R, C, build_dist())              # rows R..R+5,  cols C..C+15
    canvas.put(R - 7, C + 18, build_addrdrv())  # rows R-7..R-3, cols C+18..C+41
    canvas.put(R, C + 19, build_datadrv())      # rows R..R+4,  cols C+19..C+39
    canvas.put(R + 7, C + 20, build_swapdrv())  # rows R+7..R+11, cols C+20..C+25
    display = (
        ["+" + "=" * DISPLAY + "+"]
        + [":" + " " * DISPLAY + ":" for _ in range(DISPLAY)]
        + ["+" + "=" * DISPLAY + "+"]
    )
    canvas.put(R - 3, C + 46, display)          # rows R-3..R+14, cols C+46..C+63
    # token stream: DIST top col 13 -> ADDRDRV left row 2
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
    # every pixel one cell left).  Detour length tuned in Snake's tests.
    canvas.pipe([(R + 3, C + 40), (R + 3, C + 41), (R + 15, C + 41),
                 (R + 15, C + 44), (R + 5, C + 44), (R + 5, C + 45)])
    # SWAP: SWAPDRV right row 1 -> under the display -> display bottom wall
    canvas.pipe([(R + 8, C + 26), (R + 8, C + 27), (R + 16, C + 27),
                 (R + 16, C + 50), (R + 15, C + 50)])


def build_draw_rig() -> str:
    """Test rig: 3x3 ``I`` room -> DIST -> drivers -> 16x16 display.

    No output room: frame-judged problems must emit no integer output.
    The lifted block is everything from ``place_display_block``; the rig
    only adds ``I`` and the one pipe into DIST's left wall.
    """
    canvas = Canvas()
    place_display_block(canvas, DRAW_ROW, DRAW_COL)
    canvas.put(DRAW_ROW + 1, 0, ["+-+", "|I|", "+-+"])
    canvas.pipe([(DRAW_ROW + 2, 3), (DRAW_ROW + 2, DRAW_COL - 1)])
    return canvas.render()


# ------------------------------------------------------- EXEC-side grammar
def frame_pixels(frame: list[str]) -> list[int]:
    """A 16-row hex frame as 256 colour values in canvas order."""
    return [int(ch, 16) for row in frame for ch in row]


def frame_deltas(prev: list[int] | None, cur: list[int]) -> list[int]:
    """Packed tokens painting ``cur`` given the buffer holds ``prev``.

    Frame 1 (``prev is None``) is all 256 pixels; a later frame is the
    changed cells only -- at most two, and emitted **restore first** (the
    cell the man left goes back to its static colour before the cell it
    entered turns 9), which is the order EXEC emits and the order that
    keeps a single-cell step from ever blanking the man.
    """
    if prev is None:
        return [addr * DISPLAY + color for addr, color in enumerate(cur)]
    changed = [a for a, (p, c) in enumerate(zip(prev, cur)) if p != c]
    changed.sort(key=lambda a: cur[a] == MAN_COLOR)
    return [a * DISPLAY + cur[a] for a in changed]


def delta_stream(frames: list[list[str]]) -> list[list[int]]:
    """One token list per frame: paints then the negative commit sentinel."""
    out: list[list[int]] = []
    prev: list[int] | None = None
    for frame in frames:
        cur = frame_pixels(frame)
        out.append(frame_deltas(prev, cur) + [-1])
        prev = cur
    return out


def draw_rounds(frames: list[list[str]]) -> list[dict]:
    """``judge_case`` rounds: each frame's tokens in, that frame out."""
    return [
        {"in": tokens, "frames": [frame]}
        for tokens, frame in zip(delta_stream(frames), frames)
    ]
