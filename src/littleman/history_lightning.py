"""History Lesson lightning sprint: is 89x89 (fp 7,921) really the floor?

`docs/alexey-worklog.md` records the negative result "history-lesson is
already at its geometric optimum" from a sweep of ONE parameter (the data
row capacity, 78..91).  This module attacks the other axes -- slot count,
literal field width, layout parity, and the encoding itself -- and turns
the negative result into a proof plus a costed way out.

Everything here is measurement code.  It builds no machine; the one design
that would beat 7,921 (see `projected_footprints`) needs a dictionary
expander that was out of scope for the sprint.

Summary of what is established below, all reproducible from
`tests/test_history_lightning.py`:

1.  The live encoding is a fixed-slot grid: k literal slots per row, each
    slot ````` + f decimal digits + ````` + ``s`` = f + 3 cells.  Its
    width is exactly ``k * (f + 3) + 5`` and its height is
    ``ceil(words / k) + 12``.  Both formulas reproduce the live artifact.

2.  Sweeping BOTH k and f over every feasible value (`layout_sweep`)
    the best max-dimension is 89, attained only at k=4, f=18.  Every
    other point is worse, and the two neighbours 89->85 (k=4, f=17) and
    89->93 (k=4, f=19) show why: shrinking the field costs more rows than
    the columns it saves, exactly the balance Alexey measured, but the
    quantum here is a whole 21-cell slot rather than one cell.

3.  The width cannot be shaved by one column.  A row needs
    ``k * (f + 3) + 1`` data columns because an eastbound row puts its
    ``s`` AFTER the closing backtick and a westbound row puts it BEFORE
    the opening one, so the two directions' column sets differ by one at
    each end.  Overlapping them puts an ``s`` between two vertically
    paired backticks, which is the exact class of load error the server
    returned for `history_00.man`.  `overlap_conflict_columns` exhibits
    the offending columns for the shifted layout.

4.  The result is robust to shrinking the header band.  Even with a
    physically impossible zero-row band the best point is 85x88 = 7,744
    (k=4, f=17); at every band height from 2 rows upwards the winner is
    89x89.  The live band is 10 rows and the decoder room alone is 8, so
    there is nothing to reclaim there.

5.  Therefore no re-layout of the current radix-92 stream can beat 7,921;
    only a shorter token stream can.  `macro_compress` measures how much
    a dictionary of the 20 unused radix-92 codes buys: 2,810 -> 2,086
    tokens (-25.8%), and the expansion round-trips to the exact blob.
    `projected_footprints` turns that into geometry (k=4, f=16, width 81):
    81x81 = 6,561 for a header band up to 14 rows, 83x83 = 6,889 at 16
    rows, 85x85 = 7,225 at 18 rows.  A 10-macro dictionary (2,324 tokens)
    still reaches 84x84 = 7,056 at a 10-row band.  The band has to grow by
    the expander rooms -- a second divide loop plus its quotient relay
    (~26x8 and 10x6), a rotate-by-k dictionary ring served by one small
    room, and a router that steers the first 20 words into the ring -- so
    roughly 900 cells of new room in a band that may spend up to 14 rows.
    That is the whole remaining headroom on this problem, and it is an
    encoding job, not a layout job.
"""

from __future__ import annotations

import collections
import json
import math
from pathlib import Path
from typing import Iterable, NamedTuple, Sequence

REPO = Path(__file__).resolve().parent.parent.parent
PROBLEM_PATH = REPO / "data" / "small" / "problems" / "history-lesson.json"

RADIX = 92
ASCII_SHIFT = 31
#: Rows above the data room in the live artifact: relay + decoder + mapper +
#: output band (rows 5..13) plus the 2-cell pipe gap the server requires,
#: minus the row the data room's own top wall provides.  Measured, not
#: guessed: see `test_overhead_rows_matches_live_artifact`.
OVERHEAD_ROWS = 10
#: The word literal must be readable in both directions, so it may never
#: exceed 63 bits either way; 18 decimal digits is safely inside that and is
#: also where radix-92 saturates (92**9 = 4.72e17).
MAX_FIELD_WIDTH = 18


def expected_output() -> list[int]:
    """The fixed 2,810-byte answer, straight from the archived problem."""

    problem = json.loads(PROBLEM_PATH.read_text())
    return [int(value) for value in problem["publicTestData"][0]["rounds"][0]["out"]]


def expected_text() -> str:
    return "".join(chr(value) for value in expected_output())


# --------------------------------------------------------------------------
# Geometry of the live fixed-slot encoding
# --------------------------------------------------------------------------


def slot_pitch(field_width: int) -> int:
    """Cells one literal slot occupies: backtick, digits, backtick, `s`."""

    return field_width + 3


def room_width(slots: int, field_width: int) -> int:
    """Total program width of a k-slot serpentine data room.

    ``k * pitch`` data columns, plus one more because the eastbound and
    westbound rows disagree about which side of the literal the ``s`` sits
    on, plus two turn columns and two walls.
    """

    return slots * slot_pitch(field_width) + 1 + 2 + 2


def room_height(words: int, slots: int, overhead_rows: int = OVERHEAD_ROWS) -> int:
    """Total program height: data rows, two walls, and the header band."""

    return math.ceil(words / slots) + 2 + overhead_rows


def pack_fixed(values: Sequence[int], field_width: int, radix: int = RADIX) -> list[int]:
    """Minimum number of radix words whose decimal form fits `field_width`.

    Same dynamic program as `littleman.history.pack_history_words_fixed`,
    parameterised so the field width can be swept.
    """

    limit = 10**field_width
    states: list[tuple[int, int, int, int] | None] = [None] * (len(values) + 1)
    states[0] = (0, 0, -1, 0)
    for index in range(len(values)):
        state = states[index]
        if state is None:
            continue
        value = 0
        multiplier = 1
        for length in range(1, 16):
            end = index + length
            if end > len(values):
                break
            digit = values[end - 1]
            if not 0 < digit < radix:
                raise ValueError(f"digit {digit} outside radix {radix}")
            value += digit * multiplier
            multiplier *= radix
            if value >= limit:
                break
            candidate = (state[0] + 1, state[1] + len(str(value)), index, value)
            previous = states[end]
            if previous is None or candidate[:2] < previous[:2]:
                states[end] = candidate
    words: list[int] = []
    index = len(values)
    while index:
        state = states[index]
        if state is None:
            raise ValueError("packing failed")
        words.append(state[3])
        index = state[2]
    words.reverse()
    return words


def unpack_fixed(words: Iterable[int], radix: int = RADIX) -> list[int]:
    """Reference decoder: exactly what the machine's divide loop emits."""

    result: list[int] = []
    for value in words:
        while value:
            value, digit = divmod(value, radix)
            result.append(digit)
    return result


class LayoutPoint(NamedTuple):
    slots: int
    field_width: int
    words: int
    width: int
    height: int

    @property
    def max_dimension(self) -> int:
        return max(self.width, self.height)

    @property
    def footprint(self) -> int:
        return self.max_dimension**2


def layout_sweep(
    tokens: Sequence[int],
    radix: int = RADIX,
    overhead_rows: int = OVERHEAD_ROWS,
    max_field: int = MAX_FIELD_WIDTH,
) -> list[LayoutPoint]:
    """Every feasible (slots, field width) fixed-slot layout, best first."""

    points: list[LayoutPoint] = []
    for field_width in range(4, max_field + 1):
        words = len(pack_fixed(tokens, field_width, radix))
        for slots in range(1, 9):
            width = room_width(slots, field_width)
            height = room_height(words, slots, overhead_rows)
            points.append(LayoutPoint(slots, field_width, words, width, height))
    points.sort(key=lambda point: (point.max_dimension, point.width))
    return points


def slot_columns(slots: int, field_width: int, start: int) -> dict[str, set[int]]:
    """Column sets an eastbound and a westbound row use, given a start column.

    Eastbound slot: backtick, digits, backtick, `s`.
    Westbound slot: `s`, backtick, digits, backtick (increasing column
    order; the little man meets them right to left).
    """

    pitch = slot_pitch(field_width)
    east_ticks: set[int] = set()
    east_sends: set[int] = set()
    west_ticks: set[int] = set()
    west_sends: set[int] = set()
    for index in range(slots):
        base = start + index * pitch
        east_ticks |= {base, base + field_width + 1}
        east_sends.add(base + field_width + 2)
        west_sends.add(base)
        west_ticks |= {base + 1, base + field_width + 2}
    return {
        "east_ticks": east_ticks,
        "east_sends": east_sends,
        "west_ticks": west_ticks,
        "west_sends": west_sends,
    }


def overlap_conflict_columns(slots: int, field_width: int) -> set[int]:
    """Columns that break if east/westbound rows share their column span.

    Saving the extra data column means putting both directions' slots at
    the same start column.  A column holding a backtick on every eastbound
    row and an `s` on every westbound row then pairs its backticks across
    the intervening `s`, which is precisely
    "expected a digit or a space between backticks" -- the load error the
    server returned for history_00.
    """

    columns = slot_columns(slots, field_width, start=1)
    return (columns["east_ticks"] & columns["west_sends"]) | (
        columns["west_ticks"] & columns["east_sends"]
    )


# --------------------------------------------------------------------------
# The only way out: a shorter token stream
# --------------------------------------------------------------------------


def free_code_count(values: Sequence[int], radix: int = RADIX) -> int:
    """Radix codes not needed by the alphabet, i.e. usable as macros."""

    return (radix - 1) - len({value - ASCII_SHIFT for value in values})


class Compression(NamedTuple):
    macros: list[str]
    tokens: list[int]
    alphabet: list[int]

    @property
    def ratio(self) -> float:
        return len(self.tokens)


def macro_compress(text: str, macro_budget: int, max_expansion: int = 9) -> Compression:
    """Greedy dictionary: repeatedly fold the highest-gain repeated phrase.

    Each macro takes one of the radix's unused codes and expands to at most
    `max_expansion` characters, which is what one radix-92 word can hold, so
    the machine-side expander can reuse the existing divide loop verbatim.
    """

    units: list[str] = list(text)
    macros: list[str] = []
    for _ in range(macro_budget):
        best: tuple[int, tuple[str, ...]] | None = None
        for length in range(2, max_expansion + 1):
            counts = collections.Counter(
                tuple(units[index : index + length])
                for index in range(len(units) - length + 1)
            )
            for phrase, count in counts.items():
                if count < 2:
                    continue
                if sum(len(part) for part in phrase) > max_expansion:
                    continue
                gain = (length - 1) * count
                if best is None or gain > best[0]:
                    best = (gain, phrase)
        if best is None or best[0] <= 0:
            break
        _, phrase = best
        macros.append("".join(phrase))
        merged = "".join(phrase)
        folded: list[str] = []
        index = 0
        while index < len(units):
            if tuple(units[index : index + len(phrase)]) == phrase:
                folded.append(merged)
                index += len(phrase)
            else:
                folded.append(units[index])
                index += 1
        units = folded

    alphabet = sorted({unit for unit in units if len(unit) == 1})
    code_of = {symbol: index + 1 for index, symbol in enumerate(alphabet)}
    for offset, macro in enumerate(macros):
        code_of[macro] = len(alphabet) + 1 + offset
    tokens = [code_of[unit] for unit in units]
    return Compression(macros, tokens, [ord(symbol) for symbol in alphabet])


def expand_tokens(compression: Compression) -> str:
    """Reference expander: the machine-side room this design would need."""

    symbols = [chr(value) for value in compression.alphabet]
    out: list[str] = []
    for token in compression.tokens:
        if token <= len(symbols):
            out.append(symbols[token - 1])
        else:
            out.append(compression.macros[token - len(symbols) - 1])
    return "".join(out)


def projected_footprints(
    compression: Compression, band_rows: Iterable[int] = (10, 12, 14, 16, 18)
) -> list[tuple[int, LayoutPoint]]:
    """Best layout for the compressed stream at several header-band heights."""

    results = []
    for band in band_rows:
        best = layout_sweep(compression.tokens, overhead_rows=band)[0]
        results.append((band, best))
    return results
