"""Fold pathfinder's giant room[0] into a serpentine multi-column layout.

`submissions/pathfinder/pathfinder_02.man` has one room (`layout.rooms[0]`)
that is 181 x 1683 interior and only ~1.7% occupied; it is the entire reason
the machine's bounding box is 1877 tall, and score is
`max(width, height)**2 * avgTicks`. `room_reflow.strand_profile` finds cheap
horizontal cut lines -- rows where few walk-graph edges cross -- so the
interior can be split into several shorter columns placed side by side
instead of one tall column, without changing the man's walk.

Columns must alternate orientation (boustrophedon) so consecutive columns
meet with a SHORT sideways hop instead of a long climb back to the top of
the next column. The obvious recipe -- reverse row order, swap `v`<->`^`,
leave everything else (`<`,`>`,`X`,`d`,`a`,`x`) unchanged -- is WRONG
whenever the folded region contains a register-conditioned turn (`X`, `d`,
`a`, or `x`): a single-axis mirror REVERSES CHIRALITY, so a turn defined as
"clockwise when A > 0" becomes semantically counter-clockwise once mirrored,
and there is no same-glyph fix (proved against `sim.py`'s CLOCKWISE/
COUNTERCW tables -- see the fold log). pathfinder's room 0 has exactly this
problem: it contains a 33-cell 'X' + 33-cell 'd' "decision ladder" at column
159, spread across every candidate band.

A full 180-DEGREE ROTATION (reverse both rows AND columns) is
chirality-PRESERVING (it is two reflections composed, i.e. orientation
preserving), so `X`/`d`/`a`/`x` need NO substitution at all -- only the 4
arrow glyphs need swapping pairwise. This module uses that rotation, not a
plain mirror.

The band that contains the room's ORIGINAL bottom wall (where every
external pipe attaches) is always kept UNROTATED and placed in the room's
ORIGINAL column range, so external pipes never need rerouting: shrinking
room 0's height by `d` rows and translating every other room, plus every
pipe's cells, by `(-d, 0)` reproduces every pipe at EXACTLY its original
length (see `fold_log.md` for the arithmetic proof; `pathfinder_fold_build.py`
in the scratchpad applies it to the live artifact).
"""

from __future__ import annotations

from collections import deque

from . import room_reflow
from .sim import DOWN, LEFT, RIGHT, UP

_ARROW_ROT180 = {">": "<", "<": ">", "^": "v", "v": "^", "V": "^"}
_ARROW_OF = {UP: "^", DOWN: "v", LEFT: "<", RIGHT: ">"}
_DIRS = (UP, DOWN, LEFT, RIGHT)


def _neg(d):
    return (-d[0], -d[1])


def rotate180(lines: list[str]) -> list[str]:
    """Rotate a block of text 180 degrees (reverse rows AND columns).

    Chirality-preserving, unlike a single-axis mirror: `X`/`d`/`a`/`x`
    (register-conditioned CW/CCW turns) need no substitution, only the 4
    arrow glyphs (`>`,`<`,`^`,`v`) get swapped pairwise. `U` (turn away
    from an incoming pipe) is untouched too -- its geometry comes from
    which wall a pipe attaches to, not from direction, so it is unaffected
    either way; this module does not use it.
    """
    height = len(lines)
    width = max((len(line) for line in lines), default=0)
    padded = [line.ljust(width) for line in lines]
    out = [[" "] * width for _ in range(height)]
    for r in range(height):
        row = padded[r]
        for c in range(width):
            ch = row[c]
            out[height - 1 - r][width - 1 - c] = _ARROW_ROT180.get(ch, ch)
    return ["".join(row) for row in out]


def _route(width, height, p1, dir1, p2, dir2, is_free):
    """BFS over (cell, heading): p1 arrives already heading dir1, must
    arrive at p2 heading dir2 (so the next single-cell step lands exactly
    on the real destination cell with the right incoming direction).
    Reversal is disallowed (never useful in open space, keeps paths sane).
    """
    if not is_free(p1) or not is_free(p2):
        return None
    start = (p1, dir1)
    prev = {start: None}
    dq = deque([start])
    goal = None
    while dq:
        cur = dq.popleft()
        cell, heading = cur
        if cell == p2 and heading == dir2:
            goal = cur
            break
        r, c = cell
        for step in _DIRS:
            if step == _neg(heading):
                continue
            nb = (r + step[0], c + step[1])
            if not (0 <= nb[0] < height and 0 <= nb[1] < width):
                continue
            if not is_free(nb):
                continue
            nxt = (nb, step)
            if nxt in prev:
                continue
            prev[nxt] = cur
            dq.append(nxt)
    if goal is None:
        return None
    path = []
    cur = goal
    while cur is not None:
        path.append(cur[0])
        cur = prev[cur]
    path.reverse()
    return path


def _stamp(grid, path, dir1, dir2):
    """Write turn arrows onto `grid` for a routed detour. Straight runs
    stay blank -- blank is already a valid in-room passthrough (unlike a
    pipe, which needs body glyphs), so only actual turns need a glyph.
    """
    for i, (r, c) in enumerate(path):
        incoming = dir1 if i == 0 else (
            path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1])
        outgoing = dir2 if i == len(path) - 1 else (
            path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1])
        if incoming != outgoing:
            grid[r][c] = _ARROW_OF[outgoing]


def fold_interior(interior_lines: list[str], cuts: list[int], margin: int = 6):
    """Split `interior_lines` at row indices `cuts` into len(cuts)+1 bands,
    alternate 180-rotation (last band always unrotated), place bands side
    by side (physical left-to-right order = REVERSE of flow order, so the
    unrotated last band -- which owns the room's original bottom-wall
    ports -- lands leftmost, in the room's ORIGINAL column range), and
    reroute every walk-graph edge that crossed a cut line through the
    newly-freed blank space with a short detour.

    `margin` rows of blank space are added above AND below every band's own
    placement (not just top-aligned at row 0): a rotated band's crossing
    point is wherever its ORIGINAL far edge ends up, which after a 180
    rotation is the OPPOSITE physical edge, so some junctions need free
    rows ABOVE a band's placement rather than below. Discovered by an
    actual failed route (P1/P2 landing at row -1) rather than derived
    up front -- see fold_log.md.

    Returns `(new_lines, info)`. `info['failures']` is non-empty if any
    crossing could not be routed (caller must treat that as a hard
    failure, not silently ship a broken fold).
    """
    height = len(interior_lines)
    width = max((len(line) for line in interior_lines), default=0)
    padded = [line.ljust(width) for line in interior_lines]

    bounds = [0, *cuts, height]
    bands_orig = [padded[bounds[i]:bounds[i + 1]] for i in range(len(bounds) - 1)]
    n = len(bands_orig)
    last = n - 1
    rotate_flags = [((last - i) % 2 == 1) for i in range(n)]

    bands_t = [rotate180(b) if rotate_flags[i] else [line[:] for line in b]
               for i, b in enumerate(bands_orig)]
    band_heights = [len(b) for b in bands_t]
    band_widths = [max((len(l) for l in b), default=0) for b in bands_t]

    phys_order = list(reversed(range(n)))
    col_offset = {}
    x = 0
    for bi in phys_order:
        col_offset[bi] = x
        x += band_widths[bi]
    new_width = x
    new_height = margin + max(band_heights) + margin

    grid = [[" "] * new_width for _ in range(new_height)]
    for bi, lines in enumerate(bands_t):
        co = col_offset[bi]
        for r, line in enumerate(lines):
            for c, ch in enumerate(line):
                if ch != " ":
                    grid[margin + r][co + c] = ch

    def transform(band_index, local_row, local_col):
        if rotate_flags[band_index]:
            h, w = band_heights[band_index], band_widths[band_index]
            local_row, local_col = h - 1 - local_row, w - 1 - local_col
        return margin + local_row, col_offset[band_index] + local_col

    used = set()

    def is_free(cell):
        r, c = cell
        return grid[r][c] == " " and cell not in used

    profile = room_reflow.strand_profile(padded)
    profile_by_y = {y: cols for y, _count, cols in profile}

    # Compute every crossing's endpoints up front, THEN route narrowest
    # spans first. A greedy "process in column order" run on the real
    # artifact deadlocked: the one wide-spanning crossing went first (its
    # shortest path is a single straight jog spanning its whole column
    # range), and that jog paved directly over the one cell several
    # narrower, nested crossings needed as their unique required approach
    # to their own destination -- making them unroutable no matter how the
    # rest of a detour bent, since the LAST step into a fixed endpoint has
    # no alternative neighbour. Narrow (nested) spans claim their tight
    # lanes first; the wide one goes last, when it still has room to bend
    # around the small segments already claimed.
    pending = []
    for cut_i, cut_row in enumerate(cuts):
        upper_i, lower_i = cut_i, cut_i + 1
        cols = profile_by_y[cut_row]
        for col, label in cols:
            if label == "v":
                s_band, s_row = upper_i, band_heights[upper_i] - 1
                d_band, d_row = lower_i, 0
                dirv = DOWN
            else:
                s_band, s_row = lower_i, 0
                d_band, d_row = upper_i, band_heights[upper_i] - 1
                dirv = UP
            s_r, s_c = transform(s_band, s_row, col)
            d_r, d_c = transform(d_band, d_row, col)
            exit_dir = _neg(dirv) if rotate_flags[s_band] else dirv
            entry_dir = _neg(dirv) if rotate_flags[d_band] else dirv
            p1 = (s_r + exit_dir[0], s_c + exit_dir[1])
            p2 = (d_r - entry_dir[0], d_c - entry_dir[1])
            span = abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])
            pending.append((span, cut_row, col, label, p1, exit_dir, p2,
                            entry_dir))
    pending.sort(key=lambda t: t[0])

    detours = []
    failures = []
    for _span, cut_row, col, label, p1, exit_dir, p2, entry_dir in pending:
        path = _route(new_width, new_height, p1, exit_dir, p2, entry_dir,
                      is_free)
        if path is None:
            failures.append(
                (cut_row, col, label, p1, exit_dir, p2, entry_dir))
            continue
        _stamp(grid, path, exit_dir, entry_dir)
        for cell in path:
            used.add(cell)
        detours.append((cut_row, col, label, len(path)))

    new_lines = ["".join(row).rstrip() for row in grid]
    info = dict(bands=n, rotate_flags=rotate_flags, band_heights=band_heights,
               band_widths=band_widths, col_offset=col_offset,
               new_width=new_width, new_height=new_height,
               detours=detours, failures=failures)
    return new_lines, info
