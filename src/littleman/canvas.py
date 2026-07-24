"""Canvas for assembling .man programs from placed blocks and pipes."""

from __future__ import annotations


class Canvas:
    def __init__(self):
        self.cells = {}  # (row, col) -> char

    def put(self, row: int, col: int, rows: list[str]):
        for dr, line in enumerate(rows):
            for dc, ch in enumerate(line):
                self.cells[(row + dr, col + dc)] = ch

    def pipe(self, waypoints: list[tuple[int, int]]):
        """Draw a pipe along straight segments between waypoints.

        Waypoints include the first and last pipe cell. Arrowheads are
        placed on the first cell, on every bend, and on the last cell;
        straight runs use - or | body glyphs.
        """
        cells = []  # (pos, direction)
        for a, b in zip(waypoints, waypoints[1:]):
            dr = (b[0] > a[0]) - (b[0] < a[0])
            dc = (b[1] > a[1]) - (b[1] < a[1])
            pos = a
            if cells and cells[-1][0] == a:
                cells[-1] = (a, (dr, dc))  # bend: new direction
            else:
                cells.append((a, (dr, dc)))
            while pos != b:
                pos = (pos[0] + dr, pos[1] + dc)
                cells.append((pos, (dr, dc)))
        arrows = {(0, 1): ">", (0, -1): "<", (-1, 0): "^", (1, 0): "v"}
        bodies = {(0, 1): "-", (0, -1): "-", (-1, 0): "|", (1, 0): "|"}
        bend_at = {wp for wp in waypoints[1:-1]}
        for i, (pos, d) in enumerate(cells):
            if i == 0 or i == len(cells) - 1 or pos in bend_at:
                self.cells[pos] = arrows[d]
            else:
                self.cells[pos] = bodies[d]

    def render(self) -> str:
        if not self.cells:
            return ""
        max_r = max(r for r, _ in self.cells)
        max_c = max(c for _, c in self.cells)
        lines = []
        for r in range(max_r + 1):
            line = "".join(
                self.cells.get((r, c), " ") for c in range(max_c + 1)
            )
            lines.append(line.rstrip())
        return "\n".join(lines) + "\n"
