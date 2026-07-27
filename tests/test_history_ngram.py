"""Round-trip and cell-budget gates for the history_ngram schemes.

Mirrors test_history_pack.py's gates: every scheme must round-trip the
2,810-character history text exactly, and every packed word must be a
legal signed-64 literal, since the machine emits specific bytes and one
wrong character scores zero.
"""

import pytest

from littleman import history_ngram as ng
from littleman import history_pack as hp

BASELINE_TOTAL = 4767  # history_pack.build(): 4,242 data + 525 table


def test_baseline_is_what_the_brief_says():
    enc = hp.build()
    assert enc["data_cells"] + enc["table_cells"] == BASELINE_TOTAL


# ---------------------------------------------------------------------------
# Scheme A: escape the rare tail
# ---------------------------------------------------------------------------

def test_rare_characters_match_the_measured_tail():
    text = hp.expected_text()
    rare = ng.rare_characters(text)
    assert rare == ["'", "3", "4", "5", "7", "8", "?", "Q", "X", "Z", "z"]
    # the brief says 31 occurrences; a direct count gives 25 - use the
    # measured value rather than re-deriving it wrong a second time.
    assert sum(text.count(ch) for ch in rare) == 25


def test_escape_unescape_round_trips_generically():
    text = hp.expected_text()
    rare = ng.rare_characters(text)
    transformed, standins = ng.escape_text(text, rare)
    assert len(transformed) == len(text) + 25  # +1 symbol per rare occurrence
    assert ng.unescape_text(transformed, rare, standins) == text


def test_scheme_a_round_trips_at_default_count():
    enc = ng.build_scheme_a()
    assert ng.decode_scheme_a(enc) == enc["text"]


def test_scheme_a_round_trips_at_measured_best_count():
    text = hp.expected_text()
    enc = ng.build_scheme_a(text, count=38)
    assert ng.decode_scheme_a(enc) == text


def test_scheme_a_words_are_legal_literals():
    enc = ng.build_scheme_a()
    for word in enc["words"] + enc["table_words"] + enc["rare_words"]:
        assert 0 <= word <= hp.LIMIT


def test_scheme_a_rare_table_is_not_degenerate():
    """Regression guard for a real bug caught during measurement: packing
    the rare list against an alphabet derived from itself is a no-op
    (always the identity sequence 0..10, since `rare` is already sorted
    and unique), so it must be packed against the master 71-character
    alphabet instead, or the table stores zero information."""
    enc = ng.build_scheme_a()
    assert enc["rare_radix"] == len(enc["master_alphabet"]) == 71


def test_scheme_a_best_found_count_is_a_net_negative_vs_baseline():
    """Honest negative result: escaping the rare tail does not pay for
    itself once the (correctly, non-degenerately costed) rare table and
    the +25 escape symbols are counted."""
    text = hp.expected_text()
    enc = ng.build_scheme_a(text, count=38)
    assert enc["data_cells"] == 4380
    assert enc["table_cells"] == 402
    assert enc["total_cells"] == 4782
    assert enc["total_cells"] > BASELINE_TOTAL


# ---------------------------------------------------------------------------
# Scheme C: order-1 with grouped contexts
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("k", [2, 3, 4, 6, 8])
def test_scheme_c_round_trips_for_every_class_count(k):
    enc = ng.build_scheme_c(k=k)
    assert ng.decode_scheme_c(enc) == enc["text"]


@pytest.mark.parametrize("k", [2, 3, 4, 6, 8])
def test_scheme_c_words_are_legal_literals(k):
    enc = ng.build_scheme_c(k=k)
    for word in enc["words"]:
        assert 0 <= word <= hp.LIMIT
    for cinfo in enc["contexts"].values():
        for word in cinfo["table_words"]:
            assert 0 <= word <= hp.LIMIT


@pytest.mark.parametrize("k", [2, 3, 4, 6, 8])
def test_scheme_c_every_character_has_a_context_class(k):
    """The 8 fine buckets, merged per GROUPING[k], must exhaust the
    71-character alphabet with no gaps and no overlaps."""
    text = hp.expected_text()
    class_of = ng.make_class_of(k)
    for ch in sorted(set(text)):
        assert class_of(ch) in set(ng.GROUPING[k].values())


def test_scheme_c_k4_is_the_measured_optimum_and_beats_baseline():
    results = {k: ng.build_scheme_c(k=k)["total_cells"]
               for k in (2, 3, 4, 6, 8)}
    assert results[4] == min(results.values())
    assert results[4] == 4728
    assert results[4] < BASELINE_TOTAL


def test_scheme_c_uncapped_dictionaries_are_much_worse():
    """Documents why the per-context token count is tuned at all: letting
    every context fill its full slot budget loses badly once each
    context's own table is counted."""
    enc_capped = ng.build_scheme_c(k=6)
    enc_uncapped = ng.build_scheme_c(k=6, caps={c: 100 for c in "ABCDEF"})
    assert enc_capped["total_cells"] < enc_uncapped["total_cells"]
    assert ng.decode_scheme_c(enc_uncapped) == enc_uncapped["text"]
