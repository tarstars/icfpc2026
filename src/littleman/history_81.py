"""An 81-square History Lesson archive."""

from __future__ import annotations

import sys
from pathlib import Path

from .canvas import Canvas
from .history_82 import (
    _build_archive,
    _build_lookup_room,
    _build_main_room,
    reference_decode,
)
from .history_archive import build_splitter_room
from .history_compact import (
    MAIN_RADIX,
    OUTPUT_RADIX,
    OUTPUT_ROOM,
    CompactArchive,
    build_rotated_selector_room,
)

TOKENS = (
    ' "',
    " L",
    " M",
    " R",
    " S",
    " and ",
    " for ",
    '" (',
    "); 20",
    ", ",
    ", USA",
    ": ",
    "; 199",
    "; 20",
    "David",
    "Hask",
    "Simon Pe",
    "a ",
    "al",
    "am",
    "an",
    "ap",
    "ar",
    "at",
    "bur",
    "co",
    "ct",
    "e ",
    "ed ",
    "el",
    "ell",
    "em",
    "en",
    "er",
    "es",
    "gh",
    "ic",
    "im",
    "in",
    "ing ",
    "ion",
    "ir",
    "is",
    "it",
    "la",
    "le",
    "on",
    "or",
    "re",
    "s ",
    "ss",
    "st",
    "t ",
    "th",
    "un",
    "yton Jon",
)

# The boundary pair adds five cells to the first row. These six patterns
# therefore fill 70, 75, 75, 75, 75, and 75 cells respectively.
PAIR_WIDTH_PATTERNS = (
    (20, 14, 14, 13, 9),
    (12, 11, 10, 8, 8, 8, 8, 5, 5),
    (8, 8, 8, 8, 8, 8, 8, 8, 6, 5),
    (8, 8, 8, 8, 7, 7, 7, 7, 5, 5, 5),
    (6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 5, 5, 5),
    (*(5 for _ in range(15)),),
)


def build_archive() -> CompactArchive:
    """Build the fixed 1,754-symbol, 450-cell joint archive."""

    return _build_archive(
        TOKENS,
        PAIR_WIDTH_PATTERNS,
        expected_symbols=1754,
        expected_words=195,
        label="81-square",
    )


def build_history_81() -> str:
    """Assemble the 81x81 machine."""

    archive = build_archive()
    main = _build_main_room(archive, rows=65)
    lookup = _build_lookup_room(archive, width=81)
    main_splitter = build_splitter_room(MAIN_RADIX)
    output_splitter = build_splitter_room(OUTPUT_RADIX)
    selector = build_rotated_selector_room()

    canvas = Canvas()
    canvas.put(0, 0, main)
    canvas.put(67, 0, lookup)
    canvas.put(2, 73, main_splitter)
    canvas.put(21, 71, selector)
    canvas.put(45, 72, output_splitter)
    canvas.put(64, 73, OUTPUT_ROOM)

    canvas.pipe([(16, 71), (16, 72)])
    canvas.pipe([(19, 80), (19, 79), (20, 79)])
    canvas.pipe([(66, 80), (35, 80)])
    canvas.cells[(35, 80)] = "<"
    canvas.pipe([(43, 74), (44, 74)])
    canvas.pipe([(62, 74), (63, 74)])
    return canvas.render()


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        raise SystemExit("usage: python -m littleman.history_81 OUTPUT")
    Path(args[0]).write_text(build_history_81())
    return 0


__all__ = [
    "PAIR_WIDTH_PATTERNS",
    "TOKENS",
    "build_archive",
    "build_history_81",
    "reference_decode",
]


if __name__ == "__main__":
    raise SystemExit(main())
