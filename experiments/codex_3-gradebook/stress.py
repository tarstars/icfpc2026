#!/usr/bin/env python
"""Deterministic adversarial validation for the codex_3 Grade Book candidate."""

from __future__ import annotations

import importlib.util
import pathlib
import random

from littleman import server_compat
from littleman.judge import judge_case

ROOT = pathlib.Path(__file__).resolve().parents[2]
BUILD_PATH = ROOT / "experiments" / "codex_3-gradebook" / "build.py"


def _candidate() -> str:
    spec = importlib.util.spec_from_file_location("codex3_gradebook_build", BUILD_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_candidate()


def _random_case(seed: int) -> list[dict]:
    rng = random.Random(seed)
    count = rng.randint(4, 16)
    subjects = rng.randint(1, 4)
    ids = rng.sample(range(1000, 10000), count)
    grades = {student: [rng.randint(0, 100) for _ in range(subjects)] for student in ids}
    roster = [count, subjects]
    for student in ids:
        roster.extend((student, *grades[student]))
    rounds = [{"in": list(map(str, roster)), "out": []}]

    for _ in range(rng.randint(5, 10)):
        operations = rng.randint(1, 8)
        inputs = [operations]
        outputs = []
        for _ in range(operations):
            operation = rng.choices((1, 2, 3, 4), weights=(4, 2, 2, 2))[0]
            subject = rng.randint(1, subjects)
            if operation == 1:
                student = rng.choice(ids)
                inputs.extend((1, student, subject))
                outputs.append(grades[student][subject - 1])
            elif operation == 2:
                student = rng.choice(ids)
                value = rng.randint(0, 100)
                inputs.extend((2, student, subject, value))
                grades[student][subject - 1] = value
            elif operation == 3:
                inputs.extend((3, subject))
                outputs.append(sum(grades[student][subject - 1] for student in ids) // count)
            else:
                inputs.extend((4, subject))
                best = max(grades[student][subject - 1] for student in ids)
                outputs.append(min(student for student in ids if grades[student][subject - 1] == best))
        rounds.append({"in": list(map(str, inputs)), "out": list(map(str, outputs))})
    return rounds


def _debruijn(alphabet: int, order: int) -> list[int]:
    state = [0] * (alphabet * order)
    sequence = []

    def visit(position: int, period: int) -> None:
        if position > order:
            if order % period == 0:
                sequence.extend(state[1 : period + 1])
            return
        state[position] = state[position - period]
        visit(position + 1, period)
        for symbol in range(state[position - period] + 1, alphabet):
            state[position] = symbol
            visit(position + 1, position)

    visit(1, 1)
    return sequence


def _transition_cases() -> list[list[dict]]:
    count, subjects = 16, 4
    ids = [1000 + index * 137 for index in range(count)]
    grades = [[(index * 17 + subject * 23) % 101 for subject in range(subjects)] for index in range(count)]
    book = dict(zip(ids, grades, strict=True))
    roster = [count, subjects]
    for student in ids:
        roster.extend((student, *book[student]))

    def action(symbol: int) -> tuple[list[int], int]:
        kind = ("get_first", "get_last", "avg", "top")[symbol // 4]
        subject = symbol % 4 + 1
        if kind == "get_first":
            return [1, ids[0], subject], book[ids[0]][subject - 1]
        if kind == "get_last":
            return [1, ids[-1], subject], book[ids[-1]][subject - 1]
        values = [book[student][subject - 1] for student in ids]
        if kind == "avg":
            return [3, subject], sum(values) // count
        best = max(values)
        return [4, subject], min(student for student in ids if book[student][subject - 1] == best)

    cycle = _debruijn(16, 2)
    symbols = cycle + [cycle[0]]
    chunks = []
    start = 0
    while start < len(symbols) - 1:
        end = min(start + 79, len(symbols) - 1)
        chunks.append(symbols[start : end + 1])
        start = end

    cases = []
    for chunk in chunks:
        rounds = [{"in": list(map(str, roster)), "out": []}]
        for offset in range(0, len(chunk), 8):
            operations = chunk[offset : offset + 8]
            inputs = [len(operations)]
            outputs = []
            for symbol in operations:
                encoded, expected = action(symbol)
                inputs.extend(encoded)
                outputs.append(expected)
            rounds.append({"in": list(map(str, inputs)), "out": list(map(str, outputs))})
        assert len(rounds) - 1 <= 10
        cases.append(rounds)
    return cases


def main() -> None:
    text = _candidate()
    server_compat.validate_layout(text)

    for seed in range(100, 124):
        result = judge_case(text, _random_case(seed), max_ticks=5_000_000)
        if not result.passed:
            raise SystemExit(f"random seed {seed} failed: {result}")
        print(f"random seed {seed}: pass ticks={result.ticks}")

    edges = 0
    for index, rounds in enumerate(_transition_cases()):
        result = judge_case(text, rounds, max_ticks=5_000_000)
        if not result.passed:
            raise SystemExit(f"transition chunk {index} failed: {result}")
        actions = sum(int(round_["in"][0]) for round_ in rounds[1:])
        edges += actions - 1
        print(f"transition chunk {index}: pass actions={actions} ticks={result.ticks}")
    assert edges == 256
    print("all 24 random cases and all 256 ordered output transitions passed")


if __name__ == "__main__":
    main()
