"""Build the compact multi-round fresh-farm Reverse candidate.

The controller reads n, stores it in BP, and repeatedly uses a two-Y cycle to
spawn exactly n workers. Worker BP values are n..1. Each worker reads one
input value, enters a seven-tick countdown stage once per BP unit, then sends.
Later values have smaller BP and therefore emit earlier. Every worker halts;
the controller returns to its U/r entry for the next round.
"""
from pathlib import Path
from littleman.canvas import Canvas

ROOM_H, ROOM_W = 16, 18
cells: dict[tuple[int, int], str] = {}


def put(row: int, col: int, char: str) -> None:
    old = cells.get((row, col))
    assert old in (None, char, " "), ((row, col), old, char)
    cells[(row, col)] = char


# Seven-tick countdown stages. Worker arrivals are 4/6 ticks apart, both
# strictly below seven, so a later worker always advances through the stage
# chain faster than every earlier worker.
for row in range(16):
    if row % 2 == 0:
        for col, char in ((3, "m"), (2, "a"), (1, "s"), (0, "H")):
            put(row, col, char)
        if row:
            put(row, 8, "<")
    else:
        for col, char in ((7, "m"), (8, "d"), (9, "s"), (10, "H")):
            put(row, col, char)
        put(row, 2, ">")

# Alternating two-Y split cycle. Continuations decrement BP before returning;
# when BP reaches zero they leave the cycle and return to the round controller.
for pos, char in {
    (5, 16): "Y", (6, 16): "m", (7, 16): "d", (7, 15): "<",
    (7, 14): "Y", (6, 14): "^", (5, 14): "m", (4, 14): "d",
    (4, 15): "v", (5, 15): ">", (4, 16): " ", (3, 16): "U",
    (8, 14): " ", (9, 14): "U",
}.items():
    put(*pos, char)

# Top and bottom workers merge into the countdown pipeline.
put(3, 14, "<")
put(3, 13, "a")
put(4, 13, "<")
put(4, 12, "^")
put(0, 12, "<")
put(9, 13, "^")
put(5, 13, "<")
put(5, 12, "^")

# Initial and per-round controller. U receives n and turns away from the input
# pipe; b stores n as the split count.
for pos, char in {
    (14, 17): "U", (14, 16): "@", (14, 15): "b", (14, 14): "v",
    (15, 14): ">", (15, 15): "^",
}.items():
    put(*pos, char)

# Both zero exits return to U for the next round.
put(3, 11, "v")
put(13, 11, ">")
put(13, 17, "v")
put(8, 16, ">")
put(8, 17, "v")

room = ["+" + "-" * ROOM_W + "+"]
for row in range(ROOM_H):
    room.append("|" + "".join(cells.get((row, col), " ") for col in range(ROOM_W)) + "|")
room.append("+" + "-" * ROOM_W + "+")
io = lambda char: ["+-+", f"|{char}|", "+-+"]

canvas = Canvas()
canvas.put(5, 0, room)
canvas.put(0, 2, io("O"))
canvas.pipe([(4, 3), (3, 3)])
# The I room and its pipe fit into the three-column east strip, making the
# entire program 23x23. The input pipe has 13 cells, enough for the controller
# and worker consumption schedule on all n<=16 rounds.
canvas.put(0, 20, io("I"))
canvas.pipe([(3, 21), (14, 21), (14, 20)])

text = canvas.render()
Path(__file__).with_name("reverse_fresh_23.man").write_text(text)
print(text, end="")
