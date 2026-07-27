"""Analyze whether a room's interior can be reflowed into a different aspect
ratio while preserving the little man's walk exactly.

This module builds a directed graph over little-man states ``(x, y,
direction)`` induced by the glyph semantics of a room interior (see
``src/littleman/sim.py`` for the authoritative step rules), then computes,
for each horizontal cut line, how many distinct path "strands" cross that
line. Cut lines with few crossing strands are cheap places to fold the
interior into more columns (trading height for width) without disturbing
the man's walk, because only the crossing strands need to be rerouted.

Coordinates: ``x`` is the column, ``y`` is the row, both 0-based within the
interior (``interior_lines[y][x]``). ``direction`` is one of
``sim.UP/DOWN/LEFT/RIGHT`` -- each a ``(row_delta, col_delta)`` pair reused
verbatim from ``sim`` so this module can never drift from the simulator's
own convention.

Glyph handling (mirrors ``sim.Machine._execute`` exactly):

* ``>``, ``<``, ``^``, ``v``/``V`` set direction unconditionally.
* ``H`` halts the man: a dead end, no outgoing edge.
* Everything else sim.py recognises as a valid instruction (constants,
  hands, arithmetic, bitwise, backpack bookkeeping, pipe I/O ``r/R/s/S/q``,
  backticks, digits, ``.``/space/``@``) leaves direction unchanged. Pipe
  blocking can delay *when* a step happens but never changes *what* the next
  state is, and this graph is not time-accurate, so blocking ops are treated
  as plain pass-throughs.
* ``X``, ``d``, ``a``, ``x`` turn conditionally on registers (``A`` or
  ``BP``) this module does not track, and ``U`` turns away from whichever
  external pipe fed it (room-exterior information not available from
  interior text alone). For all five, every direction the glyph could ever
  produce becomes a separate outgoing edge (see ``_branches``). This is a
  deliberate over-approximation: the returned graph is a superset of any one
  concrete run's reachable states, so crossing counts derived from it are
  safe upper bounds -- if this analysis says a cut line is cheap, it is
  cheap no matter what the program's actual data does.
* Any other character is sim's "bad-op" load error: the program halts on
  the spot, so it is also a dead end here.
* A move that would leave the interior is sim's "wall" error (the program
  halts): also a dead end, since interior_lines is exactly the walkable
  area bounded by the room's real walls.

Public API:
    walk_graph(interior_lines) -> graph over (x, y, direction) states
    strand_profile(interior_lines) -> per-cut-line crossing counts
    fold_points(interior_lines, max_strands=1) -> cheap cut lines
"""

from __future__ import annotations

from collections import deque

from .sim import CLOCKWISE, COUNTERCW, DOWN, LEFT, RIGHT, UP

# Reused verbatim from sim.py so movement math can never drift from the
# simulator's own (row_delta, col_delta) convention.
DIRECTIONS = (UP, DOWN, LEFT, RIGHT)
DIR_LABEL = {UP: "^", DOWN: "v", LEFT: "<", RIGHT: ">"}

_ARROW_DIR = {">": RIGHT, "<": LEFT, "^": UP, "v": DOWN, "V": DOWN}

# Halts the man outright: dead end, no outgoing edge.
_HALTING = frozenset("H")

# Every other glyph sim.py's Machine._execute recognises as valid and that
# does NOT change direction (constants/backticks/digits, hands, arithmetic,
# bitwise, backpack bookkeeping short of d/a/x, pipe I/O short of U, and the
# plain no-ops space/./@).
_PASSTHROUGH = (
    set(" .@`")
    | set("0123456789")
    | set("MW+-*/%N&|~{}")
    | set("bmq]")
    | set("sSrR")
)


def _branches(ch: str, d: tuple[int, int]):
    """Outgoing directions for a glyph whose turn depends on register state
    this module does not track. Returns ``None`` if `ch` is not such a
    glyph (i.e. the caller should fall through to arrow/pass-through/dead-end
    handling instead).
    """
    if ch == "X":  # turn by sign(A): CW, CCW, or straight
        return {CLOCKWISE[d], COUNTERCW[d], d}
    if ch == "d":  # turn CW if BP > 0, else straight
        return {CLOCKWISE[d], d}
    if ch == "a":  # turn CCW if BP > 0, else straight
        return {COUNTERCW[d], d}
    if ch == "x":  # always turns: CW or CCW depending on BP's low bit
        return {CLOCKWISE[d], COUNTERCW[d]}
    if ch == "U":  # turns away from whichever incoming pipe it read
        return set(DIRECTIONS)  # room-exterior info unavailable; conservative
    return None


def _pad(interior_lines):
    """Left-justify every row to the width of the widest row.

    Ragged input (short trailing rows, e.g. after slicing text out of a
    .man file without re-padding) would otherwise make column indexing
    inconsistent between rows.
    """
    lines = list(interior_lines)
    width = max((len(line) for line in lines), default=0)
    return [line.ljust(width) for line in lines]


State = tuple[int, int, tuple[int, int]]


def walk_graph(interior_lines) -> dict[State, set[State]]:
    """Build the directed graph of (x, y, direction) states reachable from
    every ``@`` in the interior, following sim.py's Machine._execute
    semantics for direction changes and Machine._tick's movement step
    (execute, then move one cell in the resulting direction).

    Returns ``{state: set(next_states)}`` covering every reachable state,
    including dead ends (mapped to an empty set): ``H``, a bad-op glyph, or
    a move that would leave the interior.
    """
    lines = _pad(interior_lines)
    height = len(lines)
    width = len(lines[0]) if height else 0

    starts = [
        (x, y, RIGHT)  # a little man always begins facing right
        for y in range(height)
        for x in range(width)
        if lines[y][x] == "@"
    ]

    graph: dict[State, set[State]] = {}
    seen: set[State] = set(starts)
    queue: deque[State] = deque(starts)

    while queue:
        state = queue.popleft()
        x, y, d = state
        if state in graph:
            continue
        ch = lines[y][x]
        out: set[State] = set()
        graph[state] = out
        if ch in _HALTING:
            continue
        out_dirs = _branches(ch, d)
        if out_dirs is None:
            if ch in _ARROW_DIR:
                out_dirs = {_ARROW_DIR[ch]}
            elif ch in _PASSTHROUGH:
                out_dirs = {d}
            else:
                continue  # sim's "bad-op": program errors out here
        for nd in out_dirs:
            nx, ny = x + nd[1], y + nd[0]
            if not (0 <= nx < width and 0 <= ny < height):
                continue  # sim's "wall" error: program errors out
            nxt = (nx, ny, nd)
            out.add(nxt)
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)

    return graph


def strand_profile(interior_lines):
    """For each horizontal cut line ``y`` (between row ``y - 1`` and row
    ``y``), report how many distinct ``(column, direction-of-travel)``
    strands cross it -- i.e. how many *targets* of a vertical (UP/DOWN)
    move in the walk graph land on the other side of that boundary. Two
    edges that both arrive at the same ``(column, direction)`` are the same
    physical strand (a single cell can only be walked in a given direction
    as one lane) and are counted once.

    Returns a list of ``(y, crossing_count, crossing_columns)`` for
    ``y in range(1, height)``, sorted by ``y``. ``crossing_columns`` is a
    sorted list of ``(x, direction_label)`` pairs, with ``direction_label``
    in ``{"^", "v"}`` for an UP/DOWN crossing respectively.
    """
    lines = _pad(interior_lines)
    height = len(lines)
    graph = walk_graph(lines)

    crossings: dict[int, set[tuple[int, str]]] = {y: set() for y in range(1, height)}
    for (_x, y, _d), nexts in graph.items():
        for nx, ny, nd in nexts:
            if ny == y + 1:
                crossings[ny].add((nx, DIR_LABEL[nd]))
            elif ny == y - 1:
                crossings[y].add((nx, DIR_LABEL[nd]))

    profile = []
    for y in range(1, height):
        cols = sorted(crossings[y])
        profile.append((y, len(cols), cols))
    return profile


def fold_points(interior_lines, max_strands: int = 1):
    """Cut lines cheap enough to fold: crossing_count <= max_strands.

    Each crossing strand must be rerouted when folding at that line, so a
    cut line with <= max_strands crossings costs at most that many reroutes.
    Returns a sorted list of qualifying ``y`` values.
    """
    return [
        y
        for (y, count, _cols) in strand_profile(interior_lines)
        if count <= max_strands
    ]
