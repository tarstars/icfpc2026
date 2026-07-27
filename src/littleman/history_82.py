"""An 82-square History Lesson archive.

The machine architecture is inherited from :mod:`littleman.history_compact`.
The offline dictionary is selected for two coupled costs:

* at most 1,782 main symbols, so 198 radix-128 words fit in 66 rows;
* at most 456 cells of paired lookup literals, so six row-pairs fit in an
  82-column room.

The fixed token tuple below is the deterministic result of a seed-20260727
single-swap search over every repeated substring of length two through five.
Its exact suffix DP needs 1,763 symbols and its minimum paired lookup cost is
456 cells.
"""

from __future__ import annotations

import collections

from . import history_pack
from .canvas import Canvas
from .history_archive import _blank_room, _pack_little_endian, build_splitter_room
from .history_compact import (
    MAIN_PER_WORD,
    MAIN_RADIX,
    OUTPUT_RADIX,
    OUTPUT_ROOM,
    CompactArchive,
    _item_width,
    _literal_send,
    _token_word,
    build_rotated_selector_room,
)

TOKENS = (
    "cti",
    "; 20",
    ", ",
    '" (',
    ": ",
    "on",
    "an",
    "or",
    "er",
    "in",
    "ed ",
    "en",
    "re",
    "al",
    "e ",
    "ell",
    's" (',
    "it",
    "ic",
    "as",
    "at",
    "mod",
    "n Jon",
    "el",
    "th",
    "es",
    ", S",
    " and ",
    "Peyto",
    "ar",
    "igh",
    "bur",
    "ype",
    "is",
    "im",
    "199",
    " M",
    "and",
    "Hask",
    "s ",
    "a ",
    "Simon",
    "t ",
    "tract",
    "); 20",
    "ation",
    " S",
    "ing ",
    ' "',
    " L",
    "avid",
    "for ",
    ", USA",
    " R",
    "st",
    "am",
)

# Each tuple describes the widths of the literal pairs on one eastbound row.
# The first row receives the boundary pair (width five) separately.  All six
# rows therefore carry exactly 76 cells.
PAIR_WIDTH_PATTERNS = (
    (6, *(5 for _ in range(13))),
    (*(6 for _ in range(6)), *(5 for _ in range(8))),
    (8, 8, 7, 7, 7, 6, 6, 6, 6, 5, 5, 5),
    (10, 9, 9, 8, 8, 8, 8, 8, 8),
    (12, 11, 10, 10, 10, 8, 8, 7),
    (14, 14, 14, 14, 12, 8),
)


def _parser_safe_positions(
    ids: list[int],
    real_items: list[tuple[int, int]],
    initial_rows: list[list[tuple[int | None, int]]],
) -> dict[int, int]:
    """Assign equal-width entries so every packed literal parses both ways."""

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


def _build_archive(
    token_source: tuple[str, ...],
    pair_width_patterns: tuple[tuple[int, ...], ...],
    expected_symbols: int,
    expected_words: int,
    label: str,
) -> CompactArchive:
    """Build one fixed archive and its six lookup row-pairs."""

    text = history_pack.expected_text()
    tokens = list(token_source)
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
    for index, pattern in enumerate(pair_width_patterns):
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

    lookup_values = [value for row in item_rows for _, value in row]
    main_codes = [entry_to_code[entry] for entry in ids]
    main_words = _pack_little_endian(main_codes, MAIN_RADIX, MAIN_PER_WORD)
    if not (
        len(tokens) == 56
        and len(main_codes) == expected_symbols
        and len(main_words) == expected_words
        and len(lookup_values) == 128
    ):
        raise AssertionError(
            f"{label} archive measurements changed: "
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


def build_archive() -> CompactArchive:
    """Build the fixed 1,763-symbol archive and its six lookup row-pairs."""

    return _build_archive(TOKENS, PAIR_WIDTH_PATTERNS, 1763, 196, "82-square")


def reference_decode(archive: CompactArchive) -> str:
    """Decode through the exact lookup values consumed by the machine."""

    output: list[str] = []
    for code in archive.main_codes:
        value = archive.lookup_values[code]
        while value:
            value, char = divmod(value, OUTPUT_RADIX)
            output.append(chr(char))
    return "".join(output)


def _build_main_room(archive: CompactArchive, rows: int) -> list[str]:
    """Render three words per row, padding unused slots with inert zeros."""

    from .history_archive import build_word_room

    return build_word_room(
        archive.main_words,
        field=19,
        rows=rows,
        cyclic=False,
    )


def build_main_room(archive: CompactArchive) -> list[str]:
    """Render 196 words, plus two inert zero words, in 66 rows."""

    return _build_main_room(archive, rows=66)


def build_lookup_room(archive: CompactArchive) -> list[str]:
    """Render the tight six-pair cyclic lookup in a 14x82 room."""

    return _build_lookup_room(archive, width=82)


def _build_lookup_room(archive: CompactArchive, width: int) -> list[str]:
    """Render a six-pair cyclic lookup in a fixed-width room."""

    grid = _blank_room(14, width)
    payload = width - 6
    turn = width - 2
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
            grid[row][turn] = "v"
            start = 4
        else:
            physical = [segment[::-1] for segment in reversed(segments)]
            grid[row][turn] = "<"
            grid[row][2] = "<" if last else "v"
            start = 3
        tape = "".join(physical)
        if len(tape) != payload:
            raise AssertionError(
                f"lookup row must fill its exact {payload}-cell payload"
            )
        grid[row][start : start + len(tape)] = tape
    grid[1][1] = ">"
    grid[12][1] = "^"
    return ["".join(row) for row in grid]


def build_history_82() -> str:
    """Assemble the 82x82 candidate."""

    archive = build_archive()
    main = build_main_room(archive)
    lookup = build_lookup_room(archive)
    main_splitter = build_splitter_room(MAIN_RADIX)
    output_splitter = build_splitter_room(OUTPUT_RADIX)
    selector = build_rotated_selector_room()

    canvas = Canvas()
    canvas.put(0, 0, main)
    canvas.put(68, 0, lookup)
    canvas.put(2, 73, main_splitter)
    canvas.put(21, 71, selector)
    canvas.put(45, 73, output_splitter)
    canvas.put(64, 74, OUTPUT_ROOM)

    canvas.pipe([(16, 71), (16, 72)])
    canvas.pipe([(19, 80), (19, 79), (20, 79)])
    canvas.pipe([(67, 81), (35, 81), (35, 80)])
    canvas.pipe([(43, 75), (44, 75)])
    canvas.pipe([(62, 75), (63, 75)])
    return canvas.render()
