"""Two-word STATION relay for the exact ``memory_12`` packed machine.

READ constants are positive, WRITE masks are negative, and initialization
keeps B at zero.  The shared pair loop therefore dispatches its continuation
from B's sign without spending another register.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

PARENT_SHA256 = "e63c3e20e824dec33861b04305a7785efb2912b3db761bc7c46b8d78203b592e"
CANDIDATE_SHA256 = "032b067b8a506332ccf8a1a775228f64abf49aafe32ea10d2966f8aa25d0ae9e"

# Sparse local coordinates inside the extended 12x17 STATION interior.
STATION_CELLS = {
    1: {
        1: "@",
        2: "`",
        3: "3",
        4: "3",
        5: "`",
        6: "b",
        7: "0",
        15: ">",
        16: "s",
        17: "v",
    },
    2: {
        1: ">",
        2: "r",
        3: "X",
        4: "r",
        5: "b",
        6: "r",
        7: "M",
        10: "r",
        11: "v",
        15: "^",
        16: "m",
        17: "d",
    },
    3: {
        3: ">",
        4: "r",
        5: "b",
        6: "r",
        7: "M",
        10: "v",
        11: "s",
        12: ">",
        13: "v",
        15: "v",
        16: "<",
    },
    4: {10: ">", 11: ">", 12: "x", 15: "r", 16: "m"},
    5: {12: "r", 15: "s", 16: "s"},
    6: {12: "s", 13: ">", 14: "]", 15: "v", 16: "r"},
    7: {12: ">", 13: "^", 15: "a", 16: "^"},
    8: {1: "^", 15: "W", 17: "<"},
    9: {
        1: "^",
        5: "s",
        6: "}",
        7: "W",
        8: "`",
        9: "3",
        10: "4",
        11: "`",
        12: "M",
        13: "{",
        14: "W",
        15: "X",
        16: "W",
        17: "v",
    },
    10: {1: "^", 6: "v", 7: "|", 8: "r", 12: "W", 13: "M", 14: "&", 16: "r", 17: "<"},
    11: {1: "^", 6: ">", 14: "s", 15: "v"},
    12: {1: "^", 15: "<"},
}


def apply_memory12_unroll(parent: str) -> str:
    """Extend and replace only the STATION in the exact parent."""

    digest = hashlib.sha256(parent.encode()).hexdigest()
    if digest != PARENT_SHA256:
        raise ValueError(f"unexpected memory_12 parent SHA-256: {digest}")

    lines = [list(line) for line in parent.splitlines()]
    width = max(map(len, lines))
    lines.extend([] for _ in range(30 - len(lines)))
    for line in lines:
        line.extend(" " * (width - len(line)))

    # Old interior is global rows 17..27, columns 4..20.  Row 28 was
    # STATION's bottom wall; it becomes the twelfth interior row.
    for row in range(17, 29):
        for column in range(4, 21):
            lines[row][column] = " "
    for column in range(3, 22):
        lines[28][column] = " "
        lines[29][column] = "-"
    lines[28][3] = lines[28][21] = "|"
    lines[29][3] = lines[29][21] = "+"

    for local_row, cells in STATION_CELLS.items():
        for local_column, glyph in cells.items():
            lines[16 + local_row][3 + local_column] = glyph

    candidate = "\n".join("".join(line).rstrip() for line in lines).rstrip() + "\n"
    digest = hashlib.sha256(candidate.encode()).hexdigest()
    if CANDIDATE_SHA256 and digest != CANDIDATE_SHA256:
        raise AssertionError(f"memory_13 SHA-256 drifted: {digest}")
    return candidate


def build_memory_unrolled(parent: str | None = None) -> str:
    if parent is None:
        repo = Path(__file__).resolve().parents[2]
        parent = (repo / "submissions/memory/memory_12.man").read_text()
    return apply_memory12_unroll(parent)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        raise SystemExit("usage: python -m littleman.memory_unrolled OUTPUT")
    Path(args[0]).write_text(build_memory_unrolled())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
