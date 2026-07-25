"""The fuzz generator must emit well-formed, deterministic, oracle-true cases."""

from __future__ import annotations

import random

from littleman.llm import LLM, program_grid
from littleman.llm_fuzz import (
    corpus,
    llm_corpus,
    program_tokens,
    random_case,
    random_llm_case,
    random_llm_program,
    random_program,
)
from littleman.sim import Machine


def test_random_programs_are_well_formed():
    rng = random.Random(1)
    for _ in range(200):
        rows = random_program(rng)
        height, width = len(rows), len(rows[0])
        assert 4 <= width <= 16 and 4 <= height <= 16
        assert all(len(r) == width for r in rows)
        assert sum(row.count("@") for row in rows) == 1
        machine = Machine.parse("\n".join(rows))   # single outer room
        assert len(machine.rooms) == 1 and len(machine.men) == 1
        room = machine.rooms[0]
        assert (room.top, room.left, room.bottom, room.right) == (
            0, 0, height - 1, width - 1,
        )


def test_tokens_round_trip_through_program_grid():
    rng = random.Random(2)
    rows = random_program(rng)
    assert program_grid(program_tokens(rows)) == rows


def test_cases_respect_the_input_contract():
    rng = random.Random(3)
    for _ in range(60):
        case = random_case(rng, tick_cap=200)
        rounds = case["rounds"]
        assert 1 <= len(rounds) <= 30
        assert rounds[0]["frames"] and len(rounds[0]["frames"][0]) == 16
        total = 0
        for rnd in rounds[1:]:
            step = int(rnd["in"][0])
            assert 1 <= step <= 64
            total += step
        assert total <= 200
        # no step command after the program halts: replay and confirm the
        # machine is live before every issued step
        machine = LLM.parse(program_grid([int(v) for v in rounds[0]["in"]]))
        for rnd in rounds[1:]:
            assert not machine.halted()
            machine.run(int(rnd["in"][0]))


def test_corpus_is_deterministic_and_varied():
    a = corpus(20260725, 40)
    b = corpus(20260725, 40)
    assert a == b
    halted = varied = 0
    shapes = set()
    for case in a:
        rounds = case["rounds"]
        rows = program_grid([int(v) for v in rounds[0]["in"]])
        shapes.add((len(rows[0]), len(rows)))
        machine = LLM.parse(rows)
        for rnd in rounds[1:]:
            machine.run(int(rnd["in"][0]))
        halted += machine.halted()
        varied += len(rounds) > 2
    assert len(shapes) >= 10          # real size diversity
    assert halted >= 20               # most programs end (wall or H)
    assert varied >= 20               # most cases have several rounds


def test_frames_match_a_fresh_replay():
    """The recorded frames must equal an independent re-run of the oracle."""
    for case in corpus(7, 15):
        rounds = case["rounds"]
        machine = LLM.parse(program_grid([int(v) for v in rounds[0]["in"]]))
        assert machine.render() == rounds[0]["frames"][0]
        for rnd in rounds[1:]:
            machine.run(int(rnd["in"][0]))
            assert machine.render() == rnd["frames"][0]


# --------------------------------------------------------------- multi-room


def test_random_llm_programs_are_well_formed():
    rng = random.Random(11)
    for _ in range(120):
        rows = random_llm_program(rng)
        height = len(rows)
        width = len(rows[0])
        assert all(len(r) == width for r in rows)
        assert 4 <= width <= 16 and 4 <= height <= 16
        machine = Machine.parse("\n".join(rows))
        assert 2 <= len(machine.rooms) <= 3
        assert 1 <= len(machine.pipes) <= 2
        assert sum(len(p.cells) for p in machine.pipes) <= 20
        assert sum(row.count("@") for row in rows) == len(machine.rooms)
        out_rooms = {id(p.source) for p in machine.pipes}
        in_rooms = {id(p.dest) for p in machine.pipes}
        for room in machine.rooms:
            rr, cr = room.interior()
            has_s = any(machine.grid[r][c] == "s" for r in rr for c in cr)
            has_r = any(machine.grid[r][c] == "r" for r in rr for c in cr)
            assert has_s == (id(room) in out_rooms)
            assert has_r == (id(room) in in_rooms)


def test_llm_cases_respect_the_input_contract():
    rng = random.Random(5)
    for _ in range(40):
        case = random_llm_case(rng)
        rounds = case["rounds"]
        assert 1 <= len(rounds) <= 30
        assert rounds[0]["frames"] and len(rounds[0]["frames"][0]) == 16
        total = 0
        for rnd in rounds[1:]:
            step = int(rnd["in"][0])
            assert 1 <= step <= 64
            total += step
        assert total <= 100
        machine = LLM.parse(program_grid([int(v) for v in rounds[0]["in"]]))
        for rnd in rounds[1:]:
            assert not machine.halted()
            machine.run(int(rnd["in"][0]))


def test_llm_pipe_values_stay_in_domain():
    """Every value ever resident in a pipe must be within -9..9."""
    for case in llm_corpus(2026, 25):
        rounds = case["rounds"]
        machine = LLM.parse(program_grid([int(v) for v in rounds[0]["in"]]))
        for rnd in rounds:
            if rnd is not rounds[0]:
                machine.run(int(rnd["in"][0]))
            for pipe in machine.pipes:
                for v in pipe.values:
                    assert v is None or -9 <= v <= 9


def test_llm_frames_match_a_fresh_replay():
    """The recorded frames must equal an independent re-run of the oracle."""
    for case in llm_corpus(7, 15):
        rounds = case["rounds"]
        machine = LLM.parse(program_grid([int(v) for v in rounds[0]["in"]]))
        assert machine.render() == rounds[0]["frames"][0]
        for rnd in rounds[1:]:
            machine.run(int(rnd["in"][0]))
            assert machine.render() == rnd["frames"][0]


def test_llm_corpus_is_deterministic():
    a = llm_corpus(20260725, 30)
    b = llm_corpus(20260725, 30)
    assert a == b


def test_llm_corpus_coverage():
    """Real pipe traffic, real halts, and at least one stuck-in-transit case."""
    cases = llm_corpus(20260726, 120)
    e_cases = halted_cases = residual_cases = 0
    for case in cases:
        rounds = case["rounds"]
        machine = LLM.parse(program_grid([int(v) for v in rounds[0]["in"]]))
        any_e = any("e" in row for row in rounds[0]["frames"][0])
        for rnd in rounds[1:]:
            machine.run(int(rnd["in"][0]))
            if any("e" in row for row in rnd["frames"][0]):
                any_e = True
        if any_e:
            e_cases += 1
        if machine.halted():
            halted_cases += 1
        if any(any(v is not None for v in p.values) for p in machine.pipes):
            residual_cases += 1
    n = len(cases)
    assert e_cases / n >= 0.25, f"only {e_cases}/{n} cases showed a value in flight"
    assert halted_cases / n >= 0.10, f"only {halted_cases}/{n} cases halted"
    assert residual_cases >= 1, "no case ended with a value stuck in a pipe"
