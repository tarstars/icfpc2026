"""LLLM STEP station: MODEL-FIRST acceptance (work order claude_11b).

`StepModel` + the scripted claude_11a FETCH stub must reproduce the
`littleman.llm` oracle's frames, expressed through the claude_10 delta
grammar, on every public case and a 100-case fuzz corpus.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import llm_fuzz
from littleman.llm import LLM
from littleman.lllm_step import (
    CLASS_HALT,
    CLASS_WALL,
    ScriptedFetch,
    StepModel,
    case_rounds,
    frames_from_deltas,
    loader_stream,
    oracle_frames,
    pack_world,
    run_case,
)

PROBLEM = json.loads(
    (
        Path(__file__).resolve().parents[1]
        / "data/small/problems/little-little-little-man.json"
    ).read_text()
)
CASES = PROBLEM["publicTestData"]
FUZZ = llm_fuzz.corpus(20260726, 100)


def rows_of(case):
    return case_rounds(case)[0]


def check(rows, ks):
    """Run the model and assert its delta stream renders the oracle frames."""
    model = run_case(rows, ks)
    assert frames_from_deltas(model.deltas) == oracle_frames(rows, ks)
    return model


# ------------------------------------------------------- hard gate (acc. 1)
@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_public_case_frames(case):
    rows, ks, frames = case_rounds(case)
    model = run_case(rows, ks)
    assert frames_from_deltas(model.deltas) == frames


def test_fuzz_corpus_frames():
    bad = []
    for i, case in enumerate(FUZZ):
        rows, ks, frames = case_rounds(case)
        if frames_from_deltas(run_case(rows, ks).deltas) != frames:
            bad.append(i)
    assert bad == []


# --------------------------------------------------------- frozen grammars
@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_delta_grammar(case):
    """claude_10: pixels in [0,4095], one negative sentinel per round."""
    rows, ks, _ = case_rounds(case)
    deltas = run_case(rows, ks).deltas
    rounds = [[]]
    for token in deltas:
        if token < 0:
            rounds.append([])
        else:
            assert 0 <= token <= 4095
            rounds[-1].append(token)
    assert rounds.pop() == []                      # stream ends on a commit
    assert len(rounds) == 1 + len(ks)
    assert len(rounds[0]) == 257                   # 256 static + the man
    assert [t // 16 for t in rounds[0][:256]] == list(range(256))
    assert rounds[0][256] % 16 == 9
    assert all(len(r) == 2 and r[1] % 16 == 9 for r in rounds[1:])


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_fetch_request_grammar(case):
    """claude_11a: 64 setup tokens verbatim, then only legal requests."""
    rows, ks, _ = case_rounds(case)
    fetch = ScriptedFetch()
    run_case(rows, ks, fetch=fetch)
    assert loader_stream(rows)[:64] == [
        sum(fetch.records[4 * j + i] << (13 * i) for i in range(4))
        for j in range(64)
    ]
    assert fetch.setup_left == 0
    assert fetch.requests[0] == -1                 # round 1 asks for the frame
    assert fetch.requests.count(-1) == 1
    assert all(-1 <= t <= 511 for t in fetch.requests)
    colour_fetches = [t for t in fetch.requests if t >= 256]
    assert len(colour_fetches) == len(ks)          # exactly one per later round


def test_setup_seeds_control_state():
    rows = rows_of(CASES[1])
    _, man_addr = pack_world(rows)
    model = StepModel(ScriptedFetch())
    model.setup(loader_stream(rows))
    assert model.ring == [man_addr, 1, 0, 0, man_addr]   # heading East, live


def test_determinism():
    rows, ks, _ = case_rounds(CASES[0])
    assert run_case(rows, ks).deltas == run_case(rows, ks).deltas


# ------------------------------------------------------- directed (acc. 3)
HALT = ["+----+", "|@ H |", "|    |", "+----+"]
WALL = ["+---+", "|@  |", "|   |", "+---+"]
# a closed 8-tick racetrack; each lap runs `M` then `+`, so A_i doubles
RING = ["+----+", "|@9v |", "|vM< |", "|    |", "|>+^ |", "+----+"]
X_ZERO = ["+----+", "|@X  |", "|    |", "+----+"]
X_POS = ["+----+", "|@1X |", "|    |", "+----+"]
X_NEG = ["+------+", "|@1M--X|", "|      |", "+------+"]


def test_halt_mid_round():
    """H at tick 3 of a k=10 round: the rest of the round is skipped."""
    model = check(HALT, [10, 5])
    assert model.ticks == 3
    assert model._read("CTRL") & 4                 # frozen
    assert len(model.deltas) == 257 + 1 + 2 * 3    # both rounds still emit


def test_wall_freeze_then_sentinel_only_rounds():
    """The wall is found by the NEXT fetch; later rounds are no-ops."""
    model = check(WALL, [8, 4, 4])
    assert model.ticks == 4                        # 3 moves + the discovery
    rounds = "".join("|" if t < 0 else "." for t in model.deltas).split("|")
    assert [len(r) for r in rounds[1:-1]] == [2, 2, 2]
    tail = model.deltas[-6:]
    assert tail[0] == tail[3] and tail[1] == tail[4]   # frame stops changing


def test_branch_all_three_arms():
    for rows in (X_ZERO, X_POS, X_NEG):
        check(rows, [6, 6])
    ends = [run_case(rows, [6])._read("ADDR") for rows in (X_ZERO, X_POS, X_NEG)]
    assert len(set(ends)) == 3                     # straight / cw / ccw differ


def test_old_equals_addr_round():
    """A full lap of the racetrack ends where it began; still emits."""
    model = run_case(RING, [3, 8])
    assert frames_from_deltas(model.deltas) == oracle_frames(RING, [3, 8])
    assert model.trace[-1][3] == model.trace[-1][4]
    assert len(model.deltas) == 257 + 1 + 2 * 3


def test_wrap64_loop_and_k64():
    """8 rounds of k=64: 61 doublings from 9 push A_i past 2**63."""
    ks = [64] * 8
    model = check(RING, ks)
    assert model.ticks == 512
    reference = LLM.parse(RING)
    reference.run(512)
    assert model._read("AI") < 0                   # native 64-bit wrap
    assert model._read("AI") == reference.men[0].A


def test_thirty_rounds():
    ks = [1] * 29
    model = check(RING, ks)
    assert len(model.trace) == 30
    assert model.deltas.count(-1) == 30


# ------------------------------------------------------ counts / invariant
def oracle_ticks(rows, ks):
    machine = LLM.parse(rows)
    count = 0
    for k in ks:
        for _ in range(k):
            if machine.halted():
                break
            machine.step()
            count += 1
    return count


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_interpreted_tick_counts(case):
    """STEP runs at most one extra tick: the one that *discovers* a wall."""
    rows, ks, _ = case_rounds(case)
    model = run_case(rows, ks)
    assert model.ticks <= sum(ks)
    assert model.ticks - oracle_ticks(rows, ks) in (0, 1)


# -------------------------------------------- phase 2 hooks (auto-arming)
def _module(name):
    try:
        return __import__(f"littleman.{name}", fromlist=["*"])
    except ImportError:
        return None


@pytest.mark.skipif(_module("lllm_loader") is None, reason="claude_09 not landed")
def test_local_packer_matches_real_loader():
    loader = _module("lllm_loader")
    for case in CASES:
        rows = rows_of(case)
        expected = list(loader.reference_stream(llm_fuzz.program_tokens(rows)))
        assert expected[:65] == loader_stream(rows)


@pytest.mark.skipif(_module("lllm_fetch") is None, reason="claude_11a not landed")
def test_integration_rig_with_real_fetch():
    from littleman.lllm_step import ReferenceFetch

    for case in CASES + FUZZ[:30]:
        rows, ks, _ = case_rounds(case)
        assert (
            run_case(rows, ks, fetch=ReferenceFetch()).deltas
            == run_case(rows, ks).deltas
        )


# --------------------------------------------------- phase 2: the STEP room
from littleman.lllm_step import (  # noqa: E402
    STEP_AT, STEP_COLS, STEP_ROWS, Tape, build_step_rig, build_step_room,
)
from littleman.sim import Machine  # noqa: E402

RIG = build_step_rig()
SR, SC = STEP_AT


def intended_port(row, col, op):
    """The room's three-zone layout rule, stated once and asserted for real.

    Right of SCR_COL is the scratch loop; left of it, the top rows reach
    FETCH (REQ out / RESP in) and the lower rows reach the outside world
    (DRAW out / LOADER in).
    """
    from littleman.lllm_step import REQ_MAX_ROW, SCR_COL

    if col >= SCR_COL:
        return "SCR_OUT" if op == "s" else "SCR"
    if row <= REQ_MAX_ROW:
        return "REQ" if op == "s" else "RESP"
    return "DRAW" if op == "s" else "LOAD"


def step_bindings():
    """{(room row, col): (op, port actually reached)} from the engine's map."""
    from littleman.ir_export import machine_ir

    ir = machine_ir(RIG)
    out = {}
    for key, entry in ir["resolution"].items():
        r, c = (int(v) for v in key.split(","))
        if not (SR < r < SR + STEP_ROWS + 1 and SC < c < SC + STEP_COLS + 1):
            continue
        cells = ir["pipes"][entry["pipe"]]["cells"]
        end = cells[0] if entry["op"] == "s" else cells[-1]
        out[(r - SR, c - SC)] = (entry["op"], PORTS[tuple(end)])
    return out
PORTS = {
    (SR + 2, SC - 1): "REQ", (SR + 20, SC - 1): "DRAW", (SR + 21, SC - 1): "LOAD",
    (SR - 1, SC + 8): "RESP", (SR + 30, SC + 74): "SCR_OUT",
    (SR + 33, SC + 74): "SCR",
}


def test_rig_layout_gates():
    from littleman import alexey_pipecheck, server_compat

    machine = Machine.parse(RIG)
    assert len(machine.rooms) == 6 and len(machine.pipes) == 8
    assert server_compat.validate_layout(RIG) is None
    assert alexey_pipecheck.check(RIG) is None


def test_rig_is_deterministic():
    assert build_step_rig() == RIG
    assert build_step_room().render() == build_step_room().render()


def test_binding_audit_is_engine_true():
    """Every s/r resolves to its zone's port (ir_export map, no hand math)."""
    bound = step_bindings()
    assert len(bound) >= 11
    wrong = {
        cell: got
        for cell, (op, got) in bound.items()
        if got != intended_port(cell[0], cell[1], op)
    }
    assert wrong == {}


def test_binding_margins():
    """room_ports margin: how far a port may slide before a binding flips."""
    from littleman.room_ports import Op, audit

    machine = Machine.parse(RIG)
    step = next(r for r in machine.rooms if (r.top, r.left) == (SR, SC))
    ops = [
        Op((SR + r, SC + c), port, port in ("REQ", "DRAW", "SCR_OUT"))
        for (r, c), (_, port) in step_bindings().items()
    ]
    report = audit(machine, step, ops)
    assert report["satisfied"]
    assert report["margin"] >= 2, report["margin"]


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_rig_round_one_matches_model(case):
    """The real FETCH station drives the room to a byte-exact first frame."""
    rows = rows_of(case)
    res = Machine.parse(RIG).run(max_ticks=300_000, inputs=loader_stream(rows))
    assert res.output == run_case(rows, []).deltas


def test_rig_round_one_matches_model_on_fuzz():
    bad = [
        i for i, case in enumerate(FUZZ[:30])
        if Machine.parse(RIG).run(
            max_ticks=300_000, inputs=loader_stream(rows_of(case))
        ).output != run_case(rows_of(case), []).deltas
    ]
    assert bad == []


def test_tick_interpreter_not_transcribed_yet():
    """Without a k token, STEP parks at the later-round input as intended."""
    rows = rows_of(CASES[1])
    res = Machine.parse(RIG).run(max_ticks=300_000, inputs=loader_stream(rows))
    assert len(res.output) == 258 and res.output[-1] == -1


def test_tick_skeleton_reaches_class_stub():
    """The round-in, halt check, FETCH, and three blank crossings are live."""
    rows = rows_of(CASES[1])
    machine = Machine.parse(RIG)
    res = machine.run(
        max_ticks=100_000, inputs=loader_stream(rows) + [1]
    )
    man = next(
        m for m in machine.men
        if (m.room.top, m.room.left) == (SR, SC)
    )
    assert res.output == run_case(rows, []).deltas
    assert (man.r - SR, man.c - SC) == (44, 66)
    assert machine.grid[man.r][man.c] == "H"
    assert man.halted
    for row, col in ((10, 60), (11, 60), (11, 65)):
        assert machine.grid[SR + row][SC + col] == " "


def test_round_loop_tapes_place_without_collision():
    """The seed and round-in choreography is independently placeable."""
    from littleman.lllm_fetch import Room
    from littleman.lllm_step import STEP_COLS, STEP_ROWS, _step_seed

    room = Room(STEP_ROWS, STEP_COLS)
    room.put(23, 3, ">")
    _step_seed(room)
    grid = room.render()
    assert grid[23].count("r") + grid[24].count("r") >= 1     # ring reads
    assert "H" in "".join(grid)                               # loop stub


def test_tape_rejects_non_descending_exit():
    from littleman.lllm_fetch import Room

    tape = Tape(Room(4, 12), 2, 5, 5, 11).emit("M")
    with pytest.raises(ValueError, match="cannot descend"):
        tape.down_at(10, 2)


def test_tape_snakes_and_reverses_literals():
    from littleman.lllm_fetch import Room

    room = Room(4, 12)
    Tape(room, 1, 5, 5, 11).emit("M", "#256", "+", "#16", "s")
    grid = room.render()
    assert "`256`" in grid[1]                    # left-to-right lap
    assert "`61`" in grid[2]                     # digits reversed walking west
    assert "v" in grid[1] and "<" in grid[2]     # the lap turned at the edge


def test_class_table_is_the_frozen_one():
    """Wall and halt are the only two freezing classes."""
    rows = ["+---+", "|@H |", "|   |", "+---+"]
    fetch = ScriptedFetch()
    for token in loader_stream(rows)[:64]:
        fetch.send(token)
    assert fetch.send(0) == [CLASS_WALL << 4]
    assert fetch.send(18) == [CLASS_HALT << 4]
    assert fetch.send(0 + 256) == [4] and fetch.send(18 + 256) == [3]
