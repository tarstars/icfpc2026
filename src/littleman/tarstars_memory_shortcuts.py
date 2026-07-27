"""Two safe WRITE-path shortcuts for the exact ``memory_13`` machine."""

from __future__ import annotations

import hashlib
from pathlib import Path

PARENT_SHA256 = "032b067b8a506332ccf8a1a775228f64abf49aafe32ea10d2966f8aa25d0ae9e"
CANDIDATE_SHA256 = "90ab2f895d50443356fdcbb1e4ebeb7f484d0c6fd517566906cdfcf4644c8d31"

# Coordinates are local to STATION's interior.  Each replacement is guarded
# by its exact parent glyph so the transform fails closed on lineage drift.
TARSTARS_EDITS = (
    (10, 6, "v", " "),
    (10, 7, "|", "v"),
    (10, 8, "r", "|"),
    (10, 9, " ", "r"),
    (11, 6, ">", " "),
    (11, 7, " ", ">"),
    (11, 10, " ", "s"),
    (11, 11, " ", "v"),
    (11, 14, "s", " "),
    (11, 15, "v", " "),
    (12, 11, " ", "<"),
    (12, 15, "<", " "),
)


def apply_tarstars_memory_shortcuts(parent: str) -> str:
    """Move WRITE's command receive and ring send to their binding limits."""

    digest = hashlib.sha256(parent.encode()).hexdigest()
    if digest != PARENT_SHA256:
        raise ValueError(f"unexpected memory_13 parent SHA-256: {digest}")

    lines = [list(line) for line in parent.splitlines()]
    width = max(map(len, lines))
    for line in lines:
        line.extend(" " * (width - len(line)))

    for local_row, local_column, expected, replacement in TARSTARS_EDITS:
        row = 16 + local_row
        column = 3 + local_column
        actual = lines[row][column]
        if actual != expected:
            raise ValueError(
                f"unexpected STATION glyph at {(local_row, local_column)}: "
                f"{actual!r}, expected {expected!r}"
            )
        lines[row][column] = replacement

    candidate = "\n".join("".join(line).rstrip() for line in lines).rstrip() + "\n"
    digest = hashlib.sha256(candidate.encode()).hexdigest()
    if digest != CANDIDATE_SHA256:
        raise AssertionError(f"Memory shortcut SHA-256 drifted: {digest}")
    return candidate


def build_tarstars_memory_shortcuts(parent: str | None = None) -> str:
    if parent is None:
        repo = Path(__file__).resolve().parents[2]
        parent = (repo / "submissions/memory/memory_13.man").read_text()
    return apply_tarstars_memory_shortcuts(parent)
