"""LLM multi-man: the wall rule, the man tokens, and the whole architecture.

Model first.  ``littleman.llm.LLM`` is the oracle for everything here; the v2
SCAN reference is graded against it, the v2 SCAN ROOM is graded against the
reference, and the three-interpreter architecture is graded end to end
through the real ``StepModel`` -- so a failure localises to one stage.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman.llm import LLM, program_grid
from littleman.lllm_classify import classify_reference
from littleman.lllm_scan import MEN, build_scan_rig_v2, scan_reference_v2
from littleman.lllm_step import (
    ScriptedFetch,
    StepModel,
    build_gate,
    build_tee,
    frames_from_deltas,
)
from littleman.sim import Machine

DATA = Path("data/small/problems")
WALL_BIT, PADDING_BIT = 256, 512


def _cases(slug: str):
    return json.loads((DATA / f"{slug}.json").read_text())["publicTestData"]


def _rows(case):
    return program_grid([int(v) for v in case["rounds"][0]["in"]])


def _pipe_free(case):
    rows = _rows(case)
    return not sum(row.count("s") + row.count("r") for row in rows)


def _stream(rows, tail=()):
    return [len(rows[0]), len(rows), *[ord(c) for r in rows for c in r], *tail]


PIPE_FREE = [
    c for c in _cases("little-little-man") if _pipe_free(c)
] + _cases("little-little-little-man")


@pytest.mark.parametrize("case", PIPE_FREE, ids=lambda c: c["name"])
def test_wall_bit_matches_the_reference_interpreter(case):
    """SCAN v2's wall bit equals ``LLM.on_border`` on every pipe-free program.

    Address 0 is the one licensed exception: it is forced to be a wall so a
    surplus interpreter parked there can never walk.
    """
    rows = _rows(case)
    tokens = scan_reference_v2(_stream(rows))
    machine = LLM.parse(rows)
    for addr in range(1, 256):
        y, x = divmod(addr, 16)
        if tokens[addr] & PADDING_BIT:
            continue
        want = any(room.on_border(y, x) for room in machine.rooms)
        assert bool(tokens[addr] & WALL_BIT) is want, (addr, y, x)


@pytest.mark.parametrize("case", PIPE_FREE, ids=lambda c: c["name"])
def test_man_tokens_are_every_start_cell(case):
    rows = _rows(case)
    tokens = scan_reference_v2(_stream(rows))
    men = [addr for addr in tokens[256 : 256 + MEN] if addr]
    want = {y * 16 + x for y, row in enumerate(rows) for x, ch in enumerate(row)
            if ch == "@"}
    assert set(men) == want
    assert len(tokens[256 : 256 + MEN]) == MEN


def test_reference_relays_later_tokens():
    rows = ["+--+", "|@ |", "|  |", "+--+"]
    tokens = scan_reference_v2(_stream(rows, [7, 9]))
    assert tokens[256 + MEN :] == [7, 9]


# ------------------------------------------------------------- the v2 room
class _Script:
    def __init__(self, tokens, expected):
        self.tokens, self.expected, self.got = list(tokens), list(expected), []

    def pop_input(self):
        return self.tokens.pop(0) if self.tokens else None

    def on_output(self, value, tick):
        self.got.append(value)
        return "passed" if len(self.got) >= len(self.expected) else None


@pytest.fixture(scope="module")
def scan_rig():
    return build_scan_rig_v2()


def test_v2_rooms_and_pipes(scan_rig):
    machine = Machine.parse(scan_rig)
    assert len(machine.rooms) == 4          # I, SCAN, relay, O
    assert len(machine.pipes) == 4


@pytest.mark.parametrize("case", PIPE_FREE, ids=lambda c: c["name"])
def test_v2_room_equals_its_reference(scan_rig, case):
    stream = _stream(_rows(case))
    expected = scan_reference_v2(stream)
    script = _Script(stream, expected)
    result = Machine.parse(scan_rig).run(max_ticks=4_000_000, controller=script)
    assert result.error is None, result.error
    assert result.status == "passed"
    assert script.got == expected


# --------------------------------------------------- the whole architecture
def _merge(streams):
    """The gate chain in Python: drop token 9, one sentinel per round."""
    out, index = [], [0] * len(streams)

    def take(i, n):
        chunk = streams[i][index[i] : index[i] + n]
        index[i] += n
        return chunk

    first = True
    while index[0] < len(streams[0]):
        for i in range(len(streams)):
            body = take(i, 257) if first else take(i, 2)
            if first and i:
                body = body[256:]
            take(i, 1)
            out += [t for t in body if t != 9]
        out.append(-1)
        first = False
    return out


@pytest.mark.parametrize("case", PIPE_FREE, ids=lambda c: c["name"])
def test_three_interpreters_reproduce_every_pipe_free_case(case):
    """SCAN v2 -> CLASSIFY -> three unmodified STEP models -> the merge.

    This is the architecture claim in one assertion: with no pipes the men
    never interact, so three copies of the LLLM interpreter plus a merge that
    drops the parked men's pixels reproduce LLM exactly.
    """
    if case["name"] == "pileup":
        pytest.xfail(
            "pileup is the one pipe-free case that needs the LLM rule that ONE "
            "man reaching a wall freezes ALL of them; independent interpreters "
            "cannot express it and it is deliberately out of scope here."
        )
    rows = _rows(case)
    ks = [int(rd["in"][0]) for rd in case["rounds"][1:]]
    packed = classify_reference(scan_reference_v2(_stream(rows, ks)))
    world, men = packed[:64], packed[64 : 64 + MEN]
    deltas = []
    for addr in men:
        model = StepModel(ScriptedFetch())
        model.setup(world + [addr])
        model.round_one()
        for k in ks:
            model.round(int(k))
        deltas.append(model.deltas)
    frames = frames_from_deltas(_merge(deltas))
    assert frames == [rd["frames"][0] for rd in case["rounds"]]


# ------------------------------------------------------------- the new rooms
def test_tee_has_one_incoming_and_two_outgoing_bindings():
    """The two man tokens must reach different consumers, so the near and far
    sends have to resolve to different pipes by position alone."""
    room = build_tee().render()
    text = "\n".join(room)
    assert text.count("S") == 2          # one broadcast per phase
    assert len(room) == 15 and len(room[0]) == 36


def test_gate_reads_are_split_left_and_right():
    """Every upstream ``r`` west of the midline, every own ``r`` east of it."""
    room = build_gate()
    for (row, col), ch in room.cells.items():
        if ch != "r":
            continue
        assert col <= 24 or col >= 33, (row, col)


def test_each_tee_reads_exactly_the_addresses_it_still_owns():
    """The llm_04 deadlock, as a unit test.

    A tee places one address on its near pipe and the rest on its far pipe,
    so the next tee down the chain sees one address fewer.  Both tees reading
    three made TEE2 take the first round count as if it were a man: its near
    interpreter then ran one round short forever, and GATE1 -- the gate fed by
    that interpreter -- blocked on its own stream one round from the end.
    """
    addressed = [
        sorted(cell for cell, ch in room.cells.items()
               if ch == "r" and cell[0] not in (1, 10))
        for room in (build_tee(3), build_tee(2))
    ]
    assert addressed == [[(4, 2), (6, 30), (8, 30)], [(4, 2), (6, 30)]]


def test_the_machine_wires_the_shrinking_tee_chain():
    from littleman.lllm_step import LLM_PLACE, TEE_ROWS, build_llm_machine

    grid = build_llm_machine().split("\n")
    reads = []
    for tag in ("TEE1", "TEE2"):
        row, col = LLM_PLACE[tag]
        block = grid[row : row + TEE_ROWS + 2]
        reads.append(sum(line[col : col + 36].count("r") for line in block))
    assert reads == [5, 4]            # addressed reads plus the two loop reads
