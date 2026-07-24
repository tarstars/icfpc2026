"""Packet Reassembly using a scanned ring of ``(sequence, value)`` pairs.

The controller keeps the next expected sequence number in B.  Buffered
packets circulate as two consecutive values in a pipe ring.  After accepting
one packet, the controller scans every pair:

* ``seq - expected == 0``: consume the value, increment B, emit it, and scan
  again so a single arrival can drain a whole contiguous prefix;
* ``seq - expected > 0``: restore and requeue the sequence and its value;
* no match in the ring: block on the next input packet.

The input-side delay check copies ``seq - expected`` to BP and decrements it
15 times.  BP remains positive exactly when the delay is at least 16.
"""

from .canvas import Canvas


def build_pump() -> list[str]:
    """Build the single stateful controller room."""
    width, height = 34, 24
    grid = [[" "] * (width + 2) for _ in range(height + 2)]
    for col in range(width + 2):
        grid[0][col] = grid[height + 1][col] = "-"
    for row in range(height + 2):
        grid[row][0] = grid[row][width + 1] = "|"
    for row, col in (
        (0, 0),
        (0, width + 1),
        (height + 1, 0),
        (height + 1, width + 1),
    ):
        grid[row][col] = "+"

    cells: dict[tuple[int, int], str] = {
        # Start: discard n, then merge into the per-packet input lane.
        (1, 2): "@",
        (1, 3): "r",
        (1, 4): "v",
        (2, 4): "v",
        (2, 10): "<",
        (3, 1): ">",
        (3, 4): ">",
        # Read seq, compute delay against B=expected, and copy delay to BP.
        (3, 5): "r",
        (3, 6): "-",
        (3, 7): "b",
        # Fifteen decrements make BP > 0 exactly for delay >= 16.
        **{(3, col): "m" for col in range(8, 23)},
        # Positive turns south to the loss lane; zero continues to enqueue.
        (3, 23): "d",
        (3, 24): "+",
        (3, 25): "s",
        (3, 26): "r",
        (3, 27): "s",
        (3, 32): "v",
        # Long settling corridor before q counts the parked ring values.
        (5, 32): "<",
        (5, 3): "v",
        (7, 3): ">",
        (7, 32): "v",
        (9, 32): "<",
        (9, 3): "v",
        (11, 3): ">",
        (11, 32): "v",
        (15, 32): "<",
        # q==0 continues west to input. q>0 turns north into the scan.
        (15, 29): "q",
        (15, 28): "d",
        (15, 1): "^",
        (14, 28): "]",
        (13, 28): "<",
        # Receive seq and branch on seq-expected.  Negative is impossible.
        (13, 27): "r",
        (13, 26): "-",
        (13, 25): "X",
        # Match lane: increment expected in B, receive val, and emit it.
        (13, 24): "+",
        (13, 23): "M",
        (13, 22): "1",
        (13, 21): "+",
        (13, 20): "M",
        (13, 19): "r",
        (13, 6): "v",
        (18, 6): "<",
        (18, 2): "s",
        (18, 1): "v",
        # After output, settle any requeued prefix and scan again.
        (22, 1): ">",
        (22, 32): "^",
        (20, 32): "<",
        (20, 8): "^",
        (16, 8): ">",
        (16, 32): "^",
        # Nonmatch lane: restore seq, requeue the pair, and count it.
        (10, 25): ">",
        (10, 26): "+",
        (10, 27): "s",
        (10, 28): "r",
        (10, 29): "s",
        (10, 30): "m",
        # More pairs turn south back into the scanner.
        (10, 31): "d",
        (13, 31): "<",
        # An exhausted scan returns around the outside to the input merge.
        (10, 34): "v",
        (24, 34): "<",
        (24, 10): "^",
        # Loss lane: output -1 and halt after the output pipe flushes.
        (17, 23): "<",
        (17, 5): "1",
        (17, 4): "N",
        (17, 3): "s",
        (17, 2): "H",
    }
    for (row, col), char in cells.items():
        grid[row][col] = char
    return ["".join(row) for row in grid]


RELAY = [
    "+---+",
    "| @v|",
    "|>sv|",
    "|^r<|",
    "+---+",
]


def build_tcp() -> str:
    """Render the complete Packet Reassembly program."""
    canvas = Canvas()
    canvas.put(0, 9, ["+-+", "|I|", "+-+"])
    canvas.put(5, 5, build_pump())
    canvas.put(34, 6, ["+-+", "|O|", "+-+"])
    canvas.put(34, 36, RELAY)

    # Input -> pump top, attached at relative column 5.
    canvas.pipe([(3, 10), (4, 10)])
    # Pump bottom, relative column 2 -> output.
    canvas.pipe([(31, 7), (33, 7)])
    # Pump ring-out (bottom relative column 27) -> relay left.
    canvas.pipe([(31, 32), (37, 32), (37, 35)])
    # Relay right -> a long parking pipe at pump bottom relative column 14.
    # Its capacity must exceed the maximum 32 values (16 packet pairs), since
    # q can count only values parked in this one incoming pipe.
    canvas.pipe(
        [
            (36, 41),
            (36, 42),
            (40, 42),
            (40, 19),
            (31, 19),
        ]
    )
    return canvas.render()
