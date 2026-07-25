"""Evidence for the History Lesson lightning sprint.

These tests pin the geometric argument that 89x89 (footprint 7,921) is the
floor for the current radix-92 encoding, and pin the compression numbers
that say what a dictionary encoding would buy instead.
"""

from __future__ import annotations

import hashlib

from littleman import history, history_lightning as HL


def digits() -> list[int]:
    return [value - HL.ASCII_SHIFT for value in HL.expected_output()]


def test_expected_blob_is_the_known_2810_byte_answer():
    values = HL.expected_output()
    blob = bytes(values)
    assert len(blob) == 2810
    assert (
        hashlib.sha256(blob).hexdigest()
        == "9d4ffa9ef2f67ad1cd4a915273181a7c2c578d33a0e8ef211a2c403e31b635b2"
    )
    assert blob.startswith(b"1996: Philadelphia, PA, USA ")
    assert blob.endswith(b"2026: Indianapolis, IN, USA")


def test_geometry_formulas_reproduce_the_live_artifact():
    words = history.pack_history_words_fixed(HL.expected_output())
    assert len(words) == 308
    assert HL.room_width(4, 18) == 89
    assert HL.room_height(len(words), 4) == 89
    text = history.build_history()
    lines = text.rstrip("\n").split("\n")
    assert max(len(line) for line in lines) == 89
    assert len(lines) == 89


def test_packing_round_trips_to_the_exact_blob():
    values = digits()
    words = history.pack_history_words_fixed(HL.expected_output())
    assert HL.unpack_fixed(words) == values


def test_no_fixed_slot_layout_beats_89():
    best = HL.layout_sweep(digits())[0]
    assert best.max_dimension == 89
    assert (best.slots, best.field_width) == (4, 18)
    assert best.footprint == 7921


def test_saving_the_extra_data_column_creates_a_load_error():
    conflicts = HL.overlap_conflict_columns(4, 18)
    assert conflicts, "overlapping east/westbound slot spans must clash"


def test_dictionary_compression_round_trips_and_fits_the_free_codes():
    values = HL.expected_output()
    budget = HL.free_code_count(values)
    assert budget == 20
    compression = HL.macro_compress(HL.expected_text(), budget)
    assert len(compression.macros) == budget
    assert max(compression.tokens) <= 91
    assert HL.expand_tokens(compression) == HL.expected_text()
    assert len(compression.tokens) <= 2100


def test_compressed_stream_projects_under_7921():
    compression = HL.macro_compress(HL.expected_text(), 20)
    band, point = HL.projected_footprints(compression, band_rows=(17,))[0]
    assert point.max_dimension <= 85
    assert point.footprint < 7921
