"""Differential proof that `littleman.fastsim` is bit-exact against `sim`.

Every result the team has rests on `sim.py`'s semantics, so the fast
executor is only allowed to exist if it is indistinguishable from it.  This
module compares, for every run, the *whole* observable state: RunResult
status/error/ticks/output/output_ticks/frames/frame_ticks, plus every man's
position, heading, A/B/BP, halted and blocked flags, plus every pipe's cell
contents, plus every display's cursor and both buffers.

Coverage:
  * every `.man` artifact under `submissions/**` against its problem's
    public test cases (with the judge's RoundController, i.e. the real
    gating path), bounded by FASTSIM_TEST_BUDGET ticks per case;
  * the LLLM/LLM fuzz corpora (display frames + on_frame verdicts);
  * random input vectors fed to real artifacts without a controller;
  * single-character mutations of small artifacts, which is what reaches
    the "wall", "bad-op" and "no-pipe" error paths and man-on-man
    collisions.

The C extension is exercised when built; the pure-Python fast loop is
always exercised too (via LITTLEMAN_FASTSIM_EXT=0 equivalent switching).
"""

from __future__ import annotations

import json
import os
import pathlib
import random

import pytest

from littleman import fastsim, judge, sim

REPO = pathlib.Path(__file__).resolve().parent.parent
PROBLEMS = REPO / "data" / "small" / "problems"
BUDGET = int(os.environ.get("FASTSIM_TEST_BUDGET", "30000"))

SLUG = {
    "atoi": "atoi",
    "brackets": "brackets",
    "gradebook": "gradebook",
    "hello-world": "hello-world",
    "history": "history-lesson",
    "lllm": "little-little-little-man",
    "llm": "little-little-man",
    "matmul": "matmul",
    "max-element": "max-element",
    "memory": "memory",
    "palette": "palette",
    "plotter": "plotter",
    "reverse-a-list": "reverse-a-list",
    "snake": "snake",
    "sort": "sort-numbers",
    "subset-sum": "subset-sum",
    "sudoku-validity": "sudoku-validity",
    "tcp": "tcp",
    "triangle": "triangle",
}


def snapshot(machine, res):
    """Everything an observer can see after a run."""
    return {
        "status": res.status,
        "error": res.error,
        "ticks": res.ticks,
        "output": list(res.output),
        "output_ticks": list(res.output_ticks),
        "frames": [[list(row) for row in f] for f in res.frames],
        "frame_ticks": list(res.frame_ticks),
        "men": [
            (m.r, m.c, m.direction, m.A, m.B, m.BP, m.halted, m.blocked)
            for m in machine.men
        ],
        "pipes": [list(p.values) for p in machine.pipes],
        "displays": [
            (d.cursor, [list(r) for r in d.current], [list(r) for r in d.next])
            for d in machine.displays
        ],
    }


def _run(module, text, *, rounds=None, inputs=None, cap):
    machine = module.Machine.parse(text)
    controller = judge.RoundController(rounds) if rounds is not None else None
    res = machine.run(inputs=inputs, max_ticks=cap, controller=controller)
    return snapshot(machine, res)


def assert_same(text, *, rounds=None, inputs=None, cap, label):
    """Fail loudly, naming the first differing observable."""
    reference = _run(sim, text, rounds=rounds, inputs=inputs, cap=cap)
    fast = _run(fastsim, text, rounds=rounds, inputs=inputs, cap=cap)
    if reference == fast:
        return
    for key in reference:
        if reference[key] != fast[key]:
            detail = ""
            if key in ("output", "output_ticks", "frame_ticks"):
                for i, (a, b) in enumerate(zip(reference[key], fast[key])):
                    if a != b:
                        detail = f" first differing element #{i}: {a!r} vs {b!r}"
                        break
            pytest.fail(
                f"fastsim diverged from sim on {label}: field {key!r}"
                f" (sim ticks={reference['ticks']},"
                f" fast ticks={fast['ticks']}).{detail}"
            )
    pytest.fail(f"fastsim diverged from sim on {label} (unknown field)")


def artifacts():
    out = []
    for path in sorted((REPO / "submissions").rglob("*.man")):
        slug = SLUG.get(path.parent.name) or SLUG.get(path.parent.parent.name)
        if slug is None:
            continue
        out.append((path, slug))
    return out


ARTIFACTS = artifacts()


def _problem(slug):
    return json.loads((PROBLEMS / f"{slug}.json").read_text())


@pytest.mark.parametrize(
    "path,slug", ARTIFACTS, ids=[f"{p.parent.name}/{p.name}" for p, _ in ARTIFACTS]
)
def test_submission_artifact_matches_sim(path, slug):
    """Every shipped .man, every public case, both executors."""
    text = path.read_text()
    try:
        sim.Machine.parse(text)
    except sim.LoadError:
        pytest.skip("artifact does not load under sim (experiment/probe file)")
    problem = _problem(slug)
    cap = min(problem.get("tickCap") or 5_000_000, BUDGET)
    for case in problem["publicTestData"]:
        assert_same(
            text,
            rounds=judge.normalize_case(case),
            cap=cap,
            label=f"{path.name}::{case['name']}",
        )


@pytest.mark.parametrize(
    "path,slug",
    [(p, s) for p, s in ARTIFACTS if p.parent.name in ("matmul", "llm", "plotter")],
    ids=lambda v: getattr(v, "name", str(v)),
)
def test_pure_python_fast_loop_matches_sim(path, slug, monkeypatch):
    """Same proof with the C extension switched off."""
    monkeypatch.setattr(fastsim, "USE_EXTENSION", False)
    text = path.read_text()
    problem = _problem(slug)
    cap = min(problem.get("tickCap") or 5_000_000, 20_000)
    for case in problem["publicTestData"]:
        assert_same(
            text,
            rounds=judge.normalize_case(case),
            cap=cap,
            label=f"pure-python {path.name}::{case['name']}",
        )


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_llm_fuzz_corpus_matches_sim(seed):
    """Display frames, on_frame verdicts and the LLM/LLLM interpreters."""
    from littleman import llm_fuzz

    art = REPO / "submissions" / "llm" / "llm_03.man"
    text = art.read_text()
    frames = 0
    for case in llm_fuzz.corpus(seed, 4, tick_cap=100):
        rounds = judge.normalize_case(case)
        assert_same(
            text,
            rounds=rounds,
            cap=400_000,
            label=f"llm_fuzz seed={seed} {case['name']}",
        )
        machine = fastsim.Machine.parse(text)
        frames += len(
            machine.run(
                max_ticks=400_000, controller=judge.RoundController(rounds)
            ).frames
        )
    assert frames > 0, "display/frame path was not exercised"


FUZZ_ARTIFACTS = [
    p
    for p, _ in ARTIFACTS
    if p.name
    in {
        "matmul_03.man", "sort_06.man", "reverse_01.man", "atoi_00.man",
        "max_00.man", "brackets_02.man", "tcp_00.man", "memory_06.man",
        "gradebook_03.man", "sudoku_02.man", "subset_sum_00.man",
        "history_01.man", "snake_01.man", "triangle_02.man",
    }
]


@pytest.mark.parametrize("seed", [11, 12, 13, 14])
def test_random_inputs_match_sim(seed):
    """Real layouts, random data, no controller: pipes, blocking, wrapping."""
    rng = random.Random(seed)
    for path in FUZZ_ARTIFACTS:
        text = path.read_text()
        try:
            sim.Machine.parse(text)
        except sim.LoadError:
            continue
        for _ in range(2):
            n = rng.randint(0, 12)
            scale = rng.choice([1, 1, 10, 1000, 1 << 31, (1 << 63) - 1])
            inputs = [rng.randrange(-scale, scale + 1) for _ in range(n)]
            assert_same(
                text,
                inputs=inputs,
                cap=4000,
                label=f"random-inputs {path.name} seed={seed} inputs={inputs!r}",
            )


MUTATION_ALPHABET = " .@><^vVHMW+-*N%/&|~{}XsSrRUqbmda]x`0123456789"


@pytest.mark.parametrize("seed", [21, 22, 23, 24, 25, 26])
def test_mutated_programs_match_sim(seed):
    """Single-character mutations reach wall / bad-op / no-pipe / collisions."""
    rng = random.Random(seed)
    sources = [
        p.read_text()
        for p in FUZZ_ARTIFACTS
        if p.name in {"max_00.man", "reverse_01.man", "atoi_00.man", "sort_06.man"}
    ]
    checked = 0
    attempts = 0
    while checked < 25 and attempts < 400:
        attempts += 1
        text = rng.choice(sources)
        rows = text.split("\n")
        r = rng.randrange(len(rows))
        if not rows[r]:
            continue
        c = rng.randrange(len(rows[r]))
        ch = rng.choice(MUTATION_ALPHABET)
        mutated = rows[:]
        mutated[r] = rows[r][:c] + ch + rows[r][c + 1:]
        candidate = "\n".join(mutated)
        try:
            sim.Machine.parse(candidate)
        except Exception:
            continue
        inputs = [rng.randrange(-50, 50) for _ in range(rng.randint(0, 6))]
        assert_same(
            candidate,
            inputs=inputs,
            cap=3000,
            label=f"mutation seed={seed} at ({r},{c}) -> {ch!r}",
        )
        checked += 1
    assert checked >= 20, "mutation fuzz produced too few loadable programs"


def test_extension_is_optional():
    """Nothing may break when the C extension is absent."""
    assert isinstance(fastsim.HAVE_EXTENSION, bool)
    machine = fastsim.Machine.parse(
        (REPO / "submissions" / "max-element" / "max_00.man").read_text()
    )
    assert machine.run(inputs=[3, 1, 2], max_ticks=500).ticks > 0
