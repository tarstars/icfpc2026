"""Gates for the asymmetric history-lesson encoder.

The encoder may be arbitrarily expensive (it runs here, in Python); the
decoder must stay small in CELLS, because history-lesson is
footprint-scored and ticks are free. These tests pin the two properties a
machine builder depends on: the round trip is exact, and the cell budget
is what the sweep claims.
"""

import math

import pytest

from littleman import history_pack as hp


def test_round_trip_is_exact():
    enc = hp.build()
    ids = hp.unpack(enc["words"], enc["radix"], len(enc["ids"]))
    assert ids == enc["ids"]
    assert hp.untokenise(ids, enc["alphabet"], enc["tokens"]) == enc["text"]


def test_token_table_round_trips_too():
    """The decoder reads token text out of the packed table, so it must
    survive the same divmod loop as the data."""
    enc = hp.build()
    index = {ch: i for i, ch in enumerate(enc["table_alpha"])}
    ids = hp.unpack(enc["table_words"], enc["table_radix"],
                    len(enc["table_text"]))
    assert ids == [index[ch] for ch in enc["table_text"]]


def test_every_word_is_a_legal_literal():
    """A packed word is written as a decimal literal, so it must fit the
    signed-64 range the machine can load."""
    enc = hp.build()
    for word in enc["words"] + enc["table_words"]:
        assert 0 <= word <= hp.LIMIT


def test_beats_the_live_encoding_and_hits_its_budget():
    enc = hp.build()
    total = enc["data_cells"] + enc["table_cells"]
    assert total < 5460, "must beat the live 3-token encoding"
    # the sweep's claim, pinned so a regression is visible
    assert total <= 4800
    bits = len(enc["ids"]) * math.log2(enc["radix"]) / len(enc["text"])
    assert bits < 5.0, "should beat order-0 entropy (5.05) via the dictionary"


@pytest.mark.parametrize("count", [16, 24, 48, 56])
def test_round_trip_holds_at_other_token_counts(count):
    text = hp.expected_text()
    enc = hp.build(text, count)
    ids = hp.unpack(enc["words"], enc["radix"], len(enc["ids"]))
    assert hp.untokenise(ids, enc["alphabet"], enc["tokens"]) == text


def test_fifty_six_is_the_measured_optimum():
    """Beyond 56 the radix costs a symbol per word (floor(63/log2 radix)
    drops from 9 to 8) and the table grows faster than the data shrinks."""
    text = hp.expected_text()
    totals = {}
    for count in (48, 56, 64):
        enc = hp.build(text, count)
        totals[count] = enc["data_cells"] + enc["table_cells"]
    assert totals[56] < totals[48]
    assert totals[56] < totals[64]
    assert hp.symbols_per_word(127) == 9
    assert hp.symbols_per_word(135) == 8
