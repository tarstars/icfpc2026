"""Focused tests for the packed Memory candidate (`memory_02`).

Covers the 21-bit signed field encoding (directed boundaries + deterministic
randomized packing), the generated layout (parse, server compatibility, ring
capacity, pipe resolution), and end-to-end behaviour against a Python oracle
on the public cases, deterministic random streams, and worst-shape capacity
cases.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from littleman import server_compat
from littleman.judge import footprint, normalize_case
from littleman.memory_packed import (
    CELLS,
    DECODE_BASE,
    FIELD_BITS,
    FIELDS_PER_WORD,
    MASK21,
    VALUE_MAX,
    VALUE_MIN,
    WORDS,
    build_memory_packed,
    cell_to_word_field,
    pack,
    read_field,
    write_field,
)
from littleman.sim import Machine, wrap64

PROBLEM = json.loads(
    (Path(__file__).resolve().parents[1] / "data/small/problems/memory.json").read_text()
)

BOUNDARY_VALUES = [
    VALUE_MIN,
    VALUE_MIN + 1,
    -1_048_576 + 48_576,  # -1_000_000 restated via the field limit
    -1,
    0,
    1,
    VALUE_MAX - 1,
    VALUE_MAX,
]


# ---------------------------------------------------------------- encoding
def test_field_domain_fits_signed_21_bits():
    """The value domain fits a signed 21-bit field with room to spare."""
    assert VALUE_MIN >= -(1 << (FIELD_BITS - 1))
    assert VALUE_MAX <= (1 << (FIELD_BITS - 1)) - 1
    assert MASK21 == (1 << FIELD_BITS) - 1
    assert DECODE_BASE == 64 - FIELD_BITS


@pytest.mark.parametrize("field", range(FIELDS_PER_WORD))
@pytest.mark.parametrize("value", BOUNDARY_VALUES)
def test_single_field_roundtrip_boundaries(field, value):
    assert read_field(write_field(0, field, value), field) == value


def test_full_domain_roundtrip_every_field():
    """Every representable value survives a round trip in every field."""
    for field in range(FIELDS_PER_WORD):
        for value in range(VALUE_MIN, VALUE_MAX + 1, 9973):  # coprime stride
            assert read_field(write_field(0, field, value), field) == value
        for value in (VALUE_MIN, 0, VALUE_MAX):
            assert read_field(write_field(0, field, value), field) == value


def test_pack_matches_repeated_write_field():
    triple = [VALUE_MIN, 0, VALUE_MAX]
    word = pack(triple)
    built = 0
    for i, v in enumerate(triple):
        built = write_field(built, i, v)
    assert word == built
    assert [read_field(word, i) for i in range(3)] == triple


def test_field_independence_random():
    """Rewriting one field never disturbs the other two."""
    rng = random.Random(20260725)
    for _ in range(4000):
        triple = [rng.randint(VALUE_MIN, VALUE_MAX) for _ in range(3)]
        word = pack(triple)
        field = rng.randrange(3)
        new = rng.randint(VALUE_MIN, VALUE_MAX)
        word = write_field(word, field, new)
        triple[field] = new
        assert [read_field(word, i) for i in range(3)] == triple


def test_words_are_non_negative_and_never_wrap():
    """Bit 63 stays clear, so no word wraps under littleman arithmetic."""
    rng = random.Random(7)
    extremes = [
        [VALUE_MIN] * 3,
        [VALUE_MAX] * 3,
        [VALUE_MIN, VALUE_MAX, VALUE_MIN],
        [0, 0, 0],
    ]
    samples = extremes + [
        [rng.randint(VALUE_MIN, VALUE_MAX) for _ in range(3)] for _ in range(2000)
    ]
    for triple in samples:
        word = pack(triple)
        assert 0 <= word < (1 << 63)
        assert wrap64(word) == word


def test_zero_word_is_plain_zero():
    """A cleared memory is the word 0, so the ring seeds with 34 zeros."""
    assert pack([0, 0, 0]) == 0
    assert all(read_field(0, i) == 0 for i in range(3))


def test_addressing_covers_every_cell_without_collisions():
    seen = {cell_to_word_field(addr) for addr in range(CELLS)}
    assert len(seen) == CELLS
    assert max(w for w, _ in seen) == WORDS - 1
    assert cell_to_word_field(99) == (33, 0)


def test_padding_slots_never_alias_a_real_cell():
    """Word 33 has two unused fields; corrupting them must not be observable."""
    words = [0] * WORDS
    for addr in range(CELLS):
        w, f = cell_to_word_field(addr)
        words[w] = write_field(words[w], f, addr - 50)
    words[33] = write_field(words[33], 1, VALUE_MAX)
    words[33] = write_field(words[33], 2, VALUE_MIN)
    for addr in range(CELLS):
        w, f = cell_to_word_field(addr)
        assert read_field(words[w], f) == addr - 50


# ------------------------------------------------------------------ layout
@pytest.fixture(scope="module")
def text():
    return build_memory_packed()


@pytest.fixture(scope="module")
def machine(text):
    return Machine.parse(text)


def test_generator_is_deterministic(text):
    assert build_memory_packed() == text


def test_artifact_matches_generator_byte_for_byte(text):
    artifact = Path(__file__).resolve().parents[1] / "submissions/memory/memory_04.man"
    assert artifact.read_bytes() == text.encode()


def test_memory_01_artifact_is_untouched():
    """`memory_01` is the accepted submission and must stay immutable."""
    artifact = Path(__file__).resolve().parents[1] / "submissions/memory/memory_01.man"
    digest = __import__("hashlib").sha256(artifact.read_bytes()).hexdigest()
    assert digest == "68d5fb3d73f21c7171ad59dde0f6b22a493cbba297f7bc1f8dcbab04cad92089"


def test_layout_passes_server_compatibility(text):
    server_compat.validate_layout(text)  # raises on a shared wall


def test_rooms_and_pipes(machine):
    assert len(machine.rooms) == 7   # I, P1, HEAD, P2, STATION, RELAY, O
    assert len(machine.men) == 5     # one per non-I/O room
    for pipe in machine.pipes:
        assert len(pipe.cells) >= 2


def test_ring_capacity_holds_every_word(machine):
    """The two ring pipes must be able to park all 34 words."""
    station = max(machine.rooms, key=lambda r: r.bottom - r.top)
    relay = min(
        (r for r in machine.rooms if r.bottom - r.top == 3 and r.right - r.left > 2),
        key=lambda r: r.right - r.left,
    )
    ring = [
        p
        for p in machine.pipes
        if {id(p.source), id(p.dest)} == {id(station), id(relay)}
    ]
    assert len(ring) == 2
    assert sum(len(p.cells) for p in ring) >= WORDS


def test_station_pipe_resolution_is_unambiguous(machine, text):
    """Every `r`/`s` in the station must resolve to the intended pipe.

    The station is the only room with two incoming and two outgoing pipes, so
    this is the one place where nearest-pipe resolution can silently go wrong.
    """
    station = max(machine.rooms, key=lambda r: r.bottom - r.top)
    relay = min(
        (r for r in machine.rooms if r.bottom - r.top == 3 and r.right - r.left > 2),
        key=lambda r: r.right - r.left,
    )
    ring_in = next(
        p for p in machine.pipes if p.dest is station and p.source is relay
    )
    ring_out = next(
        p for p in machine.pipes if p.source is station and p.dest is relay
    )
    cmd_in = next(p for p in machine.pipes if p.dest is station and p.source is not relay)
    out = next(p for p in machine.pipes if p.source is station and p.dest is not relay)

    class Probe:
        pass

    rows = text.split("\n")
    reads: dict[tuple[int, int], object] = {}
    sends: dict[tuple[int, int], object] = {}
    for r in range(station.top + 1, station.bottom):
        for c in range(station.left + 1, station.right):
            ch = rows[r][c] if c < len(rows[r]) else " "
            if ch not in "rs":
                continue
            probe = Probe()
            probe.r, probe.c, probe.room = r, c, station
            if ch == "r":
                reads[(r, c)] = machine._nearest_incoming(probe)
            else:
                sends[(r, c)] = machine._nearest_outgoing(probe)

    # Relay loops and the write splice read the ring; everything else reads
    # the command chain. Only the READ decode's final `s` targets the output.
    ring_reads = {p for p, pipe in reads.items() if pipe is ring_in}
    cmd_reads = {p for p, pipe in reads.items() if pipe is cmd_in}
    assert ring_reads | cmd_reads == set(reads)
    assert len(ring_reads) == 3   # two relay loops + the splice's old-word read
    assert len(cmd_reads) == 7

    out_sends = {p for p, pipe in sends.items() if pipe is out}
    ring_sends = {p for p, pipe in sends.items() if pipe is ring_out}
    assert ring_sends | out_sends == set(sends)
    assert len(out_sends) == 1    # the decoded READ value
    assert len(ring_sends) == 4   # seed + two relay loops + the splice


# --------------------------------------------------------------- behaviour
class Oracle:
    """Plain 100-cell memory; the packed machine must match it exactly."""

    def __init__(self):
        self.cells = [0] * CELLS

    def run(self, tokens):
        out, i = [], 0
        while i < len(tokens):
            if tokens[i] == 0:
                out.append(self.cells[tokens[i + 1]])
                i += 2
            else:
                self.cells[tokens[i + 1]] = tokens[i + 2]
                i += 3
        return out


def run_machine(text, tokens, max_ticks=2_000_000):
    machine = Machine.parse(text)
    res = machine.run([int(t) for t in tokens], max_ticks=max_ticks)
    assert res.error is None, res.error
    return res.output


@pytest.mark.parametrize("case", PROBLEM["publicTestData"], ids=lambda c: c["name"])
def test_public_case(text, case):
    assert run_machine(text, case["in"]) == [int(v) for v in case["out"]]


def test_public_cases_pass_server_compat_judge(text):
    report = server_compat.judge_problem(text, PROBLEM)
    assert report.cases_passed == report.cases_total


def test_improves_on_memory_01(text):
    """The measured local score must beat the accepted `memory_01`."""
    from littleman.memory import build_memory_compact

    baseline = server_compat.judge_problem(build_memory_compact(), PROBLEM)
    packed = server_compat.judge_problem(text, PROBLEM)
    assert packed.cases_passed == packed.cases_total
    assert packed.score < baseline.score


def _stream(rng, ops):
    tokens, reads = [], 0
    for _ in range(ops):
        addr = rng.randrange(CELLS)
        if rng.random() < 0.5:
            tokens += [0, addr]
            reads += 1
        else:
            tokens += [1, addr, rng.randint(VALUE_MIN, VALUE_MAX)]
    if reads == 0:  # a case with no output can never "pass"
        tokens += [0, 0]
    return tokens


@pytest.mark.parametrize("seed", range(6))
def test_random_streams_match_oracle(text, seed):
    rng = random.Random(1000 + seed)
    tokens = _stream(rng, 40)
    assert run_machine(text, tokens) == Oracle().run(tokens)


def test_all_cells_written_then_read(text):
    """Worst-shape capacity case: touch every one of the 100 cells."""
    tokens = []
    for addr in range(CELLS):
        tokens += [1, addr, (addr * 20_201) - 1_000_000]
    for addr in range(CELLS):
        tokens += [0, addr]
    assert run_machine(text, tokens, max_ticks=5_000_000) == Oracle().run(tokens)


def test_worst_case_ring_distance(text):
    """Successive addresses 3 words apart force near-full ring rotations."""
    tokens = []
    for step in range(20):
        addr = (step * 51) % CELLS      # jumps ~17 words each time
        tokens += [1, addr, addr - 50]
        tokens += [0, addr]
    assert run_machine(text, tokens) == Oracle().run(tokens)


def test_boundary_values_in_every_field(text):
    """The extreme values must survive in all three fields of a word."""
    tokens = []
    for base in (0, 48, 96):
        for offset, value in enumerate((VALUE_MIN, 0, VALUE_MAX)):
            tokens += [1, base + offset, value]
    for base in (0, 48, 96):
        for offset in range(3):
            tokens += [0, base + offset]
    assert run_machine(text, tokens) == Oracle().run(tokens)


def test_repeated_writes_to_one_cell(text):
    tokens = []
    for value in (VALUE_MAX, VALUE_MIN, 0, 1, -1, 999_999):
        tokens += [1, 61, value, 0, 61]
    assert run_machine(text, tokens) == Oracle().run(tokens)


def test_reported_footprint_matches_bounding_box(text):
    rows = text.split("\n")
    occupied = [
        (r, c) for r, line in enumerate(rows) for c, ch in enumerate(line) if ch != " "
    ]
    width = max(c for _, c in occupied) - min(c for _, c in occupied) + 1
    height = max(r for r, _ in occupied) - min(r for r, _ in occupied) + 1
    assert footprint(text) == max(width, height) ** 2


def test_normalize_case_shape_is_single_round():
    assert len(normalize_case(PROBLEM["publicTestData"][0])) == 1
