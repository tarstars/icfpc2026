"""LM-75 display: parsing, DATA/ADDR/SWAP pipes, frame commits."""

from littleman.sim import Machine

# 4x1 interior display; DATA fed from the top room, SWAP(1) from the
# bottom room after a delay corridor.
DRAW = """\
+-+  +---------+   +====+
|I|>>|@rsrsrsv |>->:    :
+-+  |H      < |   +====+
     +---------+      ^
+------------+        ^
|@          v|        ^
|H    s1    <|>-------^
+------------+
"""


def _draw_text(swap_value):
    return DRAW.replace("s1", f"s{swap_value}")


def test_parse_display_and_pipe_sides():
    m = Machine.parse(DRAW)
    disp = [r for r in m.rooms if r.kind == "display"]
    assert len(disp) == 1
    d = disp[0]
    assert d.disp_w == 4 and d.disp_h == 1
    sides = sorted(p.side for p in m.pipes if p.dest.kind == "display")
    assert sides == ["data", "swap"]


def test_data_draws_and_swap1_commits_frame_preserving_next():
    m = Machine.parse(_draw_text(1))
    res = m.run(inputs=[7, 3, 9], max_ticks=500)
    assert res.status == "halted"
    assert res.frames == [[[7, 3, 9, 0]]]
    d = [r for r in m.rooms if r.kind == "display"][0]
    assert d.next[0] == [7, 3, 9, 0]  # swap 1 preserves next


def test_swap0_clears_next_buffer():
    m = Machine.parse(_draw_text(0))
    res = m.run(inputs=[7, 3, 9], max_ticks=500)
    assert res.frames == [[[7, 3, 9, 0]]]
    d = [r for r in m.rooms if r.kind == "display"][0]
    assert d.next[0] == [0, 0, 0, 0]


def test_bad_color_is_error():
    m = Machine.parse(_draw_text(1))
    res = m.run(inputs=[16, 0, 0], max_ticks=500)
    assert res.status == "error"
    assert res.error == "display"
