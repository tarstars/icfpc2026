"""Contract tests for the compact in-room assembler."""

from __future__ import annotations

import hashlib
from itertools import pairwise

import pytest

from littleman.canvas import Canvas
from littleman.lane import Lane, LaneError, unreachable
from littleman.memory_packed import build_head, build_p2
from littleman.sim import Machine

HEAD_OPS = [
    "@",
    "M",
    "r",
    "s",
    "r",
    "-",
    "M",
    "`34`",
    "W",
    "%",
    "s",
    "r",
    "M",
    "1",
    "+",
    "M",
    "`34`",
    "W",
    "%",
    "M",
    "r",
    "s",
    "r",
    "s",
    "r",
    "s",
    "W",
]
P2_PREFIX = ["@", "r", "s", "b", "r", "s"]
P2_READ = ["r", "M", " ", "`43`", "-", "s", "r", "r"]
P2_WRITE = [
    "r",
    "M",
    "`2097151`",
    "{",
    "M",
    "1",
    "N",
    "~",
    "s",
    " ",
    "`2097151`",
    "M",
    "r",
    "&",
    "M",
    "r",
    "W",
    "{",
    "s",
]


def head_lane() -> Lane:
    return Lane().loop_forever(Lane().seq(HEAD_OPS))


def p2_lane() -> Lane:
    body = Lane().seq(P2_PREFIX)
    body.branch_bp(taken=P2_WRITE, straight=P2_READ)
    return Lane().loop_forever(body)


def parse(room) -> Machine:
    return Machine.parse("\n".join(room.grid) + "\n")


def digest(grid: list[str]) -> str:
    return hashlib.sha256("\n".join(grid).encode()).hexdigest()


def rig(room) -> str:
    canvas = Canvas()
    canvas.put(0, 6, room.grid)
    io_top = 2
    canvas.put(io_top, 0, ["+-+", "|I|", "+-+"])
    canvas.pipe([(io_top + 1, 3), (io_top + 1, 5)])
    room_right = 6 + len(room.grid[0]) - 1
    output_left = room_right + 4
    canvas.put(io_top, output_left, ["+-+", "|O|", "+-+"])
    canvas.pipe([(io_top + 1, room_right + 1), (io_top + 1, output_left - 1)])
    return canvas.render()


def test_head_is_byte_exact():
    compiled = head_lane().compile(max_width=27, compact=False)
    expected = build_head().render()
    assert compiled.grid == expected
    assert digest(compiled.grid) == digest(expected)
    assert (compiled.metrics.rows, compiled.metrics.cols) == (4, 29)


def test_p2_is_byte_exact():
    compiled = p2_lane().compile(max_width=24, compact=False)
    expected = build_p2().render()
    assert compiled.grid == expected
    assert digest(compiled.grid) == digest(expected)
    assert (compiled.metrics.rows, compiled.metrics.cols) == (7, 26)


@pytest.mark.parametrize(
    ("factory", "width"),
    [(head_lane, 27), (p2_lane, 24)],
)
def test_reference_rooms_parse_and_are_deterministic(factory, width):
    first = factory().compile(max_width=width, compact=False)
    second = factory().compile(max_width=width, compact=False)
    assert first == second
    machine = parse(first)
    assert len(machine.rooms) == 1
    assert len(machine.men) == 1


@pytest.mark.parametrize(("factory", "width"), [(head_lane, 27), (p2_lane, 24)])
def test_reference_rooms_have_two_nontrivial_pipes_in_a_rig(factory, width):
    room = factory().compile(max_width=width, compact=False)
    machine = Machine.parse(rig(room))
    assert len(machine.pipes) == 2
    assert all(len(pipe.cells) >= 2 for pipe in machine.pipes)


def test_cells_map_points_at_execute_or_closing_literal_cell():
    room = head_lane().compile(max_width=27, compact=False)
    assert len(room.cells) == len(HEAD_OPS)
    for token, (row, col) in zip(HEAD_OPS, room.cells):
        assert room.grid[row][col] == token[-1]
    first_34 = HEAD_OPS.index("`34`")
    assert room.cells[first_34] == (1, 12)
    assert room.cells[-1] == (2, 19)


def test_compaction_reports_before_and_after_and_improves_head():
    room = head_lane().compile(max_width=27)
    before, after = room.metrics.before, room.metrics.after
    assert max(after.rows, after.cols) < max(before.rows, before.cols)
    assert after.cells_used == before.cells_used
    assert after.fill_ratio > before.fill_ratio
    assert any("bisection" in item for item in room.metrics.invariants)
    parse(room)


def test_x_pattern_merges_and_wall_unroutes_negative_arm():
    body = Lane().seq(["@", "M"])
    body.branch_sign(neg=unreachable, zero=["1"], pos=["2", "M"])
    room = Lane().loop_forever(body).compile(max_width=13, compact=False)
    parse(room)
    assert len(room.cells) == 2 + 1 + 0 + 1 + 2
    assert any("X arms merge" in item for item in room.metrics.invariants)
    branch_row, branch_col = room.cells[2]
    assert room.grid[branch_row - 1][branch_col] == " "


def test_backtick_alignment_is_repaired_and_rechecked():
    body = Lane().seq(["@", "`12`", "M", "s", "`34`", "r", "M", "`56`", "s", "`78`"])
    room = Lane().loop_forever(body).compile(max_width=14, compact=False)
    machine = parse(room)
    for col in range(1, room.metrics.cols - 1):
        rows = [
            row for row in range(1, room.metrics.rows - 1) if room.grid[row][col] == "`"
        ]
        for upper, lower in pairwise(rows):
            between = [room.grid[row][col] for row in range(upper + 1, lower)]
            assert not all(ch.isdigit() or ch == " " for ch in between)
    assert machine.hpairs


@pytest.mark.parametrize("bad", ["", "`3", "`1x`", "ab"])
def test_invalid_tokens_are_rejected(bad):
    with pytest.raises(LaneError):
        Lane().seq([bad])


def test_unreachable_straight_bp_arm_is_not_routed():
    body = Lane().seq(["@", "1", "b"])
    body.branch_bp(taken=["M", "s"], straight=unreachable)
    room = Lane().loop_forever(body).compile(max_width=14, compact=False)
    parse(room)
    branch_row, branch_col = room.cells[3]
    assert room.grid[branch_row][branch_col + 1] == " "


def test_prologue_is_geometrically_outside_forever_lap():
    lane = Lane().seq(["@", "3", "b"]).loop_forever(["M", "1", "+"])
    room = lane.compile(max_width=12, compact=False)
    parse(room)
    assert any("prologue path cannot" in item for item in room.metrics.invariants)
    prologue_rows = {room.cells[index][0] for index in range(3)}
    lap_rows = {room.cells[index][0] for index in range(3, 6)}
    assert prologue_rows == {1}
    assert lap_rows == {3}


def test_counted_loop_uses_cookbook_d_then_m_return():
    lane = Lane().seq(["@"]).loop_counted(["r", "s"], ["3", "b"]).seq(["H"])
    room = lane.compile(max_width=12, compact=False)
    parse(room)
    assert room.grid[4][12] == "d"
    assert room.grid[4][2] == "m"
    assert any("tested at d before m" in item for item in room.metrics.invariants)


def test_backward_label_goto_lowers_to_a_racetrack():
    lane = Lane().label("lap").seq(["@", "M", "1", "+"]).goto("lap")
    room = lane.compile(max_width=10, compact=False)
    parse(room)
    assert room.metrics.ticks_per_lap is not None
    assert len(room.cells) == 4


def test_ports_are_preserved_as_metadata_only():
    ports = {"input": (1, 0), "output": (1, 12)}
    room = Lane(["@", "H"]).compile(max_width=12, ports=ports, compact=False)
    assert room.ports == ports


def test_literal_wider_than_corridor_is_rejected():
    with pytest.raises(LaneError, match="literal width"):
        Lane().loop_forever(["@", "`123456789`"]).compile(max_width=8, compact=False)


def test_branch_literals_are_shifted_out_of_vertical_alignment():
    body = Lane().seq(["@"])
    body.branch_sign(neg=["`12`"], zero=["`34`"], pos=["`56`"])
    room = Lane().loop_forever(body).compile(max_width=16, compact=False)
    machine = parse(room)
    closing_columns = [room.cells[index][1] for index in (2, 3, 4)]
    assert len(set(closing_columns)) == 3
    assert not machine.vpairs


def test_a_branch_uses_mirrored_corner_pattern():
    body = Lane().seq(["@", "1", "b"])
    body.branch_bp(taken=["M", "s"], straight=["r"], opcode="a")
    room = Lane().loop_forever(body).compile(max_width=14, compact=False)
    parse(room)
    row, col = room.cells[3]
    assert room.grid[row][col] == "a"
    assert any("vertically mirrored" in item for item in room.metrics.invariants)
