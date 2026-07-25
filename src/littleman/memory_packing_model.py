"""Reference model for three-values-per-word packing of the Memory ring.

Priority-4 feasibility study from docs/tcp-derived-optimization-actions.md.
This is a STANDALONE arithmetic model, not a machine generator. It proves
that three Memory cell values can be packed into one signed-64-bit
littleman word, decoded/updated with the ops the machine has (`/` gives
quotient in A and remainder in B in one step), and that doing so shrinks
the circulating ring from 100 values to 34 words.

Memory value domain (from data/small/problems/memory.json):
  - 100 cells, addr in [0, 100); every cell starts at value 0.
  - cell value v in [-1_000_000, 1_000_000]  (2_000_001 distinct values).

Encoding:
  - Offset a signed value into a non-negative field:
        e = v + OFFSET,   e in [0, 2_000_000].
  - Pack three fields little-endian in base BASE = 2**21:
        word = e0 + e1*BASE + e2*BASE**2.
    BASE = 2**21 = 2_097_152 > 2_000_000, so fields never collide, and
    BASE being a power of two lets the machine peel a field with a single
    `/ BASE` (quotient = the remaining fields, remainder = this field).

Signed-64 safety:
  - Max word = MAX_FIELD*(1 + BASE + BASE**2) = 8_796_097_216_514_000_000,
    which is < 2**63-1 = 9_223_372_036_854_775_807. The sign bit stays 0,
    so words are always non-negative signed-64 integers and no littleman
    arithmetic wraps (verified against littleman.sim.wrap64).

Alternative base 2_000_001 (exact radix) also fits (2_000_001**3 - 1 =
8.0e18 < 2**63) and is documented for completeness, but base 2**21 is the
primary choice for the shift/divide friendliness above.
"""

from __future__ import annotations

from math import ceil

from .sim import wrap64

# ------------------------------------------------------------- domain
VALUE_MIN = -1_000_000
VALUE_MAX = 1_000_000
OFFSET = 1_000_000
MAX_FIELD = VALUE_MAX + OFFSET  # 2_000_000, the largest encoded field

CELLS = 100
FIELDS_PER_WORD = 3
WORDS = ceil(CELLS / FIELDS_PER_WORD)  # 34
SLOTS = WORDS * FIELDS_PER_WORD        # 102 (last word has 2 padding slots)

BASE = 1 << 21                         # 2_097_152
WORD_MAX = MAX_FIELD * (1 + BASE + BASE * BASE)
SIGNED64_MAX = (1 << 63) - 1

ALT_BASE = 2_000_001                   # exact radix alternative (also fits)

# a fully-zeroed memory: every cell value 0 -> encoded field OFFSET
ZERO_WORD = OFFSET * (1 + BASE + BASE * BASE)


class PackingError(ValueError):
    pass


# ----------------------------------------------------- value <-> field
def encode_value(v: int) -> int:
    """Signed cell value -> non-negative field in [0, MAX_FIELD]."""
    if not (VALUE_MIN <= v <= VALUE_MAX):
        raise PackingError(f"value {v} outside [{VALUE_MIN}, {VALUE_MAX}]")
    return v + OFFSET


def decode_value(e: int) -> int:
    """Field -> signed cell value."""
    if not (0 <= e <= MAX_FIELD):
        raise PackingError(f"field {e} outside [0, {MAX_FIELD}]")
    return e - OFFSET


# ----------------------------------------------------- pack / unpack
def pack_fields(fields: list[int]) -> int:
    """Pack up to FIELDS_PER_WORD encoded fields little-endian, base BASE."""
    if len(fields) > FIELDS_PER_WORD:
        raise PackingError(f"at most {FIELDS_PER_WORD} fields per word")
    word = 0
    for i, e in enumerate(fields):
        if not (0 <= e < BASE):
            raise PackingError(f"field {e} not in [0, {BASE})")
        word += e * (BASE ** i)
    return word


def unpack_fields(word: int) -> list[int]:
    """Inverse of pack_fields; always returns FIELDS_PER_WORD fields.

    Mirrors the machine's peel: repeated `/ BASE` (quotient + remainder).
    """
    if not (0 <= word <= WORD_MAX):
        raise PackingError(f"word {word} outside [0, {WORD_MAX}]")
    fields = []
    rest = word
    for _ in range(FIELDS_PER_WORD):
        rest, field = divmod(rest, BASE)  # littleman `/`: A=quotient, B=remainder
        fields.append(field)
    return fields


def pack_values(values: list[int]) -> int:
    """Pack up to three SIGNED cell values into one word."""
    return pack_fields([encode_value(v) for v in values])


def unpack_values(word: int) -> list[int]:
    """One word -> three signed cell values."""
    return [decode_value(e) for e in unpack_fields(word)]


def peel(word: int) -> tuple[int, int]:
    """One machine `/ BASE` step: return (remaining_word, low_field)."""
    rest, low = divmod(word, BASE)
    return rest, low


# ------------------------------------------------- field read / write
def read_field(word: int, field_index: int) -> int:
    """Signed value stored in field 0/1/2 of a word."""
    if not (0 <= field_index < FIELDS_PER_WORD):
        raise PackingError(f"field index {field_index} out of range")
    return decode_value(unpack_fields(word)[field_index])


def write_field(word: int, field_index: int, value: int) -> int:
    """Return the word with field 0/1/2 replaced by a signed value."""
    if not (0 <= field_index < FIELDS_PER_WORD):
        raise PackingError(f"field index {field_index} out of range")
    fields = unpack_fields(word)
    fields[field_index] = encode_value(value)
    return pack_fields(fields)


# ---------------------------------------------------- addressing
def cell_to_word_field(addr: int) -> tuple[int, int]:
    """Cell addr -> (word index in [0, WORDS), field index in [0, 3))."""
    if not (0 <= addr < CELLS):
        raise PackingError(f"addr {addr} outside [0, {CELLS})")
    return divmod(addr, FIELDS_PER_WORD)


def signed64_safe(word: int) -> bool:
    """True iff the word is a non-negative signed-64 value that does not
    wrap under littleman arithmetic."""
    return 0 <= word <= SIGNED64_MAX and wrap64(word) == word


# ------------------------------------------------- packed memory model
class PackedMemory:
    """Functional reference: a 100-cell memory backed by 34 packed words.

    Proves that packed storage reproduces exact Memory semantics over an
    operation stream (READ = [0, addr]; WRITE = [1, addr, value]).
    """

    def __init__(self) -> None:
        # all cells start at value 0; every slot (incl. padding) = ZERO_WORD
        self.words = [ZERO_WORD] * WORDS

    def read(self, addr: int) -> int:
        w, f = cell_to_word_field(addr)
        return read_field(self.words[w], f)

    def write(self, addr: int, value: int) -> None:
        w, f = cell_to_word_field(addr)
        self.words[w] = write_field(self.words[w], f, value)

    def run(self, tokens: list[int]) -> list[int]:
        """Execute a flat op-token stream, returning the READ outputs."""
        out: list[int] = []
        i = 0
        n = len(tokens)
        while i < n:
            op = tokens[i]
            if op == 0:  # READ addr
                out.append(self.read(tokens[i + 1]))
                i += 2
            elif op == 1:  # WRITE addr value
                self.write(tokens[i + 1], tokens[i + 2])
                i += 3
            else:
                raise PackingError(f"bad op {op}")
        return out


# ------------------------------------------------- capacity / projection
RING_VALUES_UNPACKED = CELLS   # 100 live values must circulate today
RING_WORDS_PACKED = WORDS      # 34 words after packing
CURRENT_RING_CELLS = 107       # measured serpentine length of build_memory


def ring_capacity_reduction() -> dict:
    """Ring circulating-item reduction from packing (definite, exact)."""
    return {
        "items_unpacked": RING_VALUES_UNPACKED,
        "items_packed": RING_WORDS_PACKED,
        "item_ratio": RING_VALUES_UNPACKED / RING_WORDS_PACKED,
        "current_serpentine_cells": CURRENT_RING_CELLS,
        "packed_serpentine_cells_estimate": RING_WORDS_PACKED + 7,  # +slack
    }


def project_score(
    *,
    current_footprint: int = 2209,      # memory_01, measured 46x47
    current_avg_ticks: float = 41_363.625,  # memory_01 server, from report
    current_score: float = 91_372_247.625,  # memory_01 server, from report
    rotation_fraction: float = 0.7,     # conservative: rotation ~70% of ticks
    per_op_decode_overhead_ticks: float = 40.0,  # added extract/insert cost
    approx_ops: int = 300,              # conservative op-count for the tick pool
    footprint_after: int | None = None,  # None = conservatively unchanged
) -> dict:
    """Conservative score projection for a packed Memory machine.

    Ticks: only the ring-rotation component scales, by items_packed /
    items_unpacked (34/100). The non-rotation remainder is kept as-is and a
    fixed per-op decode/encode overhead is ADDED. Footprint is assumed
    unchanged unless a prototype proves the shorter ring shrinks the
    binding dimension (P2's 38-wide parser currently binds width). All
    inputs are the measured memory_01 server metrics from
    reports/2026-07-24-memory-compaction.md; this remains an estimate
    until a machine is built and judged.
    """
    ratio = RING_WORDS_PACKED / RING_VALUES_UNPACKED  # 0.34
    rot = current_avg_ticks * rotation_fraction
    fixed = current_avg_ticks * (1.0 - rotation_fraction)
    overhead = per_op_decode_overhead_ticks * approx_ops
    # ``current_avg_ticks`` is per test case, so per-operation overhead must
    # be multiplied by the assumed average operation count for that case.
    projected_ticks = rot * ratio + fixed + overhead
    fp = current_footprint if footprint_after is None else footprint_after
    projected_score = fp * projected_ticks
    return {
        "current_footprint": current_footprint,
        "current_avg_ticks": current_avg_ticks,
        "current_score": current_score,
        "projected_footprint": fp,
        "projected_avg_ticks": projected_ticks,
        "projected_score": projected_score,
        "tick_multiplier": projected_ticks / current_avg_ticks,
        "score_multiplier": projected_score / current_score,
        "assumptions": {
            "rotation_fraction": rotation_fraction,
            "item_ratio": ratio,
            "per_op_decode_overhead_ticks": per_op_decode_overhead_ticks,
            "approx_ops": approx_ops,
            "total_decode_overhead_ticks": overhead,
            "footprint_unchanged": footprint_after is None,
        },
    }
