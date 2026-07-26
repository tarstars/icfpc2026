"""Packed asymmetric archive and compact-machine components for History.

The expensive dictionary search and exact parse live in :mod:`history_pack`.
This module lowers that result to two streams suited to a small machine:

* 1,755 character-or-token indices, nine per radix-128 word;
* one cyclic character/token table, nine radix-94 codes per word.

Codes 1..71 identify the sorted character alphabet and codes 72..127 identify
dictionary entries.  The table stores the alphabet once, followed by the 56
longer entries.  This avoids a branch-heavy rank-to-ASCII mapper without
duplicating the 71 single-character entry separators.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import history_pack
from .gradebook import Block, Fsm, compile_fsm

MAIN_RADIX = 128
MAIN_PER_WORD = 9
TABLE_RADIX = 94
TABLE_PER_WORD = 9
TABLE_SEPARATOR = 92
TABLE_BOUNDARY = 93


@dataclass(frozen=True)
class Archive:
    text: str
    entries: tuple[str, ...]
    main_codes: tuple[int, ...]
    main_words: tuple[int, ...]
    table_codes: tuple[int, ...]
    table_words: tuple[int, ...]


def _pack_little_endian(codes: list[int], radix: int, width: int) -> list[int]:
    """Find the fewest parser-safe little-endian decimal literals.

    The language validates every literal in both walking directions.  Thus a
    forward-safe 19-digit integer is still illegal when its reversed decimal
    digits exceed ``2**63 - 1``.  Chunk boundaries are selected by exact DP,
    and a zero high digit is forbidden because quotient-until-zero decoding
    would silently shorten that chunk.
    """

    limit = (1 << 63) - 1
    count = len(codes)
    infinity = count + 1
    best = [infinity] * (count + 1)
    step = [0] * (count + 1)
    best[count] = 0
    for start in range(count - 1, -1, -1):
        value = 0
        multiplier = 1
        for length in range(1, width + 1):
            if start + length > count:
                break
            code = codes[start + length - 1]
            if not 0 <= code < radix:
                raise ValueError(f"code {code} does not fit radix {radix}")
            value += code * multiplier
            multiplier *= radix
            if value > limit:
                break
            if code == 0 or int(str(value)[::-1]) > limit:
                continue
            if 1 + best[start + length] < best[start]:
                best[start] = 1 + best[start + length]
                step[start] = length

    if best[0] == infinity:
        raise ValueError("no parser-safe packing exists")
    words: list[int] = []
    position = 0
    while position < count:
        length = step[position]
        words.append(
            sum(codes[position + offset] * radix**offset for offset in range(length))
        )
        position += length
    return words


def _unpack_nonzero_high(words: tuple[int, ...], radix: int) -> list[int]:
    """Repeated-divmod decoder used by the machine's two splitter rooms."""

    codes: list[int] = []
    for word in words:
        while word:
            word, code = divmod(word, radix)
            codes.append(code)
    return codes


def build_archive() -> Archive:
    """Build the deterministic archive lowered for a quotient-until-zero core."""

    packed = history_pack.build()
    entries = [*packed["alphabet"], *packed["tokens"]]
    # Zero is reserved as the quotient terminator, so every archive id is
    # shifted by one.  128**9 == 2**63; the exact safe-packing DP chooses
    # shorter chunks whenever a particular nine-code word would overflow.
    main_codes = [code + 1 for code in packed["ids"]]
    main_words = _pack_little_endian(main_codes, MAIN_RADIX, MAIN_PER_WORD)

    table_codes = [
        TABLE_BOUNDARY,
        *(ord(char) - 31 for char in packed["alphabet"]),
        TABLE_SEPARATOR,
    ]
    for entry in packed["tokens"]:
        table_codes.extend(ord(char) - 31 for char in entry)
        table_codes.append(TABLE_SEPARATOR)
    table_words = _pack_little_endian(table_codes, TABLE_RADIX, TABLE_PER_WORD)

    return Archive(
        packed["text"],
        tuple(entries),
        tuple(main_codes),
        tuple(main_words),
        tuple(table_codes),
        tuple(table_words),
    )


def reference_decode(archive: Archive) -> str:
    """Reference the intended machine operation, including cyclic-table scan."""

    main = _unpack_nonzero_high(archive.main_words, MAIN_RADIX)
    table = _unpack_nonzero_high(archive.table_words, TABLE_RADIX)
    boundary = table.index(TABLE_BOUNDARY)
    alphabet_end = table.index(TABLE_SEPARATOR, boundary + 1)
    alphabet = [chr(code + 31) for code in table[boundary + 1 : alphabet_end]]
    token_expansions: list[str] = []
    current: list[str] = []
    for code in table[alphabet_end + 1 :]:
        if code == TABLE_SEPARATOR:
            token_expansions.append("".join(current))
            current = []
        else:
            current.append(chr(code + 31))
    return "".join(
        alphabet[code - 1] if code <= 71 else token_expansions[code - 72]
        for code in main
    )


def _blank_room(height: int, width: int) -> list[list[str]]:
    edge = ["+", *(["-"] * (width - 2)), "+"]
    return [
        edge.copy(),
        *[["|", *([" "] * (width - 2)), "|"] for _ in range(height - 2)],
        edge.copy(),
    ]


def build_word_room(
    words: tuple[int, ...],
    *,
    field: int,
    rows: int,
    cyclic: bool,
) -> list[str]:
    """Render three fixed-width literals per horizontal serpentine row."""

    slots = 3
    padded = [*words, *([0] * (slots * rows - len(words)))]
    if len(padded) != slots * rows:
        raise ValueError("word room dimensions do not match the word count")
    stride = field + 3
    cyclic_shift = int(cyclic)
    width = slots * stride + 5 + cyclic_shift
    grid = _blank_room(rows + 2, width)
    starts = [3 + cyclic_shift + slot * stride for slot in range(slots)]
    right_turn = starts[-1] + field + 3

    for offset in range(rows):
        row = offset + 1
        chunk = padded[slots * offset : slots * (offset + 1)]
        east = offset % 2 == 0
        last = offset == rows - 1
        grid[row][1] = "@" if offset == 0 else (">" if east else ("H" if last else "v"))
        grid[row][right_turn] = ("H" if last else "v") if east else "<"
        ordered = chunk if east else list(reversed(chunk))
        for slot, value in enumerate(ordered):
            start = starts[slot]
            end = start + field + 1
            grid[row][start] = "`"
            grid[row][end] = "`"
            digits = str(value)
            if len(digits) > field:
                raise ValueError(f"{value} exceeds the {field}-digit field")
            if east:
                grid[row][start + 1 : end] = digits.rjust(field)
                grid[row][end + 1] = "s"
            else:
                walked = digits.rjust(field)
                for index, character in enumerate(walked):
                    grid[row][end - 1 - index] = character
                grid[row][start - 1] = "s"

    if cyclic:
        if rows % 2:
            raise ValueError("cyclic serpentine needs an even number of rows")
        grid[rows][1] = " "
        grid[rows][2] = "^"
        grid[1][2] = ">"
        grid[1][1] = "@"
    return ["".join(row) for row in grid]


def build_splitter_room(radix: int) -> list[str]:
    """Receive a word and emit its little-endian digits until quotient zero."""

    code = f"M`{radix}`W/WsW"
    end = 3 + len(code) - 1
    grid = _blank_room(end + 4, 8)
    cells = {
        (1, 2): ">",
        (1, 3): "v",
        (1, 5): "<",
        (2, 3): "v",
        (end - 2, 4): ">",
        (end - 2, 6): "v",
        (end - 1, 4): "d",
        (end - 1, 5): "^",
        (end, 4): "b",
        (end + 1, 2): "^",
        (end + 1, 3): "X",
        (end + 1, 4): "r",
        (end + 2, 2): "@",
        (end + 2, 3): ">",
        (end + 2, 4): "^",
        (end + 2, 6): "<",
    }
    for offset, char in enumerate(code):
        grid[3 + offset][3] = char
    for (row, col), char in cells.items():
        grid[row][col] = char
    return ["".join(row) for row in grid]


def _dispatcher_fsm() -> Fsm:
    """Control graph for one complete expansion before reading the next id."""

    fsm = Fsm()
    fsm.go("boundary_const", "logic", "@`93`M", "sync")
    fsm.sign(
        "sync",
        "table",
        "r-",
        negative="sync",
        zero="main",
        positive="sync",
    )
    fsm.sign(
        "main",
        "main",
        "rM`72`W-",
        negative="char_setup",
        zero="token",
        positive="token",
    )
    fsm.go("char_setup", "logic", "+b", "char_read")
    fsm.go("char_read", "table", "rm", "char_choose")
    fsm.bp(
        "char_choose",
        "logic",
        ".",
        zero="char_send",
        positive="char_read",
    )
    fsm.go("char_send", "output", "M`31`+s", "boundary_const")
    fsm.go("token", "logic", "b", "separator_const")
    fsm.go("separator_const", "logic", "`92`M", "skip_char_prefix")
    fsm.sign(
        "skip_char_prefix",
        "table",
        "r-",
        negative="skip_char_prefix",
        zero="choose",
        positive="boundary_const",
    )
    fsm.bp("choose", "logic", ".", zero="emit", positive="skip")
    fsm.sign(
        "skip",
        "table",
        "r-",
        negative="skip",
        zero="skip_dec",
        positive="boundary_const",
    )
    fsm.bp("skip_dec", "logic", "m", zero="emit", positive="skip")
    fsm.sign(
        "emit",
        "table",
        "r-",
        negative="ascii_base",
        zero="boundary_const",
        positive="boundary_const",
    )
    fsm.go("ascii_base", "output", "+M`31`+s", "emit_separator_const")
    # ASCII conversion uses M, so B no longer contains TABLE_SEPARATOR.
    fsm.go("emit_separator_const", "logic", "`92`M", "emit")
    return fsm


def build_dispatcher_room() -> list[str]:
    """Compile the verified expansion-table protocol before hand compaction."""

    fsm = _dispatcher_fsm()
    offsets = {"logic": 0, "main": 16, "table": 32, "output": 48}
    literal_offsets: dict[str, int] = {}
    cursor = 80
    rewritten = Fsm()
    for block in fsm.blocks:
        if "`" in block.code:
            key = block.zone if block.zone.startswith("literal_") else block.code
            zone = literal_offsets.setdefault(key, cursor)
            if zone == cursor:
                cursor += len(block.code) + 3
            name = f"safe_{zone}"
            offsets[name] = zone
            block = Block(block.name, name, block.code, block.kind, block.targets)
        rewritten.blocks.append(block)
    return compile_fsm(rewritten, offsets, right_padding=2).rows
