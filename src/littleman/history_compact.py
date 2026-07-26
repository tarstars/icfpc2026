"""An 83-square candidate architecture for History Lesson.

The offline encoder uses 56 dictionary entries of at most five characters.
The machine has two streams:

* 201 radix-128 words contain exactly nine text symbols apiece;
* a cyclic lookup tape maps each symbol to either one ASCII value or one
  little-endian radix-128 token word.

One tiny selector joins those streams.  A radix-128 splitter then emits both
single characters and complete short tokens without a separate ASCII mapper.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass

from . import history_pack
from .canvas import Canvas
from .history_archive import (
    _blank_room,
    _pack_little_endian,
    build_splitter_room,
    build_word_room,
)

TOKEN_COUNT = 56
TOKEN_MAX_LEN = 5
MAIN_RADIX = 128
OUTPUT_RADIX = 128
MAIN_PER_WORD = 9
PAIR_WIDTH_PATTERNS = (
    # The first row also begins with the five-cell boundary pair.
    (14, 9, 8, 8, 7, 6, 6, 5, 5),
    (14, 10, 8, 8, 7, 6, 6, 5, 5, 5),
    (12, 12, 8, 8, 6, 6, 5, 5, 5, 5, 5),
    (14, 10, 8, 8, 6, 6, 5, 5, 5, 5, 5),
    (13, 10, 8, 8, 7, 6, 5, 5, 5, 5, 5),
    (14, 8, 8, 8, 7, 6, 6, 5, 5, 5, 5),
)


@dataclass(frozen=True)
class CompactArchive:
    text: str
    tokens: tuple[str, ...]
    main_codes: tuple[int, ...]
    main_words: tuple[int, ...]
    lookup_values: tuple[int, ...]
    lookup_rows: tuple[tuple[int, ...], ...]
    lookup_width_rows: tuple[tuple[int, ...], ...]


def _choose_tokens(text: str) -> list[str]:
    """Use the established greedy factory, bounded for one-word expansions."""

    selected: list[str] = []
    working = text
    for _ in range(TOKEN_COUNT):
        best: tuple[int, str] | None = None
        for length in range(2, TOKEN_MAX_LEN + 1):
            candidates = collections.Counter(
                working[index : index + length]
                for index in range(len(working) - length + 1)
            )
            for candidate, hits in candidates.items():
                if (
                    hits < 2
                    or history_pack.SEP in candidate
                ):
                    continue
                gain = hits * (length - 1)
                if best is None or gain > best[0]:
                    best = (gain, candidate)
        if best is None:  # pragma: no cover - the canonical text has 51
            break
        selected.append(best[1])
        working = working.replace(best[1], history_pack.SEP)
    return selected


def _token_word(token: str) -> int:
    return sum(ord(char) * OUTPUT_RADIX**offset for offset, char in enumerate(token))


def _item_width(value: int) -> int:
    return 2 if value < 10 else len(str(value)) + 3


def _parser_safe_positions(
    ids: list[int],
    real_items: list[tuple[int, int]],
    initial_rows: list[list[tuple[int | None, int]]],
) -> dict[int, int]:
    """Assign equal-width entries so every nine-code literal parses both ways."""

    starts = collections.Counter(ids[::MAIN_PER_WORD])
    entries_by_width: dict[int, list[int]] = collections.defaultdict(list)
    slots_by_width: dict[int, list[int]] = collections.defaultdict(list)
    values = dict(real_items)
    for entry, value in real_items:
        entries_by_width[_item_width(value)].append(entry)
    position = 0
    for row in initial_rows:
        for entry, value in row:
            if entry is not None:
                slots_by_width[_item_width(value)].append(position)
            position += 1

    assignment: dict[int, int] = {}
    for width, entries in entries_by_width.items():
        entries.sort(key=lambda entry: (-starts[entry], entry))
        slots = slots_by_width[width]
        slots.sort(key=lambda slot: (slot % 10 == 9, slot))
        assignment.update(zip(entries, slots, strict=True))

    chunks = [
        ids[start : start + MAIN_PER_WORD]
        for start in range(0, len(ids), MAIN_PER_WORD)
    ]
    if any(len(chunk) != MAIN_PER_WORD for chunk in chunks):
        raise AssertionError("83-square stream must fill every main word")
    occurrences: dict[int, set[int]] = collections.defaultdict(set)
    for word_index, chunk in enumerate(chunks):
        for entry in set(chunk):
            occurrences[entry].add(word_index)

    powers = [MAIN_RADIX**offset for offset in range(MAIN_PER_WORD)]
    limit = (1 << 63) - 1

    def safe(word_index: int) -> bool:
        value = sum(
            assignment[entry] * powers[offset]
            for offset, entry in enumerate(chunks[word_index])
        )
        return int(str(value)[::-1]) <= limit

    bad = {word_index for word_index in range(len(chunks)) if not safe(word_index)}
    while bad:
        best: tuple[tuple[int, int, int], int, int, set[int]] | None = None
        for word_index in sorted(bad):
            for first in sorted(set(chunks[word_index])):
                width = _item_width(values[first])
                for second in entries_by_width[width]:
                    if first == second:
                        continue
                    affected = occurrences[first] | occurrences[second]
                    before = sum(index in bad for index in affected)
                    assignment[first], assignment[second] = (
                        assignment[second],
                        assignment[first],
                    )
                    after = sum(not safe(index) for index in affected)
                    assignment[first], assignment[second] = (
                        assignment[second],
                        assignment[first],
                    )
                    key = (before - after, -first, -second)
                    if key[0] > 0 and (best is None or key > best[0]):
                        best = (key, first, second, affected)
        if best is None:
            raise AssertionError("equal-width swaps could not make literals safe")
        _, first, second, affected = best
        assignment[first], assignment[second] = (
            assignment[second],
            assignment[first],
        )
        bad.difference_update(affected)
        bad.update(index for index in affected if not safe(index))
    return assignment


def build_archive() -> CompactArchive:
    """Build the deterministic symbol stream and paired-row lookup order."""

    text = history_pack.expected_text()
    tokens = _choose_tokens(text)
    alphabet = sorted(set(text))
    ids = history_pack.tokenise(text, tokens)
    real_items = [
        *((entry, ord(char)) for entry, char in enumerate(alphabet)),
        *(
            (len(alphabet) + index, _token_word(token))
            for index, token in enumerate(tokens)
        ),
    ]

    boundary: tuple[int | None, int] = (None, 0)
    remaining = list(real_items)
    boundary_mate = min(
        remaining,
        key=lambda item: (_item_width(item[1]), item[0]),
    )
    remaining.remove(boundary_mate)
    pairs: list[tuple[tuple[int | None, int], tuple[int | None, int], int]] = [
        (boundary, boundary_mate, _item_width(boundary_mate[1]))
    ]
    remaining.sort(key=lambda item: (-_item_width(item[1]), item[0]))
    for offset in range(0, len(remaining), 2):
        first, second = remaining[offset : offset + 2]
        pairs.append(
            (
                first,
                second,
                max(_item_width(first[1]), _item_width(second[1])),
            )
        )

    pair_queues: dict[int, collections.deque] = collections.defaultdict(
        collections.deque
    )
    for pair in pairs[1:]:
        pair_queues[pair[2]].append(pair)
    bins: list[list] = []
    for index, pattern in enumerate(PAIR_WIDTH_PATTERNS):
        row_pairs = [pairs[0]] if index == 0 else []
        row_pairs.extend(pair_queues[width].popleft() for width in pattern)
        bins.append(row_pairs)
    if any(pair_queues.values()):
        raise AssertionError("lookup width patterns left unused pairs")

    initial_rows: list[list[tuple[int | None, int]]] = []
    width_rows: list[list[int]] = []
    for row_pairs in bins:
        initial_rows.append([pair[0] for pair in row_pairs])
        initial_rows.append([pair[1] for pair in reversed(row_pairs)])
        width_rows.extend(
            ([pair[2] for pair in row_pairs], [pair[2] for pair in reversed(row_pairs)])
        )
    if initial_rows[0][0] != (None, 0):
        raise AssertionError("cyclic lookup must begin with the zero boundary")

    entry_to_code = _parser_safe_positions(ids, real_items, initial_rows)
    placed: list[tuple[int | None, int] | None] = [None] * 128
    placed[0] = boundary
    for entry, value in real_items:
        placed[entry_to_code[entry]] = (entry, value)
    if any(item is None for item in placed):
        raise AssertionError("lookup assignment did not fill every position")

    item_rows: list[list[tuple[int | None, int]]] = []
    position = 0
    for initial_row in initial_rows:
        end = position + len(initial_row)
        row = placed[position:end]
        if any(
            _item_width(item[1]) != _item_width(slot[1])
            for item, slot in zip(row, initial_row, strict=True)
        ):
            raise AssertionError("lookup assignment changed a literal field width")
        item_rows.append(row)  # type: ignore[arg-type]
        position = end

    lookup_values: list[int] = []
    for row in item_rows:
        for entry, value in row:
            lookup_values.append(value)
    main_codes = [entry_to_code[entry] for entry in ids]
    main_words = _pack_little_endian(main_codes, MAIN_RADIX, MAIN_PER_WORD)
    if not (
        len(tokens) == TOKEN_COUNT
        and len(main_codes) == 1809
        and len(main_words) == 201
        and len(lookup_values) == 128
    ):
        raise AssertionError(
            "compact archive measurements changed: "
            f"{len(tokens), len(main_codes), len(main_words), len(lookup_values)}"
        )
    return CompactArchive(
        text,
        tuple(tokens),
        tuple(main_codes),
        tuple(main_words),
        tuple(lookup_values),
        tuple(tuple(value for _, value in row) for row in item_rows),
        tuple(tuple(row) for row in width_rows),
    )


def reference_decode(archive: CompactArchive) -> str:
    """Decode through the exact lookup values consumed by the machine."""

    output: list[str] = []
    for code in archive.main_codes:
        value = archive.lookup_values[code]
        while value:
            value, char = divmod(value, OUTPUT_RADIX)
            output.append(chr(char))
    return "".join(output)


def _literal_send(value: int, field: int | None = None) -> str:
    if field is None and value < 10:
        return f"{value}s"
    digits = str(value)
    if field is not None:
        if len(digits) > field:
            raise ValueError(f"{value} exceeds a {field}-digit field")
        digits = digits.rjust(field)
    return f"`{digits}`s"


def build_main_room(archive: CompactArchive) -> list[str]:
    """Three parser-safe 19-digit words per row in a 69x71 room."""

    return build_word_room(
        archive.main_words,
        field=19,
        rows=67,
        cyclic=False,
    )


def build_lookup_room(archive: CompactArchive) -> list[str]:
    """Render the paired-row lookup tape as a cyclic 14x83 room."""

    grid = _blank_room(14, 83)
    for offset, (values, widths) in enumerate(
        zip(archive.lookup_rows, archive.lookup_width_rows, strict=True)
    ):
        row = offset + 1
        east = offset % 2 == 0
        last = offset == len(archive.lookup_rows) - 1
        segments = [
            _literal_send(value, field=width - 3)
            for value, width in zip(values, widths, strict=True)
        ]
        if east:
            physical = segments
            grid[row][2] = "@" if offset == 0 else ">"
            grid[row][81] = "v"
            start = 4
        else:
            physical = [segment[::-1] for segment in reversed(segments)]
            grid[row][81] = "<"
            grid[row][2] = "<" if last else "v"
            start = 3
        tape = "".join(physical)
        if not 1 <= len(tape) <= 77:
            raise AssertionError("lookup bin escaped its 77-cell payload")
        grid[row][start : start + len(tape)] = tape
    grid[1][1] = ">"
    grid[12][1] = "^"
    return ["".join(row) for row in grid]


def rotate_clockwise(room: list[str]) -> list[str]:
    """Rotate a room while preserving walking directions and literal order."""

    arrows = {">": "v", "v": "<", "<": "^", "^": ">", "-": "|", "|": "-"}
    height, width = len(room), len(room[0])
    return [
        "".join(
            arrows.get(room[height - 1 - col][row], room[height - 1 - col][row])
            for col in range(height)
        )
        for row in range(width)
    ]


def build_selector_room() -> list[str]:
    """Join main ids with the cyclic value tape in a compact two-loop room."""

    grid = _blank_room(9, 22)
    cells = {
        # Read a 1-based lookup position from the main splitter.
        (1, 1): ">",
        (1, 2): "@",
        (1, 3): "r",
        (1, 4): "b",
        (1, 5): "v",
        (2, 5): ">",
        (2, 12): "v",
        # Discard lookup values until the zero boundary.
        (3, 12): ">",
        (3, 13): "r",
        (3, 14): "X",
        (3, 15): "v",
        (4, 12): "^",
        (4, 14): "<",
        # Count values after the boundary and send the selected one.
        (5, 15): ">",
        (5, 16): "r",
        (5, 17): "m",
        (5, 18): "d",
        (5, 19): "s",
        (5, 20): "v",
        (6, 15): "^",
        (6, 18): "<",
        # Re-enter the main read after a selected value is sent.
        (7, 1): "^",
        (7, 20): "<",
    }
    for (row, col), char in cells.items():
        grid[row][col] = char
    return ["".join(row) for row in grid]


def build_rotated_selector_room() -> list[str]:
    """Rotate the selector and add a one-cell east-facing start spur."""

    grid = [list(row) for row in rotate_clockwise(build_selector_room())]
    starts = [
        (row, col)
        for row, cells in enumerate(grid)
        for col, char in enumerate(cells)
        if char == "@"
    ]
    if starts != [(2, 7)] or grid[2][6] != " ":
        raise AssertionError("selector rotation changed")
    grid[2][7] = "v"
    grid[2][6] = "@"
    return ["".join(row) for row in grid]


OUTPUT_ROOM = ["+-+", "|O|", "+-+"]


def build_history_compact() -> str:
    """Assemble the intended 83x83 candidate."""

    archive = build_archive()
    main = build_main_room(archive)
    lookup = build_lookup_room(archive)
    main_splitter = build_splitter_room(MAIN_RADIX)
    output_splitter = build_splitter_room(OUTPUT_RADIX)
    selector = build_rotated_selector_room()

    canvas = Canvas()
    canvas.put(0, 0, main)
    canvas.put(69, 0, lookup)
    canvas.put(2, 73, main_splitter)
    canvas.put(21, 72, selector)
    canvas.put(45, 73, output_splitter)
    canvas.put(64, 74, OUTPUT_ROOM)

    canvas.pipe([(16, 71), (16, 72)])
    canvas.pipe([(19, 80), (19, 79), (20, 79)])
    canvas.pipe([(68, 82), (35, 82), (35, 81)])
    canvas.pipe([(43, 75), (44, 75)])
    canvas.pipe([(62, 75), (63, 75)])
    return canvas.render()
