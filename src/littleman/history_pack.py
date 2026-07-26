"""Asymmetric encoder for history-lesson: costly here, trivial in-machine.

`history-lesson` is footprint-scored ONLY, so ticks in the machine are
free. That licenses an encoding whose decoder is *slow* as long as it is
*small*, and lets all the expense sit in Python.

The identity that governs everything: a 19-digit literal occupies 21
cells and carries 63 bits, so

    cells per character = (bits per character) / 3

Every bit of compression is worth exactly a third of a cell. The live
machine spends 5.75 bits/char (73-symbol alphabet plus 3 dictionary
tokens, radix 74) = 5,418 cells of data. Order-0 entropy of the text is
5.05 bits/char, and a dictionary beats that because the text is
structured, not random: years, ``, USA``, ``University of``, and the
month/city vocabulary all repeat.

Sweeping the token count with the table cost included (the token strings
must themselves be stored, packed over the base alphabet):

    tokens   radix   symbols   data   table   total
         3      74      2578   5418      42    5460   <- live
        24      95      2050   4560     231    4791
        48     119      1809   4221     420    4641
        56     127      1761   4116     462    4578   <- optimum
        96     167      1608   4020     672    4692

56 tokens is the minimum. Beyond it the radix grows enough to cost a
symbol per word (floor(63 / log2(radix)) drops), and the table grows
faster than the data shrinks.

Decoding stays trivial *in cells* because ticks are free: to emit token
k, walk the table from the start counting separators until the k-th is
reached -- O(table) ticks, a handful of cells. That asymmetry is the
whole point.
"""

from __future__ import annotations

import collections
import json
import math
import pathlib

LIMIT = 9223372036854775807          # the largest signed-64 literal
REPO = pathlib.Path(__file__).resolve().parent.parent.parent
PROBLEM = REPO / "data" / "small" / "problems" / "history-lesson.json"
TOKEN_COUNT = 56


def expected_text() -> str:
    """The 2,810 characters the machine must emit, from the problem JSON."""
    data = json.loads(PROBLEM.read_text())
    codes = data["publicTestData"][0]["rounds"][0]["out"]
    return "".join(chr(int(code)) for code in codes)


def symbols_per_word(radix: int) -> int:
    """How many radix-`radix` symbols fit in one signed-64 literal."""
    count = 0
    while radix ** (count + 1) <= LIMIT:
        count += 1
    return count


def word_cells(radix: int) -> int:
    """Cells a packed word occupies: its digits plus two backticks."""
    return len(str(radix ** symbols_per_word(radix) - 1)) + 2


SEP = "\x00"                          # marks a token slot while tokenising


def choose_tokens(text: str, count: int = TOKEN_COUNT) -> list[str]:
    """Greedily pick the substrings that save the most symbols.

    Expensive on purpose (this is the side that may be slow): each round
    scores every substring of length 2..13 by `occurrences * (len - 1)`,
    which is exactly the number of symbols that substitution removes.
    """
    tokens: list[str] = []
    working = text
    for _ in range(count):
        best = None
        for length in range(2, 14):
            counts = collections.Counter(
                working[i:i + length] for i in range(len(working) - length + 1))
            for candidate, hits in counts.items():
                if hits < 2 or SEP in candidate:
                    continue
                if any(candidate in t or t in candidate for t in tokens):
                    continue
                gain = hits * (length - 1)
                if best is None or gain > best[0]:
                    best = (gain, candidate)
        if best is None:
            break
        tokens.append(best[1])
        working = working.replace(best[1], SEP)
    return tokens


def tokenise(text: str, tokens: list[str]) -> list[int]:
    """Text -> symbol ids. Ids 0..A-1 are literal characters, then tokens.

    Longest-token-first at each position, so the result is deterministic
    and independent of the order `choose_tokens` returned.
    """
    alphabet = sorted(set(text))
    index = {ch: i for i, ch in enumerate(alphabet)}
    ranked = sorted(tokens, key=len, reverse=True)
    token_id = {t: len(alphabet) + tokens.index(t) for t in tokens}
    out: list[int] = []
    i = 0
    while i < len(text):
        for token in ranked:
            if text.startswith(token, i):
                out.append(token_id[token])
                i += len(token)
                break
        else:
            out.append(index[text[i]])
            i += 1
    return out


def untokenise(ids: list[int], alphabet: list[str], tokens: list[str]) -> str:
    """The in-machine operation, in Python: id -> character or token text."""
    pieces = []
    for value in ids:
        pieces.append(alphabet[value] if value < len(alphabet)
                      else tokens[value - len(alphabet)])
    return "".join(pieces)


def pack(ids: list[int], radix: int) -> list[int]:
    """Pack symbol ids into signed-64 words, most significant first."""
    per = symbols_per_word(radix)
    words = []
    for start in range(0, len(ids), per):
        chunk = ids[start:start + per]
        value = 0
        for symbol in chunk:
            value = value * radix + symbol
        # pad the final short chunk so unpacking knows the width
        for _ in range(per - len(chunk)):
            value = value * radix
        words.append(value)
    return words


def unpack(words: list[int], radix: int, count: int) -> list[int]:
    """The in-machine loop, in Python: repeated divmod by the radix."""
    per = symbols_per_word(radix)
    out: list[int] = []
    for word in words:
        digits = []
        for _ in range(per):
            word, rest = divmod(word, radix)
            digits.append(rest)
        out.extend(reversed(digits))
    return out[:count]


def build(text: str | None = None, count: int = TOKEN_COUNT) -> dict:
    """The whole encoding, with its measured cell cost."""
    text = expected_text() if text is None else text
    tokens = choose_tokens(text, count)
    alphabet = sorted(set(text))
    radix = len(alphabet) + len(tokens)
    ids = tokenise(text, tokens)
    words = pack(ids, radix)
    table_text = SEP.join(tokens)
    table_alpha = sorted(set(table_text))
    table_radix = len(table_alpha)
    table_index = {ch: i for i, ch in enumerate(table_alpha)}
    table_words = pack([table_index[ch] for ch in table_text], table_radix)
    return {
        "text": text, "tokens": tokens, "alphabet": alphabet, "radix": radix,
        "ids": ids, "words": words,
        "table_text": table_text, "table_alpha": table_alpha,
        "table_radix": table_radix, "table_words": table_words,
        "data_cells": len(words) * word_cells(radix),
        "table_cells": len(table_words) * word_cells(table_radix),
    }
