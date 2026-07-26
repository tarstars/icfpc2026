from pathlib import Path

from littleman.canvas import Canvas

H = W = 22
cells: dict[tuple[int, int], str] = {}
cells[(2, 0)] = "@"

# A linear `Y` chain leaves one worker at every split. The right copy retains
# the parent's creation-order slot and continues; left copies become workers
# 0..15 in creation order.
for i in range(16):
    yr, yc = 2 + i, 2 + i
    cells[(yr, yc)] = "Y"
    cells[(yr - 1, yc)] = ">"
    cells[(yr - 1, yc + 1)] = "r"
    if i < 15:
        cells[(yr + 1, yc)] = ">"

# Final continuation is creation-order slot zero. It consumes the length token.
cells[(18, 17)] = "<"
cells[(18, 16)] = "r"
cells[(18, 15)] = "H"

# Workers enter this column simultaneously, then form a southbound train.
for row in range(1, 18):
    cells[(row, 20)] = "v"
cells[(18, 20)] = "s"
cells[(19, 20)] = "H"

room = ["+" + "-" * W + "+"]
for row in range(H):
    room.append("|" + "".join(cells.get((row, col), " ") for col in range(W)) + "|")
room.append("+" + "-" * W + "+")
io = lambda char: ["+-+", f"|{char}|", "+-+"]

canvas = Canvas()
canvas.put(0, 0, room)
canvas.put(18, 26, io("O"))
canvas.put(27, 55, io("I"))
canvas.pipe([(19, 24), (19, 25)])
# Deliberately long startup pipe: all 16 workers exist before the length token
# and values reach the room. This is a proof artifact, not compact geometry.
canvas.pipe([(26, 56), (25, 56), (25, 17), (24, 17)])

text = canvas.render()
Path(__file__).with_name("reverse_y_one_round.man").write_text(text)
print(text, end="")
