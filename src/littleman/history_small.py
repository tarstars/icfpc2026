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
# Machine layout plan (encoder above is done and verified; rooms still to build)
# ---------------------------------------------------------------------------
#
# Footprint arithmetic (all measured, see build_encoding()):
#   FIELD=17 -> data line = 4*(17+2) + 5 s/turn cells = 83 interior, 85 total.
#   RADIX=77 -> 9 symbols per word (77**9 = 9.5e16 < 1e17).  288 words.
#   Vertical serpentine: interior height 4*(17+3)+3 = 83, room 85 tall;
#   72 data columns + 1 entry column + 2 walls = 75 wide.
#   Leftover is a TALL strip (S-76 wide, S tall) instead of a short wide band,
#   which is the only shape that fits a stack of decoder rooms.
#   S = 85 needs a 9-wide interior strip; S = 87 gives 11.
#
# Four rooms, three pipes, no relays and no pipe-nearest ambiguity (every room
# has at most one incoming and one outgoing pipe):
#
#   DATA --> CORE --> MAPPER --> OUTPUT
#
# The trick that removes every relay room: to get a constant into B while
# keeping the accumulator, use  M , <literal> , W  --  M copies A into B, the
# literal overwrites A, and W swaps them back.  Three cells, no pipe.
#
# CORE  (radix split):  r ; X ; if A>0: M `77` W / W s W  and loop back to X;
#                       if A==0: loop back to r.
# MAPPER (index -> ASCII, one man, one chain):
#   r ; M `74` W - ; X
#     A >= 0 : token t; a second X on (A-1) selects one of three straight-line
#              emitters, each a row of  `nnn` s  pairs writing ASCII directly.
#     A <  0 : M `72` W + rebases to (index - I_1), then the gap chain:
#              node i:  X ; if A<0 leaf i (M `k` W + s), else M `d` W - and on
#              to node i+1.  8 pieces -> 7 nodes, 8 leaves.
# OUTPUT: 3x3 room with O.
