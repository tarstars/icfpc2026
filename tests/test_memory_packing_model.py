"""Correctness proof for three-values-per-word Memory packing.

Covers: encode/decode over the full value domain, pack/unpack with
boundary and random field combinations, ordering (monotonicity + field
independence), signed-64-bit safety (no wrap), padding (unused slots
never affect in-range cells), and functional equivalence of the packed
memory against a plain unpacked memory over the real public cases and
seeded random operation streams.
"""

import json
import random
from pathlib import Path

import pytest

from littleman.memory_packing_model import (
    BASE,
    CELLS,
    FIELDS_PER_WORD,
    MAX_FIELD,
    OFFSET,
    SIGNED64_MAX,
    SLOTS,
    VALUE_MAX,
    VALUE_MIN,
    WORD_MAX,
    WORDS,
    ZERO_WORD,
    PackedMemory,
    PackingError,
    cell_to_word_field,
    decode_value,
    encode_value,
    pack_values,
    peel,
    project_score,
    read_field,
    ring_capacity_reduction,
    signed64_safe,
    unpack_fields,
    unpack_values,
    write_field,
)

PROBLEMS = Path(__file__).resolve().parent.parent / "data" / "small" / "problems"


# ------------------------------------------------------------- domain
def test_domain_constants():
    assert FIELDS_PER_WORD == 3
    assert CELLS == 100 and WORDS == 34 and SLOTS == 102
    assert BASE == 2_097_152 and BASE > MAX_FIELD  # fields cannot collide
    assert OFFSET == 1_000_000 and MAX_FIELD == 2_000_000


def test_encode_decode_full_domain_roundtrip():
    # exhaustive over every legal cell value
    for v in range(VALUE_MIN, VALUE_MAX + 1):
        e = encode_value(v)
        assert 0 <= e <= MAX_FIELD
        assert decode_value(e) == v


def test_encode_rejects_out_of_domain():
    for bad in (VALUE_MIN - 1, VALUE_MAX + 1, 10 ** 9, -10 ** 9):
        with pytest.raises(PackingError):
            encode_value(bad)


# ------------------------------------------------------------- pack/unpack
def _boundary_values():
    return [VALUE_MIN, -1, 0, 1, VALUE_MAX, 123456, -987654]


def test_pack_unpack_boundary_combinations():
    vals = _boundary_values()
    for a in vals:
        for b in vals:
            for c in vals:
                word = pack_values([a, b, c])
                assert signed64_safe(word)
                assert unpack_values(word) == [a, b, c]


def test_pack_unpack_random():
    rng = random.Random(20260725)
    for _ in range(20000):
        triple = [rng.randint(VALUE_MIN, VALUE_MAX) for _ in range(3)]
        word = pack_values(triple)
        assert signed64_safe(word)
        assert unpack_values(word) == triple


def test_peel_matches_division_semantics():
    # peel is the machine's single `/ BASE` step: quotient + remainder
    word = pack_values([VALUE_MAX, -1, VALUE_MIN])
    rest, low = peel(word)
    assert low == encode_value(VALUE_MAX)          # field 0 == remainder
    assert rest == unpack_fields(word)[1] + unpack_fields(word)[2] * BASE


def test_short_field_lists_zero_pad_high_fields():
    from littleman.memory_packing_model import pack_fields
    word = pack_fields([encode_value(5)])          # only field 0 set
    fields = unpack_fields(word)
    assert fields[0] == encode_value(5)
    assert fields[1] == 0 and fields[2] == 0


# ------------------------------------------------------------- ordering
def test_encode_is_strictly_monotonic():
    prev = None
    for v in range(VALUE_MIN, VALUE_MAX + 1, 4999):
        e = encode_value(v)
        if prev is not None:
            assert e > prev
        prev = e


def test_field_independence():
    # rewriting one field must not disturb the decoded value of the others
    base_word = pack_values([10, 20, 30])
    w1 = write_field(base_word, 1, -777)
    assert read_field(w1, 0) == 10
    assert read_field(w1, 1) == -777
    assert read_field(w1, 2) == 30


def test_write_field_roundtrip_all_positions():
    rng = random.Random(7)
    for _ in range(3000):
        triple = [rng.randint(VALUE_MIN, VALUE_MAX) for _ in range(3)]
        word = pack_values(triple)
        f = rng.randrange(3)
        nv = rng.randint(VALUE_MIN, VALUE_MAX)
        word2 = write_field(word, f, nv)
        expect = list(triple)
        expect[f] = nv
        assert unpack_values(word2) == expect


# ------------------------------------------------------------- signed-64
def test_word_max_fits_signed64_with_sign_bit_clear():
    assert WORD_MAX == MAX_FIELD * (1 + BASE + BASE * BASE)
    assert WORD_MAX < SIGNED64_MAX
    assert WORD_MAX >> 63 == 0                      # sign bit stays 0
    # the extreme all-max word is the true maximum and is safe
    extreme = pack_values([VALUE_MAX, VALUE_MAX, VALUE_MAX])
    assert extreme == WORD_MAX
    assert signed64_safe(extreme)


def test_no_word_wraps_under_littleman_arithmetic():
    from littleman.sim import wrap64
    for word in (0, ZERO_WORD, WORD_MAX, pack_values([VALUE_MIN, VALUE_MIN, VALUE_MIN])):
        assert wrap64(word) == word                # no signed-64 wrap


# ------------------------------------------------------------- padding
def test_zero_word_reads_as_zero_values():
    assert unpack_values(ZERO_WORD) == [0, 0, 0]


def test_fresh_memory_reads_zero_everywhere():
    mem = PackedMemory()
    assert len(mem.words) == WORDS
    for addr in range(CELLS):
        assert mem.read(addr) == 0


def test_padding_slots_do_not_affect_in_range_cells():
    # cells 99 -> word 33 field 0; fields 1,2 of word 33 are padding
    w, f = cell_to_word_field(CELLS - 1)
    assert (w, f) == (33, 0)
    mem = PackedMemory()
    # corrupt the padding slots of the last word to arbitrary junk
    mem.words[33] = write_field(mem.words[33], 1, VALUE_MAX)
    mem.words[33] = write_field(mem.words[33], 2, VALUE_MIN)
    for addr in range(CELLS):                       # every real cell unaffected
        assert mem.read(addr) == 0
    # addr in range never maps into a padding slot
    for addr in range(CELLS):
        wi, fi = cell_to_word_field(addr)
        assert wi * FIELDS_PER_WORD + fi < CELLS


def test_addr_out_of_range_rejected():
    for bad in (-1, CELLS, 1000):
        with pytest.raises(PackingError):
            cell_to_word_field(bad)


# ---------------------------------------------- functional equivalence
class _PlainMemory:
    def __init__(self):
        self.cells = [0] * CELLS

    def run(self, tokens):
        out, i, n = [], 0, len(tokens)
        while i < n:
            if tokens[i] == 0:
                out.append(self.cells[tokens[i + 1]])
                i += 2
            else:
                self.cells[tokens[i + 1]] = tokens[i + 2]
                i += 3
        return out


def _public_streams():
    spec = json.loads((PROBLEMS / "memory.json").read_text())
    streams = []
    for case in spec["publicTestData"]:
        rounds = case["rounds"] if "rounds" in case else [case]
        toks = []
        for rd in rounds:
            toks.extend(int(x) for x in rd["in"])
        streams.append((case["name"], toks))
    return streams


@pytest.mark.parametrize("name,tokens", _public_streams())
def test_packed_matches_plain_on_public_cases(name, tokens):
    assert PackedMemory().run(tokens) == _PlainMemory().run(tokens)


def test_packed_matches_plain_on_random_streams():
    rng = random.Random(31337)
    for _ in range(200):
        toks = []
        for _ in range(rng.randint(1, 400)):
            addr = rng.randrange(CELLS)
            if rng.random() < 0.5:
                toks += [0, addr]
            else:
                toks += [1, addr, rng.randint(VALUE_MIN, VALUE_MAX)]
        assert PackedMemory().run(toks) == _PlainMemory().run(toks)


# ---------------------------------------------- capacity / projection
def test_ring_capacity_reduction_is_material():
    r = ring_capacity_reduction()
    assert r["items_unpacked"] == 100 and r["items_packed"] == 34
    assert r["item_ratio"] > 2.9                    # ~2.94x fewer items
    assert r["current_serpentine_cells"] == 107     # measured build_memory


def test_score_projection_is_conservative_and_material():
    p = project_score()
    # The per-operation overhead is charged for all 300 assumed operations.
    assert p["assumptions"]["total_decode_overhead_ticks"] == 12_000
    # Conservative estimate remains strictly better than memory_01.
    assert p["projected_score"] < p["current_score"]
    assert p["score_multiplier"] < 0.85
    # sanity: ticks improve, footprint assumed unchanged
    assert p["projected_avg_ticks"] < p["current_avg_ticks"]
    assert p["projected_footprint"] == 2209
