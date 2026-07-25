"""Gates for the pressed Sudoku Auditor (`sudoku_03.man`).

The press only moves rooms and re-routes the five non-ring pipes, so the
tests below are all *differential* against the live `sudoku_02.man`: same
rooms byte-for-byte, same ring capacities, same pipe-instruction bindings.
"""

from __future__ import annotations

import json
from pathlib import Path

from littleman.ir_export import machine_ir
from littleman.judge import judge_case
from littleman.sim import Machine
from littleman import sudoku_press as sp

REPO = Path(__file__).resolve().parents[1]
LIVE = REPO / "submissions" / "sudoku-validity" / "sudoku_02.man"
PRESSED = REPO / "submissions" / "sudoku-validity" / "sudoku_03.man"
PROBLEM = REPO / "data" / "small" / "problems" / "sudoku-validity.json"


def _named(text: str) -> dict:
    machine = Machine.parse(text)
    named = {}
    for room in machine.rooms:
        if room.kind in ("input", "output"):
            named[room.kind] = room
            continue
        shape = sp._room_shape(room)
        if shape == (5, 5):
            continue
        named[next(n for n, w in sp.SHAPES.items() if w == shape)] = room
    return machine, named


def test_generator_is_deterministic_and_matches_the_artifact():
    first = sp.build_pressed_sudoku()
    assert first == sp.build_pressed_sudoku()
    assert first == PRESSED.read_text()


def test_bounding_box_beats_the_live_artifact():
    lines = PRESSED.read_text().rstrip("\n").split("\n")
    height, width = len(lines), max(len(line) for line in lines)
    assert (height, width) == (194, 198)
    assert max(height, width) < 248
    assert max(height, width) ** 2 == 39204


def test_every_room_is_byte_identical_to_sudoku_02():
    live, live_named = _named(LIVE.read_text())
    built, built_named = _named(PRESSED.read_text())
    assert sorted(live_named) == sorted(built_named)

    def rect(machine, room):
        return [
            "".join(machine.grid[r][room.left:room.right + 1])
            for r in range(room.top, room.bottom + 1)
        ]

    for name in live_named:
        assert rect(live, live_named[name]) == rect(built, built_named[name]), name

    # ...and so are all twelve 5x5 ring relays.
    def relays(machine):
        return sorted(
            tuple(rect(machine, room))
            for room in machine.rooms
            if sp._room_shape(room) == (5, 5)
        )

    assert relays(live) == relays(built)


def test_ring_capacity_is_unchanged():
    live, live_named = _named(LIVE.read_text())
    built, built_named = _named(PRESSED.read_text())
    for name in ("row", "column", "box"):
        got = sp.ring_lengths(built, built_named[name])
        assert got == sp.ring_lengths(live, live_named[name]), name
        # Each worker's nine-mask FIFO needs its full ring; the pressed
        # machine copies the ring pipes cell-for-cell, so capacity is exact.
        assert sum(got) >= 100, (name, got)


def _solved_grid() -> list[list[int]]:
    return [[(3 * (r % 3) + r // 3 + c) % 9 + 1 for c in range(9)]
            for r in range(9)]


def _rounds(order, mutate=None) -> list[dict]:
    """81 rounds of `r c v` in `order`, all verdicts 1 unless `mutate` fires."""
    grid = _solved_grid()
    rounds = []
    for r, c in order:
        value = grid[r][c]
        verdict = 1
        if mutate is not None and (r, c) == order[-1]:
            value, verdict = mutate(grid, r, c)
        rounds.append({"in": [str(r), str(c), str(value)], "out": [str(verdict)]})
    return rounds


def test_public_cases_all_pass():
    problem = json.loads(PROBLEM.read_text())
    text = PRESSED.read_text()
    for case in problem["publicTestData"]:
        result = judge_case(text, case["rounds"], max_ticks=5_000_000)
        assert result.passed, (case["name"], result.reason)


def test_directed_worst_case_ring_and_pipe_stress():
    """Orders that maximally desynchronise the three workers.

    The command pipes are the only ones the press shortened (109/119/245
    cells -> 105/106/196), so the risk they carry is back-pressure: the
    broadcaster's `S` blocks until ALL THREE have room.  These two orders
    pin one worker's rotation count at 0 while another's runs 8, 7, 6...,
    which is the widest per-cell speed gap the problem admits.  The public
    cases use scattered orders and never hold that gap for a whole row.
    """
    text = PRESSED.read_text()
    by_row = [(r, c) for r in range(9) for c in range(8, -1, -1)]
    by_col = [(r, c) for c in range(9) for r in range(8, -1, -1)]
    for order in (by_row, by_col):
        result = judge_case(text, _rounds(order), max_ticks=5_000_000)
        assert result.passed, result.reason


def test_directed_violation_on_the_slowest_cell():
    text = PRESSED.read_text()
    order = [(r, c) for r in range(9) for c in range(8, -1, -1)]
    result = judge_case(
        text,
        _rounds(order, mutate=lambda grid, r, c: (grid[r][1], 0)),
        max_ticks=5_000_000,
    )
    assert result.passed, result.reason


def _binding_roles(text: str) -> dict:
    """Map (room name, cell offset) -> `op|pipe role`, geometry-free.

    A pipe's ROLE is `<source room>-><dest room>`, with the twelve relays
    named by their owner and their column order, so the map is comparable
    across two different layouts of the same machine.
    """
    machine, named = _named(text)
    role = {id(room): name for name, room in named.items()}
    owners: dict[str, list] = {}
    for pipe in machine.pipes:
        shapes = (sp._room_shape(pipe.source), sp._room_shape(pipe.dest))
        if (5, 5) not in shapes:
            continue
        relay = pipe.source if shapes[0] == (5, 5) else pipe.dest
        worker = pipe.dest if shapes[0] == (5, 5) else pipe.source
        owners.setdefault(role[id(worker)], []).append(
            (relay.left - worker.left, id(relay))
        )
    for worker, found in owners.items():
        for index, (_, rid) in enumerate(sorted(set(found))):
            role[rid] = f"{worker}.relay{index}"
    labels = {
        i: f"{role[id(p.source)]}->{role[id(p.dest)]}"
        for i, p in enumerate(machine.pipes)
    }
    out = {}
    for key, entry in machine_ir(text)["resolution"].items():
        r, c = (int(v) for v in key.split(","))
        room = next(rm for rm in machine.rooms if rm.contains(r, c))
        pipes = [entry["pipe"]] if "pipe" in entry else entry["pipes"]
        out[(role[id(room)], r - room.top, c - room.left)] = (
            entry["op"],
            tuple(sorted(labels[i] for i in pipes)),
        )
    return out


def test_no_pipe_instruction_changes_its_role():
    live = _binding_roles(LIVE.read_text())
    built = _binding_roles(PRESSED.read_text())
    assert len(live) == 115
    assert live == built


def test_worker_ports_keep_their_offsets():
    _, built_named = _named(PRESSED.read_text())
    want = sp._expected_ports()
    for key, cell in want.items():
        name, port = key.split(".")
        room = built_named[name]
        offset = (cell[0] - room.bottom, cell[1] - room.left)
        assert offset == sp.WORKER_PORTS[name][port], key
