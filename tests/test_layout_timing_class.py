"""Per-pipe timing classification for `Conn.exact`.

Regression cover for a specific bug: `layout_ir.parse` used to compute one
layout-wide `timing` boolean (true if ANY room anywhere contained a q/R/U
op) and copy it onto every `Conn.exact`. Downstream, `layout_solve` pins
the Manhattan distance of every "exact" pipe, so on a real machine with
145 rooms / 231 pipes -- where only 2 rooms actually contained a timing
op -- all 231 pipes were pinned and the placer could not move anything.

The fix: a pipe is exact only if ITS OWN endpoint room (source or
destination) contains a timing op. `Layout.timing_sensitive` is untouched
(other code reads it) and still means "any room anywhere".
"""

from __future__ import annotations

from pathlib import Path

from littleman import layout_ir

ROOT = Path(__file__).resolve().parents[1]


def _chain(ops: list[str]) -> str:
    """A horizontal chain of `len(ops)` 3x5 rooms, room i linked to room
    i + 1 by a single-cell '>' pipe. `ops[i]` is the character placed in
    the middle of room i's interior: a timing op ('q', 'R', or 'U') or a
    plain ' ' for a room with none.

    Known gotcha: `layout_ir.parse` drops any line that is exactly "",
    which desyncs every later room-row lookup (and surfaces as an
    IndexError) if one slips in from a ragged join. So every line is
    ljust-padded to a common width before it is ever handed to parse.
    """
    top = " ".join("+---+" for _ in ops)
    mid = ">".join(f"| {ch} |" for ch in ops)
    bot = " ".join("+---+" for _ in ops)
    width = max(len(top), len(mid), len(bot))
    return "\n".join(line.ljust(width) for line in (top, mid, bot)) + "\n"


def _layout(ops: list[str]):
    text = _chain(ops)
    layout = layout_ir.parse(text)
    assert layout_ir.render(layout) == text, "round trip must stay byte-exact"
    return layout


def test_no_timing_ops_anywhere_yields_zero_exact_pipes():
    layout = _layout([" ", " ", " "])
    assert [c.exact for c in layout.conns] == [False, False]
    assert layout.timing_sensitive is False


def test_every_room_with_a_timing_op_yields_all_pipes_exact():
    layout = _layout(["q", "R", "U"])
    assert [c.exact for c in layout.conns] == [True, True]
    assert layout.timing_sensitive is True


def test_exact_is_per_pipe_not_per_layout():
    """The regression case: only the LAST room has a timing op, so only
    the pipe touching it should be exact -- the OTHER pipe, strung between
    two non-timing rooms, must stay free for the solver to reposition.

    Before the fix this returned [True, True]: one q/R/U anywhere set a
    layout-wide flag that every Conn.exact blindly copied.
    """
    layout = _layout([" ", " ", "q"])
    assert [c.exact for c in layout.conns] == [False, True]
    # Layout-wide flag is unaffected by the per-pipe fix -- it stays True.
    assert layout.timing_sensitive is True


def test_timing_op_on_the_source_side_also_marks_its_own_pipe_exact():
    layout = _layout(["R", " ", " "])
    assert [c.exact for c in layout.conns] == [True, False]


def test_round_trip_is_byte_exact_on_a_real_artifact():
    path = ROOT / "submissions" / "tcp" / "tarstars_tcp_11.man"
    text = path.read_text()
    assert layout_ir.render(layout_ir.parse(text)) == text
