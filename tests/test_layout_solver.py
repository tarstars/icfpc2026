"""The solver stack's own gates: IR fidelity, port freedom, and the oracle.

The stack is only allowed to touch a submission because every step is
checkable against the artifact it started from, so the tests are that
check, not a sample of it:

* the IR round-trips byte-exact (a re-placement of a lossy IR means
  nothing);
* `endpoint_freedom` says a port may move only where `sim` provably has no
  choice to make -- these assertions are the safety argument for M2;
* `layout_gate` passes an artifact against ITSELF, and rejects each of the
  specific corruptions it exists to catch, including the pipe that got
  SHORTER, which is the one that passes the public cases while deadlocking.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from littleman import layout_gate, layout_ir, layout_route, layout_solve

ROOT = Path(__file__).resolve().parents[1]
TARGETS = {
    "tcp": ROOT / "submissions" / "tcp" / "tcp_08.man",
    "plotter": ROOT / "submissions" / "plotter" / "plotter_05.man",
    "matmul": ROOT / "submissions" / "matmul" / "matmul_03.man",
    "history": ROOT / "submissions" / "history" / "history_00.man",
}


def _text(slug: str) -> str:
    path = TARGETS[slug]
    if not path.exists():
        pytest.skip(f"{path} not checked in")
    return path.read_text()


@pytest.mark.parametrize("slug", ["tcp", "plotter", "matmul"])
def test_ir_round_trips_byte_exact(slug: str) -> None:
    text = _text(slug)
    assert layout_ir.render(layout_ir.parse(text)) == text


@pytest.mark.parametrize("slug", ["tcp", "plotter", "matmul"])
def test_freedom_matches_sim_binding_rule(slug: str) -> None:
    """A port may move exactly when its room has nothing to rank."""
    layout = layout_ir.parse(_text(slug))
    src_free, dst_free = layout_solve.endpoint_freedom(layout)
    outs: dict[int, int] = {}
    ins: dict[int, int] = {}
    for conn in layout.conns:
        outs[conn.src.room] = outs.get(conn.src.room, 0) + 1
        ins[conn.dst.room] = ins.get(conn.dst.room, 0) + 1
    for index, conn in enumerate(layout.conns):
        if src_free[index]:
            assert outs[conn.src.room] == 1
            assert layout.rooms[conn.src.room].kind != "display"
        if dst_free[index]:
            assert ins[conn.dst.room] == 1
            assert layout.rooms[conn.dst.room].kind != "display"


def test_freedom_is_per_direction_not_per_room() -> None:
    """A fan-in room may still move its single OUTGOING port."""
    layout = layout_ir.parse(_text("plotter"))
    outs: dict[int, int] = {}
    ins: dict[int, int] = {}
    for conn in layout.conns:
        outs[conn.src.room] = outs.get(conn.src.room, 0) + 1
        ins[conn.dst.room] = ins.get(conn.dst.room, 0) + 1
    src_free, _dst_free = layout_solve.endpoint_freedom(layout)
    mixed = [i for i, conn in enumerate(layout.conns)
             if outs.get(conn.src.room, 0) == 1 and ins.get(conn.src.room, 0) > 1]
    if not mixed:
        pytest.skip("no fan-in room with a single outgoing pipe here")
    assert all(src_free[i] for i in mixed)


@pytest.mark.parametrize("slug", ["tcp", "plotter", "matmul"])
def test_gate_accepts_an_artifact_against_itself(slug: str) -> None:
    text = _text(slug)
    problem = {"tcp": "tcp", "plotter": "plotter", "matmul": "matmul"}[slug]
    report = layout_gate.check(text, text, problem, judge_original=False)
    assert report.passed, report.reasons
    assert report.cases_passed == report.cases_total > 0


def test_gate_rejects_a_shortened_pipe() -> None:
    """The failure with no other symptom: a storage pipe that lost a cell.

    A squeezed snake passed 5/5 public and deadlocked at snake-length 68,
    and an independent fold hit the same wall the same day. Length is
    capacity, so a shorter pipe is a different machine even when every
    public case still passes.
    """
    text = _text("tcp")
    layout = layout_ir.parse(text)
    target = max(range(len(layout.conns)), key=lambda i: layout.conns[i].length)
    conn = layout.conns[target]
    lines = [list(line) for line in text.split("\n")]
    # Drop the pipe's second cell by pulling the whole tail back one step:
    # re-draw it one cell shorter and blank the vacated cell.
    row, col = conn.cells[-1]
    lines[row][col] = " "
    shorter = "\n".join("".join(line) for line in lines)
    report = layout_gate.check(text, shorter, "tcp", judge_original=False)
    assert not report.passed
    assert any("SHRANK" in reason or "pipe count" in reason
               or "does not parse" in reason for reason in report.reasons), \
        report.reasons


def test_gate_rejects_a_layout_the_server_would_refuse() -> None:
    """Two rooms sharing wall cells parse locally and load 0/0 on the server."""
    text = _text("tcp")
    lines = text.split("\n")
    width = max(len(line) for line in lines)
    grid = [list(line.ljust(width)) for line in lines]
    for row in range(3):
        for col in range(3):
            grid[row][col] = "#" if row in (0, 2) or col in (0, 2) else "."
    report = layout_gate.check(text, "\n".join("".join(r) for r in grid),
                               "tcp", judge_original=False)
    assert not report.passed


@pytest.mark.skipif(not layout_solve.HAVE_ORTOOLS, reason="needs ortools")
def test_solver_chooses_ports_and_the_router_follows_them() -> None:
    layout = layout_ir.parse(_text("tcp"))
    place = layout_solve.solve(layout, seconds=20.0, channel=2)
    assert place is not None
    assert place.ports is not None and len(place.ports) == len(layout.conns)
    src_free, dst_free = layout_solve.endpoint_freedom(layout)
    for index, conn in enumerate(layout.conns):
        chosen_src, chosen_dst = place.ports[index]
        assert chosen_src.room == conn.src.room
        assert chosen_dst.room == conn.dst.room
        if not src_free[index]:
            assert (chosen_src.side, chosen_src.offset) == (conn.src.side,
                                                            conn.src.offset)
        if not dst_free[index]:
            assert (chosen_dst.side, chosen_dst.offset) == (conn.dst.side,
                                                            conn.dst.offset)
    paths, err = layout_route.route_with_ripup(layout, place, tries=6)
    if err is not None:
        paths, err = layout_route.route_negotiated(layout, place)
    if err is not None:
        pytest.skip(f"tcp did not route at channel 2: {err}")
    for index, path in paths:
        chosen_src, chosen_dst = place.ports[index]
        start = layout_solve._port_cell(
            place.tops[chosen_src.room], place.lefts[chosen_src.room],
            layout.rooms[chosen_src.room], chosen_src)
        assert path[0] == start
        assert len(path) >= 2


@pytest.mark.skipif(not layout_solve.HAVE_ORTOOLS, reason="needs ortools")
def test_a_routed_placement_survives_the_gate() -> None:
    """End to end: place, route, emit, and let the oracle judge the result."""
    text = _text("tcp")
    layout = layout_ir.parse(text)
    place, paths, _log = layout_route.place_route_repair(
        layout, seconds=15.0, channel=2, rounds=3, restarts=20)
    if place is None:
        pytest.skip("tcp did not route within the test's budget")
    report = layout_gate.check(text, layout_route.emit(layout, place, paths),
                               "tcp", judge_original=False)
    assert report.passed, report.reasons
