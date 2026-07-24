"""Generated packed-text solution for the History Lesson problem."""

from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple

from .canvas import Canvas

REPO = Path(__file__).resolve().parent.parent.parent
PROBLEM_PATH = REPO / "data" / "small" / "problems" / "history-lesson.json"

RADIX = 92
ASCII_SHIFT = 31
DATA_INNER_WIDTH = 87
DATA_ROW_CAPACITY = DATA_INNER_WIDTH - 2
FIXED_FIELD_WIDTH = 18
FIXED_SLOT_WIDTH = FIXED_FIELD_WIDTH + 3
FIXED_DATA_INNER_WIDTH = 4 * FIXED_SLOT_WIDTH + 3
DATA_ROW_OFFSETS = [
    5,
    4,
    2,
    0,
    2,
    7,
    14,
    5,
    0,
    2,
    0,
    1,
    2,
    0,
    1,
    4,
    0,
    0,
    0,
    0,
    1,
    0,
    1,
    0,
    3,
    4,
    0,
    6,
    6,
    0,
    2,
    1,
    2,
    0,
    1,
    0,
    0,
    0,
    3,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    1,
    3,
    2,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    2,
    2,
    0,
    1,
    0,
    0,
    0,
    1,
    0,
    4,
    4,
    1,
    2,
    0,
    0,
    0,
]


class _PackedWord(NamedTuple):
    end: int
    value: int
    source_cells: int


def _put_text(
    cells: dict[tuple[int, int], str],
    row: int,
    col: int,
    text: str,
) -> None:
    for offset, value in enumerate(text):
        cells[(row, col + offset)] = value


def _room(height: int, width: int, cells: dict[tuple[int, int], str]) -> list[str]:
    rows = [
        list("+" + "-" * (width - 2) + "+"),
        *[list("|" + " " * (width - 2) + "|") for _ in range(height - 2)],
        list("+" + "-" * (width - 2) + "+"),
    ]
    for (row, col), value in cells.items():
        rows[row][col] = value
    return ["".join(row) for row in rows]


def _render_cropped(canvas: Canvas) -> str:
    min_row = min(row for row, _ in canvas.cells)
    max_row = max(row for row, _ in canvas.cells)
    min_col = min(col for _, col in canvas.cells)
    max_col = max(col for _, col in canvas.cells)
    lines = []
    for row in range(min_row, max_row + 1):
        line = "".join(
            canvas.cells.get((row, col), " ") for col in range(min_col, max_col + 1)
        )
        lines.append(line.rstrip())
    return "\n".join(lines) + "\n"


def history_output() -> list[int]:
    """Load the canonical byte sequence from the archived problem."""

    problem = json.loads(PROBLEM_PATH.read_text())
    values = problem["publicTestData"][0]["rounds"][0]["out"]
    return [int(value) for value in values]


def _word_options(values: list[int], start: int) -> list[_PackedWord]:
    options = []
    value = 0
    multiplier = 1
    for length in range(1, 13):
        end = start + length
        if end > len(values):
            break
        digit = values[end - 1] - ASCII_SHIFT
        if not 0 < digit < RADIX:
            raise ValueError(f"unsupported History Lesson byte: {values[end - 1]}")
        value += digit * multiplier
        multiplier *= RADIX
        if value >= 1 << 63:
            break
        if int(str(value)[::-1]) >= 1 << 63:
            continue
        options.append(
            _PackedWord(
                end=end,
                value=value,
                source_cells=len(str(value)) + 3,
            )
        )
    return options


def pack_history_words(values: list[int]) -> list[list[int]]:
    """Pack bytes into radix words jointly optimized for serpentine rows."""

    # Each state is keyed by occupied data cells in the current row. Its value
    # is (rows, source_cells, previous_index, previous_used, packed_value).
    states: list[dict[int, tuple[int, int, int, int, int]]] = [
        {} for _ in range(len(values) + 1)
    ]
    states[0][0] = (1, 0, -1, -1, 0)
    options = [_word_options(values, index) for index in range(len(values))]

    for index, by_used in enumerate(states[:-1]):
        for used, record in by_used.items():
            rows, source_cells = record[:2]
            for option in options[index]:
                if used + option.source_cells <= DATA_ROW_CAPACITY:
                    next_rows = rows
                    next_used = used + option.source_cells
                else:
                    next_rows = rows + 1
                    next_used = option.source_cells
                candidate = (
                    next_rows,
                    source_cells + option.source_cells,
                    index,
                    used,
                    option.value,
                )
                previous = states[option.end].get(next_used)
                if previous is None or candidate[:2] < previous[:2]:
                    states[option.end][next_used] = candidate

    final_used, final = min(
        states[-1].items(),
        key=lambda item: (item[1][0], item[1][1], item[0]),
    )
    words = []
    index = len(values)
    used = final_used
    while index:
        record = states[index][used]
        _, _, previous_index, previous_used, value = record
        words.append(value)
        index = previous_index
        used = previous_used
    words.reverse()

    rows: list[list[int]] = [[]]
    occupied = 0
    for value in words:
        cells = len(str(value)) + 3
        if occupied + cells > DATA_ROW_CAPACITY:
            rows.append([])
            occupied = 0
        rows[-1].append(value)
        occupied += cells
    assert len(rows) == final[0]
    return rows


def unpack_history_words(rows: list[list[int]]) -> list[int]:
    """Reference decoder for tests and manifest generation."""

    result = []
    for value in (word for row in rows for word in row):
        while value:
            value, digit = divmod(value, RADIX)
            result.append(digit + ASCII_SHIFT)
    return result


def pack_history_words_fixed(values: list[int]) -> list[int]:
    """Minimize the number of words subject to an 18-decimal-digit field."""

    # Each state is (word_count, decimal_digits, previous_index, value).
    states: list[tuple[int, int, int, int] | None] = [None] * (len(values) + 1)
    states[0] = (0, 0, -1, 0)
    for index in range(len(values)):
        state = states[index]
        if state is None:
            continue
        value = 0
        multiplier = 1
        for length in range(1, 13):
            end = index + length
            if end > len(values):
                break
            digit = values[end - 1] - ASCII_SHIFT
            value += digit * multiplier
            multiplier *= RADIX
            if value >= 10**FIXED_FIELD_WIDTH:
                break
            candidate = (
                state[0] + 1,
                state[1] + len(str(value)),
                index,
                value,
            )
            previous = states[end]
            if previous is None or candidate[:2] < previous[:2]:
                states[end] = candidate

    words = []
    index = len(values)
    while index:
        state = states[index]
        if state is None:
            raise ValueError("History Lesson fixed-word packing failed")
        words.append(state[3])
        index = state[2]
    words.reverse()
    return words


def build_history_fixed_data_room(words: list[int]) -> list[str]:
    """Build a server-safe data room with vertically aligned literal pairs."""

    if len(words) % 4:
        raise ValueError("fixed History Lesson layout requires four words per row")
    word_rows = [words[index : index + 4] for index in range(0, len(words), 4)]
    width = FIXED_DATA_INNER_WIDTH + 2
    room = [
        list("+" + "-" * (width - 2) + "+"),
        *[list("|" + " " * (width - 2) + "|") for _ in word_rows],
        list("+" + "-" * (width - 2) + "+"),
    ]
    starts = [3 + slot * FIXED_SLOT_WIDTH for slot in range(4)]

    for row_index, row_words in enumerate(word_rows, start=1):
        eastbound = row_index % 2 == 1
        room[row_index][1] = (
            ("@" if row_index == 1 else ">")
            if eastbound
            else ("H" if row_index == len(word_rows) else "v")
        )
        room[row_index][FIXED_DATA_INNER_WIDTH] = (
            ("H" if row_index == len(word_rows) else "v") if eastbound else "<"
        )

        ordered = row_words if eastbound else list(reversed(row_words))
        for slot, value in enumerate(ordered):
            start = starts[slot]
            end = start + FIXED_FIELD_WIDTH + 1
            room[row_index][start] = "`"
            room[row_index][end] = "`"
            digits = str(value)
            if eastbound:
                field = digits.rjust(FIXED_FIELD_WIDTH)
                room[row_index][start + 1 : end] = field
                room[row_index][end + 1] = "s"
            else:
                position = end - 1
                for character in digits:
                    room[row_index][position] = character
                    position -= 1
                room[row_index][start - 1] = "s"
    return ["".join(row) for row in room]


def build_history_data_room(rows: list[list[int]]) -> list[str]:
    """Build the serpentine numeric-literal producer."""

    width = DATA_INNER_WIDTH + 2
    room = [
        list("+" + "-" * (width - 2) + "+"),
        # Dots prevent unrelated horizontal literals on different rows from
        # accidentally pairing into enormous vertical literals.
        *[list("|" + "." * (width - 2) + "|") for _ in rows],
        list("+" + "-" * (width - 2) + "+"),
    ]

    if len(rows) != len(DATA_ROW_OFFSETS):
        raise ValueError("History Lesson row packing changed; recompute offsets")

    for row_index, words in enumerate(rows, start=1):
        eastbound = row_index % 2 == 1
        occupied = sum(len(str(value)) + 3 for value in words)
        offset = DATA_ROW_OFFSETS[row_index - 1]
        if offset > DATA_ROW_CAPACITY - occupied:
            raise ValueError("History Lesson data-row offset exceeds padding")
        if eastbound:
            room[row_index][1] = "@" if row_index == 1 else ">"
            position = 2 + offset
            for value in words:
                token = f"`{value}`s"
                for character in token:
                    room[row_index][position] = character
                    position += 1
            room[row_index][DATA_INNER_WIDTH] = "H" if row_index == len(rows) else "v"
        else:
            room[row_index][DATA_INNER_WIDTH] = "<"
            position = DATA_INNER_WIDTH - 1 - offset
            for value in words:
                digits = str(value)
                room[row_index][position] = "`"
                position -= 1
                for character in digits:
                    room[row_index][position] = character
                    position -= 1
                room[row_index][position] = "`"
                position -= 1
                room[row_index][position] = "s"
                position -= 1
            room[row_index][1] = "H" if row_index == len(rows) else "v"
    return ["".join(row) for row in room]


def build_history_decoder_room() -> list[str]:
    """Divide packed words, forwarding quotients and character codes."""

    cells: dict[tuple[int, int], str] = {
        # Initialize divisor B=92 and enter the receive loop.
        (1, 2): "@",
        (1, 7): "M",
        (1, 8): "v",
        (2, 8): "<",
        (2, 4): "v",
        (3, 4): ">",
        (3, 8): "R",
        (3, 9): "X",
        # A positive word: divide, send quotient left, then character right.
        (4, 9): "/",
        (5, 9): "<",
        (5, 2): "s",
        (5, 1): "v",
        (6, 1): ">",
        (6, 9): "W",
        (6, 22): "s",
        (6, 24): "v",
        # A zero quotient, or a completed character, resets B and loops.
        (3, 24): "v",
        (7, 24): "<",
        (7, 16): "M",
        (7, 4): "^",
    }
    _put_text(cells, 1, 3, "`92`")
    # Walked westbound, this spelling loads 92 rather than 29.
    _put_text(cells, 7, 17, "`29`")
    return _room(9, 26, cells)


def build_history_compact_decoder_room() -> list[str]:
    """Return the decoder with its reset track folded into row two."""

    cells: dict[tuple[int, int], str] = {
        (1, 2): "@",
        (1, 7): "M",
        (1, 8): "v",
        (2, 8): "<",
        (2, 4): "v",
        (2, 16): "M",
        (2, 24): "<",
        (3, 4): ">",
        (3, 8): "R",
        (3, 9): "X",
        (3, 24): "^",
        (4, 9): "/",
        (5, 9): "<",
        (5, 2): "s",
        (5, 1): "v",
        (6, 1): ">",
        (6, 9): "W",
        (6, 22): "s",
        (6, 24): "^",
    }
    _put_text(cells, 1, 3, "`92`")
    _put_text(cells, 2, 17, "`29`")
    return _room(8, 26, cells)


def build_history_relay_room() -> list[str]:
    """Echo decoder quotients back to its higher-priority input."""

    return _room(
        6,
        10,
        {
            (1, 1): "@",
            (1, 2): ">",
            (1, 3): "r",
            (1, 4): "s",
            (1, 7): "v",
            (4, 7): "<",
            (4, 2): "^",
        },
    )


def build_history_mapper_room() -> list[str]:
    """Add the ASCII shift to each radix digit and emit it."""

    cells: dict[tuple[int, int], str] = {
        (1, 2): "@",
        (1, 7): "M",
        (1, 8): "v",
        (2, 8): "<",
        (2, 2): "v",
        (3, 2): ">",
        (3, 4): "r",
        (3, 5): "+",
        (3, 6): "s",
        (3, 10): "v",
        (4, 10): "<",
        (4, 2): "^",
    }
    _put_text(cells, 1, 3, "`31`")
    return _room(6, 14, cells)


def build_history_unsafe() -> str:
    """Reproduce the first candidate rejected by the server literal parser."""

    rows = pack_history_words(history_output())
    canvas = Canvas()

    relay_top, relay_left = 5, 0
    decoder_top, decoder_left = 5, 13
    mapper_top, mapper_left = 8, 42
    data_top, data_left = 16, 0

    canvas.put(relay_top, relay_left, build_history_relay_room())
    canvas.put(decoder_top, decoder_left, build_history_decoder_room())
    canvas.put(mapper_top, mapper_left, build_history_mapper_room())
    canvas.put(data_top, data_left, build_history_data_room(rows))

    # Decoder quotient -> relay.
    canvas.pipe(
        [
            (decoder_top + 5, decoder_left - 1),
            (decoder_top + 5, decoder_left - 2),
            (relay_top + 4, decoder_left - 2),
            (relay_top + 4, relay_left + 10),
        ]
    )

    # Relay -> decoder feedback. It arrives earlier in reading order than the
    # data pipe, so R always drains the current packed word before the next.
    canvas.pipe(
        [
            (relay_top + 6, relay_left + 5),
            (data_top - 1, relay_left + 5),
            (data_top - 1, decoder_left + 5),
            (decoder_top + 9, decoder_left + 5),
        ]
    )

    # Packed data -> decoder.
    canvas.pipe(
        [
            (data_top - 1, decoder_left + 17),
            (decoder_top + 9, decoder_left + 17),
        ]
    )

    # Decoder character code -> ASCII mapper.
    canvas.pipe(
        [
            (decoder_top + 6, decoder_left + 26),
            (mapper_top + 3, mapper_left - 1),
        ]
    )

    # Mapper -> output.
    output_top, output_left = 10, 62
    canvas.put(output_top, output_left, ["+-+", "|O|", "+-+"])
    canvas.pipe(
        [
            (mapper_top + 3, mapper_left + 14),
            (output_top + 1, output_left - 1),
        ]
    )

    return _render_cropped(canvas)


def build_history() -> str:
    """Build the server-safe fixed-slot History Lesson program."""

    words = pack_history_words_fixed(history_output())
    canvas = Canvas()

    relay_top, relay_left = 5, 0
    decoder_top, decoder_left = 5, 13
    mapper_top, mapper_left = 8, 42
    data_top, data_left = 15, 0

    canvas.put(relay_top, relay_left, build_history_relay_room())
    canvas.put(decoder_top, decoder_left, build_history_compact_decoder_room())
    canvas.put(mapper_top, mapper_left, build_history_mapper_room())
    canvas.put(data_top, data_left, build_history_fixed_data_room(words))

    canvas.pipe(
        [
            (decoder_top + 5, decoder_left - 1),
            (decoder_top + 5, decoder_left - 2),
            (relay_top + 4, decoder_left - 2),
            (relay_top + 4, relay_left + 10),
        ]
    )
    canvas.pipe(
        [
            (relay_top + 6, relay_left + 5),
            (data_top - 1, relay_left + 5),
            (data_top - 1, decoder_left + 5),
            (decoder_top + 8, decoder_left + 5),
        ]
    )
    canvas.pipe(
        [
            (data_top - 1, decoder_left + 17),
            (decoder_top + 8, decoder_left + 17),
        ]
    )
    canvas.pipe(
        [
            (decoder_top + 6, decoder_left + 26),
            (mapper_top + 3, mapper_left - 1),
        ]
    )

    output_top, output_left = 10, 62
    canvas.put(output_top, output_left, ["+-+", "|O|", "+-+"])
    canvas.pipe(
        [
            (mapper_top + 3, mapper_left + 14),
            (output_top + 1, output_left - 1),
        ]
    )

    return _render_cropped(canvas)
