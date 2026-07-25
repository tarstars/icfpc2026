"""LLLM DRAW subsystem acceptance (work order claude_10).

The rig is a pure stream transducer, so every test here is "tokens in,
frames out": deltas are computed in Python from the ``littleman.llm``
oracle's frames (never typed out), fed through the rig's ``I`` room and
judged frame-by-frame by ``littleman.judge.judge_case``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from littleman import alexey_pipecheck, server_compat, snake
from littleman.ir_export import machine_ir
from littleman.judge import judge_case
from littleman.lllm_draw import (
    DISPLAY,
    DRAW_COL,
    DRAW_ROW,
    build_addrdrv,
    build_datadrv,
    build_dist,
    build_draw_rig,
    build_swapdrv,
    delta_stream,
    draw_rounds,
)
from littleman.lllm_step import (
    case_rounds,
    frames_from_deltas,
    oracle_frames,
    run_case,
)
from littleman.sim import Machine

PROBLEM = json.loads(
    (
        Path(__file__).resolve().parents[1]
        / "data/small/problems/little-little-little-man.json"
    ).read_text()
)
CASES = PROBLEM["publicTestData"]
RIG = build_draw_rig()
MAX_TICKS = 1_000_000


def frame_of(buf: list[int]) -> list[str]:
    """16 hex rows for a 256-cell canvas buffer."""
    return [
        "".join("%x" % buf[r * DISPLAY + c] for c in range(DISPLAY))
        for r in range(DISPLAY)
    ]


def full_frame_round(buf: list[int]) -> dict:
    """Round 1 shape: 256 paints + commit, expecting ``buf``."""
    return {
        "in": [a * DISPLAY + v for a, v in enumerate(buf)] + [-1],
        "frames": [frame_of(buf)],
    }


def base_buffer() -> list[int]:
    """A non-trivial static canvas with the man (colour 9) at addr 42."""
    buf = [(a * 7) % 16 for a in range(256)]
    buf[42] = 9
    return buf


@pytest.mark.parametrize("index", range(len(CASES)))
def test_public_case_frames(index):
    """RIG FRAME EQUALITY: all 10 public cases, every frame, exact."""
    rows, ks, expected = case_rounds(CASES[index])
    frames = oracle_frames(rows, ks)
    assert frames == expected  # the oracle is the delta source
    rounds = draw_rounds(frames)
    assert len(rounds[0]["in"]) == 257  # frame 1 = 256 paints + sentinel
    assert all(len(rd["in"]) <= 3 for rd in rounds[1:])  # <= 2 pixels + commit
    result = judge_case(RIG, rounds, max_ticks=MAX_TICKS)
    assert result.passed, (index, result.reason)


def test_delta_grammar_matches_draw_oracle():
    """The Python delta stream and DRAW's semantics agree on every case."""
    for case in CASES:
        rows, ks, _ = case_rounds(case)
        frames = oracle_frames(rows, ks)
        tokens = [t for round_tokens in delta_stream(frames) for t in round_tokens]
        assert frames_from_deltas(tokens) == frames
        assert all(-1 <= t < 4096 for t in tokens)


def test_restore_precedes_the_man():
    """Later rounds restore the vacated cell before painting the new 9."""
    seen = 0
    for case in CASES:
        rows, ks, _ = case_rounds(case)
        for tokens in delta_stream(oracle_frames(rows, ks))[1:]:
            paints = tokens[:-1]
            assert tokens[-1] < 0
            if len(paints) == 2:
                assert paints[0] % DISPLAY != 9 and paints[1] % DISPLAY == 9
                seen += 1
    assert seen  # the pattern actually occurs


# ------------------------------------------------------------- directed
def test_sentinel_only_round_commits_unchanged_frame():
    """A halted man emits no pixels: the same frame must commit again."""
    buf = base_buffer()
    first = full_frame_round(buf)
    rounds = [first, {"in": [-1], "frames": [frame_of(buf)]}]
    assert judge_case(RIG, rounds, max_ticks=MAX_TICKS).passed


def test_257_paint_round():
    """EXEC's real round 1: 256 colours then the man's cell painted again."""
    buf = base_buffer()
    static = buf[:]
    static[42] = 4  # the man stands on a wall cell
    tokens = [a * DISPLAY + v for a, v in enumerate(static)]
    tokens += [42 * DISPLAY + 9, -1]  # repeated address, man on top
    rounds = [{"in": tokens, "frames": [frame_of(buf)]}]
    assert len(tokens) == 258
    assert judge_case(RIG, rounds, max_ticks=MAX_TICKS).passed


def test_sixty_back_to_back_pixels():
    """Snake's stress pattern: 60 consecutive paints inside one round."""
    buf = base_buffer()
    after = buf[:]
    for i in range(60):
        after[100 + i] = (i % 15) + 1
    rounds = [
        full_frame_round(buf),
        {
            "in": [(100 + i) * DISPLAY + after[100 + i] for i in range(60)] + [-1],
            "frames": [frame_of(after)],
        },
    ]
    assert judge_case(RIG, rounds, max_ticks=MAX_TICKS).passed


def test_man_on_a_wall_cell():
    """addr 0 is a wall in every LLLM program; colour 9 must still land."""
    buf = base_buffer()
    after = buf[:]
    after[42] = 4          # restore the wall the man left
    after[0] = 9           # man drawn on the perimeter wall
    rounds = [
        full_frame_round(buf),
        {"in": [42 * DISPLAY + 4, 0 * DISPLAY + 9, -1], "frames": [frame_of(after)]},
    ]
    assert judge_case(RIG, rounds, max_ticks=MAX_TICKS).passed


ROOM_AT = {  # name -> (top, left) of every room in the lifted block
    "DIST": (DRAW_ROW, DRAW_COL),
    "ADDRDRV": (DRAW_ROW - 7, DRAW_COL + 18),
    "DATADRV": (DRAW_ROW, DRAW_COL + 19),
    "SWAPDRV": (DRAW_ROW + 7, DRAW_COL + 20),
}

# (room, cell relative to the room's own Box) -> (op, source, dest)
EXPECTED_BINDINGS = {
    ("DIST", 2, 3): ("r", "INPUT", "DIST"),      # EXEC token stream in
    ("DIST", 1, 3): ("s", "DIST", "ADDRDRV"),    # commit arm -> chain head
    ("DIST", 3, 9): ("s", "DIST", "ADDRDRV"),    # paint arm  -> chain head
    ("ADDRDRV", 2, 3): ("r", "DIST", "ADDRDRV"),
    ("ADDRDRV", 2, 4): ("s", "ADDRDRV", "DATADRV"),   # forward the token
    ("ADDRDRV", 3, 17): ("s", "ADDRDRV", "DISPLAY"),  # addr -> TOP
    ("DATADRV", 2, 3): ("r", "ADDRDRV", "DATADRV"),
    ("DATADRV", 2, 4): ("s", "DATADRV", "SWAPDRV"),   # forward the token
    ("DATADRV", 3, 18): ("s", "DATADRV", "DISPLAY"),  # colour -> LEFT
    ("SWAPDRV", 2, 3): ("r", "DATADRV", "SWAPDRV"),
    ("SWAPDRV", 1, 2): ("s", "SWAPDRV", "DISPLAY"),   # SWAP=1 -> BOTTOM
}


def test_binding_audit():
    """Every send/read resolves to the intended pipe -- engine map, no maths."""
    ir = machine_ir(RIG)
    corner = {(r["top"], r["left"]): i for i, r in enumerate(ir["rooms"])}
    name_of = {corner[pos]: name for name, pos in ROOM_AT.items()}
    for index, room in enumerate(ir["rooms"]):
        if room["kind"] != "room":
            name_of[index] = room["kind"].upper()
    edges = {
        i: (name_of[p["source"]], name_of[p["dest"]])
        for i, p in enumerate(ir["pipes"])
    }
    seen = {}
    for key, entry in ir["resolution"].items():
        row, col = (int(v) for v in key.split(","))
        (owner,) = [
            r
            for r in ir["rooms"]
            if r["top"] < row < r["bottom"] and r["left"] < col < r["right"]
        ]
        name = name_of[ir["rooms"].index(owner)]
        seen[(name, row - owner["top"], col - owner["left"])] = (
            entry["op"],
            *edges[entry["pipe"]],
        )
    assert seen == EXPECTED_BINDINGS


def test_display_pipe_sides():
    """The three driver pipes attach to TOP / LEFT / BOTTOM, per the engine."""
    machine = Machine.parse(RIG)
    (display,) = [room for room in machine.rooms if room.kind == "display"]
    corner = {pos: name for name, pos in ROOM_AT.items()}
    sides = {
        pipe.side: corner[(pipe.source.top, pipe.source.left)]
        for pipe in machine.in_pipes[id(display)]
    }
    assert sides == {"addr": "ADDRDRV", "data": "DATADRV", "swap": "SWAPDRV"}


@pytest.mark.parametrize("index", [0, 3, 5, 9])
def test_real_exec_delta_stream(index):
    """End-to-end with the actual producer: StepModel's own DRAW output.

    ``lllm_step.StepModel`` emits round 1 as 256 colours **plus** the man
    painted on top (257 paints, a repeated address) and later rounds as
    restore/draw pairs that may name the same cell twice when the man is
    frozen -- shapes the hand-built delta stream never produces.
    """
    rows, ks, expected = case_rounds(CASES[index])
    model = run_case(rows, ks)
    rounds, tokens = [], []
    for token in model.deltas:
        tokens.append(token)
        if token < 0:
            rounds.append({"in": tokens, "frames": [expected[len(rounds)]]})
            tokens = []
    assert not tokens and len(rounds) == len(expected)
    assert len(rounds[0]["in"]) == 258
    assert judge_case(RIG, rounds, max_ticks=MAX_TICKS).passed


def test_layout_gates():
    """Parses, no shared walls, every pipe >= 2 cells, no output room."""
    machine = Machine.parse(RIG)
    server_compat.validate_layout(RIG)
    alexey_pipecheck.check(RIG)
    assert not [room for room in machine.rooms if room.kind == "output"]
    assert len(machine.men) == 4  # DIST + three drivers, one man each
    assert min(len(pipe.cells) for pipe in machine.pipes) >= 2


def test_drivers_are_copied_from_snake_verbatim():
    """The three drivers are Snake's, character for character."""
    assert build_addrdrv() == snake.build_addrdrv()
    assert build_datadrv() == snake.build_datadrv()
    assert build_swapdrv() == snake.build_swapdrv()


def test_driver_lap_race_tuning():
    """ADDRDRV rate-limits the chain: exactly 46 ticks per pixel, steady.

    46 is ADDRDRV's lap and 40 is DATADRV's; measuring the slope instead
    of asserting the constants proves the *race* (DATA never becomes the
    bottleneck and so never slips past the next pixel's ADDR), which is
    the property the tuning exists for.
    """

    def ticks_for(count):
        buf = [0] * 256
        for i in range(count):
            buf[i] = (i % 15) + 1
        rounds = [
            {
                "in": [a * DISPLAY + buf[a] for a in range(count)] + [-1],
                "frames": [frame_of(buf)],
            }
        ]
        result = judge_case(RIG, rounds, max_ticks=MAX_TICKS)
        assert result.passed
        return result.ticks

    short, mid, long = ticks_for(40), ticks_for(100), ticks_for(160)
    assert (mid - short) / 60 == 46.0
    assert (long - mid) / 60 == 46.0


def test_determinism():
    """Same text every build; same verdict and tick count every judge."""
    assert build_draw_rig() == RIG
    assert build_dist() == build_dist()
    rows, ks, _ = case_rounds(CASES[0])
    rounds = draw_rounds(oracle_frames(rows, ks))
    first = judge_case(RIG, rounds, max_ticks=MAX_TICKS)
    second = judge_case(build_draw_rig(), rounds, max_ticks=MAX_TICKS)
    assert (first.passed, first.ticks) == (second.passed, second.ticks)


def test_every_address_and_colour_is_reachable():
    """Sweep all 256 addresses through all 16 colours (t = 0..4095)."""
    buf = [0] * 256
    rounds = [full_frame_round(buf)]
    for color in range(DISPLAY):
        buf = [color] * 256
        rounds.append(
            {
                "in": [a * DISPLAY + color for a in range(256)] + [-1],
                "frames": [frame_of(buf)],
            }
        )
    assert judge_case(RIG, rounds, max_ticks=5_000_000).passed
