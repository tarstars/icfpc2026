"""Gates for the asymmetric History archive and its compact components."""

from littleman.canvas import Canvas
from littleman.history_archive import (
    MAIN_RADIX,
    TABLE_RADIX,
    build_archive,
    build_dispatcher_room,
    build_splitter_room,
    build_word_room,
    reference_decode,
)
from littleman.sim import Machine


def _output_rig(room: list[str], attach_row: int) -> str:
    canvas = Canvas()
    canvas.put(0, 0, room)
    room_right = len(room[0]) - 1
    output_left = room_right + 4
    canvas.put(attach_row - 1, output_left, ["+-+", "|O|", "+-+"])
    canvas.pipe([(attach_row, room_right + 1), (attach_row, output_left - 1)])
    return canvas.render()


def _splitter_rig(radix: int) -> str:
    room = build_splitter_room(radix)
    canvas = Canvas()
    canvas.put(0, 5, room)
    canvas.put(len(room) - 4, 0, ["+-+", "|I|", "+-+"])
    canvas.pipe([(len(room) - 3, 3), (len(room) - 3, 4)])
    right = 5 + len(room[0]) - 1
    canvas.put(1, right + 3, ["+-+", "|O|", "+-+"])
    canvas.pipe([(2, right + 1), (2, right + 2)])
    return canvas.render()


def _dispatcher_rig() -> str:
    archive = build_archive()
    table = build_word_room(archive.table_words, field=19, rows=14, cyclic=True)
    splitter = build_splitter_room(TABLE_RADIX)
    dispatcher = build_dispatcher_room()
    canvas = Canvas()
    canvas.put(0, 0, table)
    canvas.put(0, 75, splitter)
    canvas.pipe([(7, 72), (7, 74)])

    dispatcher_top, dispatcher_left = 30, 20
    canvas.put(dispatcher_top, dispatcher_left, dispatcher)
    canvas.pipe(
        [
            (16, 79),
            (28, 79),
            (28, dispatcher_left + 44),
            (29, dispatcher_left + 44),
        ]
    )

    canvas.put(20, dispatcher_left + 100, ["+-+", "|I|", "+-+"])
    canvas.pipe(
        [
            (23, dispatcher_left + 101),
            (29, dispatcher_left + 101),
        ]
    )
    output_top = dispatcher_top + len(dispatcher) + 2
    canvas.put(output_top, dispatcher_left + 110, ["+-+", "|O|", "+-+"])
    canvas.pipe(
        [
            (dispatcher_top + len(dispatcher), dispatcher_left + 111),
            (output_top - 1, dispatcher_left + 111),
        ]
    )
    return canvas.render()


def test_archive_round_trip_and_geometry_thresholds():
    archive = build_archive()
    assert len(archive.entries) == 127
    assert len(archive.main_codes) == 1755
    assert len(archive.main_words) == 197
    assert len(archive.table_codes) == 340
    assert len(archive.table_words) == 38
    assert all(0 <= word < 1 << 63 for word in archive.main_words)
    assert all(0 <= word < 1 << 63 for word in archive.table_words)
    assert all(int(str(word)[::-1]) < 1 << 63 for word in archive.main_words)
    assert all(int(str(word)[::-1]) < 1 << 63 for word in archive.table_words)
    assert reference_decode(archive) == archive.text


def test_main_word_room_is_68_by_71_and_emits_words_then_padding():
    archive = build_archive()
    room = build_word_room(archive.main_words, field=19, rows=66, cyclic=False)
    assert (len(room), len(room[0])) == (68, 71)
    result = Machine.parse(_output_rig(room, 34)).run(max_ticks=100_000)
    assert result.error is None
    assert result.output == [*archive.main_words, 0]


def test_table_word_room_is_16_by_72_and_repeats():
    archive = build_archive()
    room = build_word_room(archive.table_words, field=19, rows=14, cyclic=True)
    assert (len(room), len(room[0])) == (16, 72)
    result = Machine.parse(_output_rig(room, 7)).run(max_ticks=50_000)
    expected = [*archive.table_words, 0, 0, 0, 0]
    assert result.error is None
    assert result.output[: 2 * len(expected)] == expected * 2


def test_splitter_rooms_emit_little_endian_digits_and_skip_zero():
    for radix, words in (
        (MAIN_RADIX, [1 + 2 * MAIN_RADIX + 3 * MAIN_RADIX**2, 0]),
        (TABLE_RADIX, [4 + 5 * TABLE_RADIX + 6 * TABLE_RADIX**2, 0]),
    ):
        result = Machine.parse(_splitter_rig(radix)).run(
            inputs=words,
            max_ticks=10_000,
        )
        assert result.error is None
        assert result.output == [1, 2, 3] if radix == MAIN_RADIX else [4, 5, 6]


def test_roomy_dispatcher_serializes_complete_expansions():
    archive = build_archive()
    requested = [1, 2, 71, 72, 127]
    result = Machine.parse(_dispatcher_rig()).run(
        inputs=requested,
        max_ticks=2_000_000,
    )
    assert result.error is None
    assert "".join(map(chr, result.output)) == "".join(
        archive.entries[index - 1] for index in requested
    )
