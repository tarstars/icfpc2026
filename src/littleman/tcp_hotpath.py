"""Tick-only successor to the compact Packet Reassembly machine.

The packed controller's insertion return originally walks around the west
edge of room C.  Two turns create a shorter internal chord.  They are placed
on cells that the main entry path already crosses while heading east, so the
entry protocol is unchanged; each stored packet saves four executed cells.
"""

from __future__ import annotations

from .tcp_fast import build_compact

# Coordinates in the rendered tcp_08 grid, including room walls.
_SHORTCUTS = {
    (22, 3): ">",  # C interior (4, 2): rejoin the eastbound main path
    (28, 3): "^",  # C interior (10, 2): leave the westbound return path
}


def build_tcp_hotpath() -> str:
    """Return tcp_08 with the two-cell insertion-return shortcut."""
    rows = [list(row) for row in build_compact().rstrip("\n").split("\n")]
    for (row, col), glyph in _SHORTCUTS.items():
        assert rows[row][col] == " "
        rows[row][col] = glyph
    return "\n".join("".join(row) for row in rows) + "\n"
