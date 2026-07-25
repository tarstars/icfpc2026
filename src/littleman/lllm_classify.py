"""LLLM CLASSIFY room: semantics and packing, half of the split LOADER.

`claude_17` splits the rejected monolithic LOADER into SCAN | CLASSIFY.
SCAN owns all geometry and feeds this room, in order:

1. 256 cell tokens in canvas order (addr = y*16 + x):
   ``t = char + 256*perimeter + 512*padding`` (padding cells and the ``@``
   cell both carry char 32, an ordinary space);
2. one man token, the canvas address of ``@``;
3. every later input token, forever.

CLASSIFY reproduces the frozen `claude_09` output byte for byte: 64 packed
tokens, the man token forwarded unchanged, then a verbatim relay forever.
It never computes a coordinate; its live state is char, accumulator, count.
"""

from __future__ import annotations

BASE = 1 << 13

SPACE = 0
WALL = 4 | (1 << 4) | (1 << 12)
HEADING = tuple(3 | (2 << 4) | (value << 8) for value in range(4))
DIGIT = tuple(8 | (3 << 4) | (value << 8) for value in range(10))
M_RECORD = 12 | (4 << 4)
ADD_RECORD = 10 | (5 << 4)
SUB_RECORD = 10 | (6 << 4)
X_RECORD = 3 | (7 << 4)
H_RECORD = 3 | (8 << 4)

#: `claude_09`'s glyph table, keyed by ASCII code.  ``@`` never reaches this
#: room -- SCAN reports it as the man token and emits a space in its place.
GLYPH_RECORD = {
    ord(" "): SPACE,
    ord("^"): HEADING[0],
    ord(">"): HEADING[1],
    ord("v"): HEADING[2],
    ord("<"): HEADING[3],
    **{ord(str(value)): DIGIT[value] for value in range(10)},
    ord("M"): M_RECORD,
    ord("+"): ADD_RECORD,
    ord("-"): SUB_RECORD,
    ord("X"): X_RECORD,
    ord("H"): H_RECORD,
}

#: Every record the room can ever emit, in the order the ladder tests them.
RECORDS = sorted(set(GLYPH_RECORD.values()) | {WALL})


# --------------------------------------------------------------- geometry
# Column map of the room's interior.  The classification tree consumes the
# cell token from BP, testing bit ``b`` at column ``TRIE + 2b`` and shifting
# it away at ``TRIE + 2b + 1``; every trie row carries the shift cells, so a
# path executes exactly one shift per bit whatever branch it took.
STATUS_X = 12  # padding test (bit 9)
PERIM_X = 22  # perimeter test (bit 8)
TRIE = 24  # first classification column
LITERAL = 42  # opening backtick of every literal in the room
LIT_DIGITS = 18  # fixed width: any 18-digit literal is 63-bit safe reversed
LIT_END = LITERAL + LIT_DIGITS + 1
DROP = 80  # leaf -> collector highway
RETURN = 82  # boundary -> prologue return highway
WIDTH = 84


def _literal(value: int) -> str:
    """A fixed-width literal cell run, safe to read in either direction."""
    if not 0 <= value < 10**LIT_DIGITS:
        raise ValueError(f"literal out of range: {value}")
    return "`" + str(value).rjust(LIT_DIGITS, "0") + "`"


class _Grid:
    """Sparse character grid with collision detection."""

    def __init__(self) -> None:
        self.cells: dict[tuple[int, int], str] = {}

    def put(self, row: int, col: int, char: str) -> None:
        old = self.cells.get((row, col))
        if old not in (None, char):
            raise ValueError(f"collision at {(row, col)}: {old!r} vs {char!r}")
        self.cells[(row, col)] = char

    def write(self, row: int, col: int, text: str) -> int:
        for offset, char in enumerate(text):
            if char != " ":
                self.put(row, col + offset, char)
        return col + len(text)

    def rows(self, height: int) -> list[str]:
        return [
            "".join(self.cells.get((r, c), " ") for c in range(WIDTH))
            for r in range(height)
        ]


def _trie(keys: dict[int, int], bit: int = 0):
    """A shift-and-test tree over the low bits of the interior glyph."""
    records = set(keys.values())
    if len(records) == 1:
        return ("leaf", records.pop())
    while True:
        even = {k: v for k, v in keys.items() if not (k >> bit) & 1}
        odd = {k: v for k, v in keys.items() if (k >> bit) & 1}
        if even and odd:
            return ("node", bit, _trie(even, bit + 1), _trie(odd, bit + 1))
        bit += 1


def _plan(node, top: int, nodes: list, leaves: list) -> tuple[int, int]:
    """Assign one row per tree node; a subtree owns a contiguous row block.

    The even child sits above its parent and the odd child below, matching
    ``x``'s turn (odd = clockwise = down when heading right).  Because
    subtrees never share rows, a parent's vertical run to a child crosses
    only its own descendants, whose cells all live in deeper columns.
    """
    if node[0] == "leaf":
        leaves.append((top, node[1]))
        return top, top + 1
    _, bit, even, odd = node
    even_row, middle = _plan(even, top, nodes, leaves)
    odd_row, end = _plan(odd, middle + 1, nodes, leaves)
    nodes.append((middle, bit, even_row, odd_row))
    return middle, end


def _leaf_code(grid: _Grid, row: int, entry: int, value: int, *, keep: bool):
    """Enter a leaf, fold its record into the accumulator, leave downward."""
    grid.put(row, entry, ">")
    column = grid.write(row, LITERAL, _literal(value))
    column = grid.write(row, column, "+M" if keep else "+")
    grid.put(row, DROP, "v")


def _phase_block(grid: _Grid, top: int, phase: int) -> int:
    """Emit one record's worth of room: status tests, tree, leaves, exit."""
    keep = phase < 3
    shift = 13 * phase
    nodes: list = []
    leaves: list = []
    root_row, after = _plan(
        _trie({char: record for char, record in GLYPH_RECORD.items()}),
        top,
        nodes,
        leaves,
    )
    for row in range(top, after):
        for bit in range(8):
            grid.put(row, TRIE + 2 * bit + 1, "]")
    for row, bit, even_row, odd_row in nodes:
        grid.put(row, TRIE + 2 * bit, "x")
        grid.put(even_row, TRIE + 2 * bit, ">")
        grid.put(odd_row, TRIE + 2 * bit, ">")
    for row, record in leaves:
        _leaf_code(grid, row, TRIE + 2 * 8, record << shift, keep=keep)
    grid.put(root_row, PERIM_X, ">")
    grid.put(root_row, PERIM_X + 1, "b")

    perim, entry, space, wall, collector = range(after, after + 5)
    grid.write(perim, STATUS_X, ">b" + "]" * 8)
    grid.put(perim, PERIM_X, "x")
    grid.write(entry, 0, ">rb" + "]" * 9)
    grid.put(entry, STATUS_X, "x")
    _leaf_code(grid, space, STATUS_X, SPACE << shift, keep=keep)
    _leaf_code(grid, wall, PERIM_X, WALL << shift, keep=keep)
    grid.put(collector, DROP, "<")
    grid.put(collector, 0, "v")
    return collector + 1


STATE_SHIFT = 52  # the token counter rides above the four packed records
TOKENS = 64


def _build_rows() -> list[str]:
    """The CLASSIFY room's interior, one string per row."""
    grid = _Grid()
    # Prologue, off the loop: seed B with the outstanding token count.
    column = grid.write(0, 0, "@")
    column = grid.write(0, LITERAL, _literal(TOKENS << STATE_SHIFT))
    grid.write(0, column, "M")
    grid.put(0, RETURN, "v")
    grid.put(1, RETURN, "<")
    grid.put(1, 0, "v")

    top = 2
    for phase in range(4):
        top = _phase_block(grid, top, phase)

    # Token boundary: split the state, emit the packed token, count down.
    split, back, reseed, relay, ret = range(top, top + 5)
    grid.write(split, 0, ">M")
    column = grid.write(split, LITERAL, _literal(1 << STATE_SHIFT))
    column = grid.write(split, column, "W/Ws")
    column = grid.write(split, column, "WM1-N")
    grid.put(split, column, "X")
    grid.put(back, column, "<")
    grid.put(split, column + 5, "v")
    grid.put(back, 0, "v")
    grid.write(reseed, 0, ">M")
    column = grid.write(reseed, LITERAL, _literal(1 << STATE_SHIFT))
    grid.write(reseed, column, "*M")
    grid.put(reseed, RETURN, "^")

    # Phase 2 forever: the man token and every later k, relayed verbatim.
    grid.write(relay, DROP - 4, ">rsv")
    grid.put(ret, DROP - 4, "^")
    grid.put(ret, DROP - 1, "<")
    return grid.rows(ret + 1)


def build_classify_room() -> list[str]:
    """The deliverable room: one man, one incoming pipe, one outgoing pipe."""
    interior = _build_rows()
    top = "+" + "-" * WIDTH + "+"
    return [top] + ["|" + row + "|" for row in interior] + [top]


PIPE_ROW = 3  # interior row the two pipes attach to


def build_classify_rig() -> str:
    """Build ``3x3 I -> CLASSIFY -> 3x3 O`` around the exact room."""
    from .canvas import Canvas

    room = build_classify_room()
    canvas = Canvas()
    left = 6
    canvas.put(0, left, room)
    canvas.put(PIPE_ROW - 1, 0, ["+-+", "|I|", "+-+"])
    canvas.pipe([(PIPE_ROW, 3), (PIPE_ROW, left - 1)])
    right = left + len(room[0]) - 1
    out_left = right + 4
    canvas.put(PIPE_ROW - 1, out_left, ["+-+", "|O|", "+-+"])
    canvas.pipe([(PIPE_ROW, right + 1), (PIPE_ROW, out_left - 1)])
    return canvas.render()


def classify_record(token: int) -> int:
    """Classify one SCAN cell token into a 13-bit record."""

    if (token >> 9) & 1:
        return SPACE
    if (token >> 8) & 1:
        return WALL
    return GLYPH_RECORD[token & 0xFF]


def classify_reference(scan_tokens: list[int]) -> list[int]:
    """Return the frozen CLASSIFY output for one complete SCAN stream."""

    records = [classify_record(token) for token in scan_tokens[:256]]
    packed = [
        sum(records[base + offset] << (13 * offset) for offset in range(4))
        for base in range(0, 256, 4)
    ]
    return packed + list(scan_tokens[256:])
