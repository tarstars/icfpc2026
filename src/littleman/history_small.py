"""Smaller-footprint generator for the History Lesson problem.

The output is a fixed 2810-character string, so the whole problem is data
encoding.  ``history.py`` packs 9 characters per 18-decimal-digit literal in
radix 92 (``ascii - 31``), which forces a 4*21+5 = 89 cell wide data room and
an 89x89 footprint.

Here the literal field shrinks to 17 digits.  A 17-digit field only holds 9
symbols when the radix is at most 77, so the alphabet is compressed:

* the 71 distinct characters are indexed in ASCII order, and the decoder
  turns an index back into ASCII with a short chain of conditional adds
  (one per gap in the used-ASCII range);
* a handful of top indices are dictionary tokens that expand to fixed
  substrings, which buys back the rows the narrower field costs.

The data room is transposed (a vertical serpentine), so the leftover space is
a tall narrow strip -- a much better shape for stacking decoder rooms than the
short wide band a horizontal data room leaves behind.
"""

from __future__ import annotations

import json
from pathlib import Path

from littleman.canvas import Canvas

REPO = Path(__file__).resolve().parent.parent.parent
PROBLEM_PATH = REPO / "data" / "small" / "problems" / "history-lesson.json"

FIELD = 17
SLOTS_PER_LINE = 4
RADIX = 77
TOKEN_COUNT = 3
TOKEN_MAX_LEN = 6
LIMIT = 10**FIELD


def history_output() -> list[int]:
    """Load the canonical byte sequence from the archived problem."""

    problem = json.loads(PROBLEM_PATH.read_text())
    return [int(value) for value in problem["publicTestData"][0]["rounds"][0]["out"]]


def history_text() -> str:
    return "".join(chr(value) for value in history_output())


def ascii_runs(text: str) -> list[tuple[int, int]]:
    """Maximal runs of consecutive ASCII codes that the text actually uses."""

    used = sorted({ord(character) for character in text})
    runs: list[list[int]] = []
    for code in used:
        if runs and code == runs[-1][1] + 1:
            runs[-1][1] = code
        else:
            runs.append([code, code])
    return [(low, high) for low, high in runs]


def merge_runs(runs: list[tuple[int, int]], absorb: int) -> list[tuple[int, int]]:
    """Merge the ``absorb`` cheapest gaps, trading index slots for chain nodes."""

    pieces = [list(run) for run in runs]
    for _ in range(absorb):
        gaps = [
            (pieces[i + 1][0] - pieces[i][1] - 1, i) for i in range(len(pieces) - 1)
        ]
        if not gaps:
            break
        _, index = min(gaps)
        pieces[index][1] = pieces[index + 1][1]
        del pieces[index + 1]
    return [(low, high) for low, high in pieces]


def build_pieces(text: str, token_count: int) -> list[tuple[int, int]]:
    """Pick the coarsest piece list that still leaves room for the tokens."""

    runs = ascii_runs(text)
    distinct = sum(high - low + 1 for low, high in runs)
    for absorb in range(len(runs)):
        pieces = merge_runs(runs, absorb)
        slots = sum(high - low + 1 for low, high in pieces)
        if slots + token_count <= RADIX - 1:
            best = pieces
        else:
            break
    del distinct
    return best


def index_map(pieces: list[tuple[int, int]]) -> dict[int, int]:
    """ASCII code -> packing index (1-based, ascending)."""

    mapping = {}
    index = 1
    for low, high in pieces:
        for code in range(low, high + 1):
            mapping[code] = index
            index += 1
    return mapping


def choose_tokens(text: str, count: int = TOKEN_COUNT) -> list[str]:
    """Greedily pick substrings whose replacement saves the most symbols."""

    working = text
    tokens: list[str] = []
    for _ in range(count):
        best_gain, best_sub = 0, None
        for length in range(2, TOKEN_MAX_LEN + 1):
            seen = {working[i : i + length] for i in range(len(working) - length + 1)}
            for sub in seen:
                if "\x00" in sub:
                    continue
                gain = working.count(sub) * (length - 1)
                if gain > best_gain:
                    best_gain, best_sub = gain, sub
        if best_sub is None:
            break
        tokens.append(best_sub)
        working = working.replace(best_sub, "\x00")
    return tokens


def encode_symbols(text: str, mapping: dict[int, int], tokens: list[str]) -> list[int]:
    """Rewrite the text as packing symbols: characters first, then tokens."""

    token_base = max(mapping.values()) + 1
    working = text
    for index, token in enumerate(tokens):
        working = working.replace(token, chr(index))
    symbols = []
    for character in working:
        if ord(character) < len(tokens):
            symbols.append(token_base + ord(character))
        else:
            symbols.append(mapping[ord(character)])
    if symbols and max(symbols) >= RADIX:
        raise ValueError("symbol alphabet does not fit the radix")
    return symbols


def decode_symbols(symbols: list[int], mapping: dict[int, int], tokens: list[str]) -> str:
    token_base = max(mapping.values()) + 1
    inverse = {index: code for code, index in mapping.items()}
    out = []
    for symbol in symbols:
        if symbol >= token_base:
            out.append(tokens[symbol - token_base])
        else:
            out.append(chr(inverse[symbol]))
    return "".join(out)


def pack_words(symbols: list[int]) -> list[int]:
    """Least-squares-free DP: fewest little-endian radix words under 10**FIELD."""

    count = len(symbols)
    infinity = count + 1
    best = [infinity] * (count + 1)
    step = [0] * (count + 1)
    best[count] = 0
    for start in range(count - 1, -1, -1):
        value, multiplier = 0, 1
        for length in range(1, 14):
            if start + length > count:
                break
            value += symbols[start + length - 1] * multiplier
            multiplier *= RADIX
            if value >= LIMIT:
                break
            if best[start + length] + 1 < best[start]:
                best[start] = best[start + length] + 1
                step[start] = length
    words = []
    position = 0
    while position < count:
        length = step[position]
        value, multiplier = 0, 1
        for offset in range(length):
            value += symbols[position + offset] * multiplier
            multiplier *= RADIX
        words.append(value)
        position += length
    while len(words) % SLOTS_PER_LINE:
        words.append(0)
    return words


def unpack_words(words: list[int]) -> list[int]:
    symbols = []
    for value in words:
        while value:
            value, digit = divmod(value, RADIX)
            symbols.append(digit)
    return symbols


def build_encoding():
    """Return (pieces, mapping, tokens, symbols, words) for the live encoding."""

    text = history_text()
    tokens = choose_tokens(text, TOKEN_COUNT)
    pieces = build_pieces(text, len(tokens))
    mapping = index_map(pieces)
    symbols = encode_symbols(text, mapping, tokens)
    words = pack_words(symbols)
    if decode_symbols(unpack_words(words), mapping, tokens) != text:
        raise ValueError("packing round-trip failed")
    return pieces, mapping, tokens, symbols, words


# ---------------------------------------------------------------------------
# Machine layout: 85x85, four rooms, three pipes (as built and verified)
# ---------------------------------------------------------------------------
#
# Footprint arithmetic (all measured, see build_encoding()):
#   FIELD=17 -> RADIX=77 gives 9 symbols per word (77**9 < 1e17).  288 words.
#   Vertical serpentine: 4 slots of (1+17+1 literal + 1 send) = 80 data rows
#   plus 3 turn rows = 83 interior, room 85 tall; 72 data columns + 1 entry
#   column + 2 walls = 75 wide.  Leftover is a TALL strip, cols 75..84.
#
#   DATA(0,0 85x75) --> CORE(2,76 16x9) --> MAPPER(20,75 60x10) --> OUTPUT
#
# Every room has at most one incoming and one outgoing pipe, so `s`/`r` never
# need a nearest-pipe audit.
#
# DATA: down- and up-columns carry backticks, digits and sends on exactly the
#   same rows, so horizontal backtick pairs are always adjacent (empty) and can
#   never straddle an `s`.  That is the parser trap that killed history_00.
# CORE (radix split): r ; b ; d skips the zero padding word; otherwise the
#   column M `77` W / W s W drops a digit, and X at its foot loops while the
#   quotient is positive.
# MAPPER (index -> ASCII): A = index + 31, then seven conditional-add nodes
#   M `bound` - b W d  --  `-` leaves BP = bound - A while W restores A, so the
#   test is non-destructive and a leaf needs no add-back at all: it just walks
#   to the shared `s`.  Nodes run south in one column and north in the next so
#   both 48-row runs fit the 58-row interior.  The eighth node (bound 123)
#   separates characters from the three dictionary tokens, whose emitters are
#   straight `nnn` s columns.
# OUTPUT: 3x3 room with O.


# ---------------------------------------------------------------------------
# Room builders
# ---------------------------------------------------------------------------

DATA_HEIGHT = 85
DATA_WIDTH = 75
DATA_FIRST_COL = 2
DATA_COLUMNS = 72


def _blank_room(height: int, width: int) -> list[list[str]]:
    edge = ["+"] + ["-"] * (width - 2) + ["+"]
    return [
        list(edge),
        *[["|"] + [" "] * (width - 2) + ["|"] for _ in range(height - 2)],
        list(edge),
    ]


def build_data_room(words: list[int]) -> list[str]:
    """Vertical serpentine literal store: 75 wide x 85 tall, 4 words per column.

    Every data column carries backticks on the same eight rows and digits on
    the same rows, so horizontal backtick pairs are always adjacent (empty)
    and never straddle an ``s``.
    """

    if len(words) != DATA_COLUMNS * SLOTS_PER_LINE:
        raise ValueError("data room expects exactly 288 words")
    grid = _blank_room(DATA_HEIGHT, DATA_WIDTH)
    grid[1][1] = "@"
    for index in range(DATA_COLUMNS):
        col = DATA_FIRST_COL + index
        chunk = words[SLOTS_PER_LINE * index : SLOTS_PER_LINE * (index + 1)]
        last = index == DATA_COLUMNS - 1
        if index % 2 == 0:
            grid[1][col] = "v"
            grid[83][col] = ">"
            for slot, value in enumerate(chunk):
                head = 3 + 20 * slot
                tail = 21 + 20 * slot
                grid[head][col] = "`"
                grid[tail][col] = "`"
                for offset, digit in enumerate(str(value).rjust(FIELD)):
                    grid[head + 1 + offset][col] = digit
                grid[tail + 1][col] = "s"
        else:
            grid[83][col] = "^"
            grid[1][col] = "H" if last else ">"
            for slot, value in enumerate(chunk):
                head = 81 - 20 * slot
                tail = 63 - 20 * slot
                grid[head][col] = "`"
                grid[tail][col] = "`"
                for offset, digit in enumerate(str(value).rjust(FIELD)):
                    grid[head - 1 - offset][col] = digit
                grid[tail - 1][col] = "s"
    return ["".join(row) for row in grid]


CORE_HEIGHT = 16
CORE_WIDTH = 9


def build_core_room() -> list[str]:
    """Radix-77 splitter: receive a word, emit its little-endian digits.

    ``r`` sits on the northbound entry lane and a ``b``/``d`` pair skips the
    divide chain for the zero padding word.  The chain runs south in one
    column; the ``X`` at its foot loops back while the quotient is positive
    and drops through to the receive lane when it reaches zero.
    """

    grid = _blank_room(CORE_HEIGHT, CORE_WIDTH)
    cells = {
        (1, 2): ">",
        (1, 3): "v",
        (1, 5): "<",
        (2, 3): "v",
        (10, 4): ">",
        (10, 6): "v",
        (11, 4): "d",
        (11, 5): "^",
        (12, 4): "b",
        (13, 2): "^",
        (13, 3): "X",
        (13, 4): "r",
        (14, 2): "@",
        (14, 3): ">",
        (14, 4): "^",
        (14, 6): "<",
    }
    for offset, char in enumerate("M`77`W/W" + "sW"):
        cells[(3 + offset, 3)] = char
    for (row, col), char in cells.items():
        grid[row][col] = char
    return ["".join(row) for row in grid]


MAPPER_HEIGHT = 60
MAPPER_WIDTH = 10
CHAIN_BOUNDS = [35, 42, 60, 64, 89, 91, 113]
CHAIN_GAPS = [4, 2, 3, 1, 1, 6, 1]
TOKEN_BASE_VALUE = 123
EMITTER_START = 20


def _node_cells(bound: int, gap: int | None) -> list[str]:
    """One conditional-add node: BP = bound - A, keep A, branch, then add gap."""

    cells = ["M", "`", *str(bound), "`", "-", "b", "W", "d"]
    if gap is not None:
        cells += ["M", str(gap), "+"]
    return cells


def _emitter_cells(text: str) -> list[str]:
    """Straight-line ASCII emitter: six cells per character, uniform width."""

    cells: list[str] = []
    for character in text:
        cells += ["`", *str(ord(character)).rjust(3), "`", "s"]
    return cells


def build_mapper_room(tokens: list[str]) -> list[str]:
    """Index -> ASCII decoder: two conditional-add runs plus token emitters."""

    if [len(token) for token in tokens] != [5, 4, 2]:
        raise ValueError("mapper layout is tuned to the 5/4/2 token lengths")
    grid = _blank_room(MAPPER_HEIGHT, MAPPER_WIDTH)
    cells: dict[tuple[int, int], str] = {(1, 1): "@", (1, 2): "v", (2, 2): "r"}
    for col in range(3, 9):
        cells[(1, col)] = "<"
    for offset, char in enumerate("M`31`+"):
        cells[(3 + offset, 2)] = char
    for row, bound, gap in ((9, 35, 4), (21, 42, 2), (33, 60, 3), (45, 64, 1)):
        node = _node_cells(bound, gap)
        for offset, char in enumerate(node):
            cells[(row + offset, 2)] = char
        cells[(row + node.index("d"), 1)] = "v"
    cells[(57, 2)] = ">"
    cells[(57, 3)] = "^"
    for row, bound, gap in ((56, 89, 1), (44, 91, 6), (32, 113, 1), (19, 123, None)):
        node = _node_cells(bound, gap)
        for offset, char in enumerate(node):
            cells[(row - offset, 3)] = char
        cells[(row - node.index("d"), 4)] = "v"
    cells[(9, 3)] = ">"
    cells[(9, 6)] = "v"
    for offset, char in enumerate("M`124`W-X"):
        cells[(10 + offset, 6)] = char
    cells[(18, 5)] = "v"
    cells[(18, 7)] = "v"
    for col, token in ((7, tokens[0]), (6, tokens[1]), (5, tokens[2])):
        for offset, char in enumerate(_emitter_cells(token)):
            cells[(EMITTER_START + offset, col)] = char
    for col in (5, 6, 7):
        cells[(57, col)] = ">"
    cells[(57, 8)] = "^"
    cells[(58, 1)] = ">"
    cells[(58, 4)] = ">"
    cells[(58, 7)] = "s"
    cells[(58, 8)] = "^"
    for (row, col), char in cells.items():
        grid[row][col] = char
    return ["".join(row) for row in grid]


OUTPUT_ROOM = ["+-+", "|O|", "+-+"]


def build_history_small() -> str:
    """Assemble the 85x85 machine: DATA -> CORE -> MAPPER -> OUTPUT."""

    _, _, tokens, _, words = build_encoding()
    canvas = Canvas()
    canvas.put(0, 0, build_data_room(words))
    canvas.put(2, 76, build_core_room())
    canvas.put(20, 75, build_mapper_room(tokens))
    canvas.put(82, 81, OUTPUT_ROOM)
    canvas.pipe([(1, 75), (1, 77)])
    canvas.cells[(1, 77)] = "v"  # terminal arrowhead doubles as the bend
    canvas.pipe([(18, 79), (19, 79)])
    canvas.pipe([(80, 82), (81, 82)])
    return canvas.render()
