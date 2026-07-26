"""Geometry-only hot-path transforms for the recovered ``memory_11``.

The counted 29-square program was recovered from the contest editor rather
than from a generator.  Treat it as an immutable parent and apply explicit,
guarded cell substitutions: this keeps the release reproducible without
pretending that the earlier hand compaction can be regenerated.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

PARENT_SHA256 = "c9e2dea84fa3b6d809cfe85a02abfcf7e614349d5488432e776fdd256fbb41a4"
CANDIDATE_SHA256 = "e63c3e20e824dec33861b04305a7785efb2912b3db761bc7c46b8d78203b592e"

# Zero-based canvas coordinates: (row, column, expected parent glyph, new glyph).
# The first pair advances READ's send/return by one cell.  The next three add
# the earliest ring-bound WRITE send and a short return.  The final arrow lets
# both WRITE and the one-time seed exit rejoin the main loop one column sooner.
PATCHES = (
    (21, 5, "s", "^"),
    (21, 6, " ", "s"),
    (26, 13, " ", "s"),
    (26, 14, " ", "v"),
    (27, 14, " ", "<"),
    (27, 5, " ", "^"),
)


def apply_memory11_hotpath(parent: str) -> str:
    """Return ``memory_12`` after verifying and patching its exact parent."""

    digest = hashlib.sha256(parent.encode()).hexdigest()
    if digest != PARENT_SHA256:
        raise ValueError(f"unexpected memory_11 parent SHA-256: {digest}")

    lines = [list(line) for line in parent.splitlines()]
    for row, column, expected, replacement in PATCHES:
        actual = lines[row][column]
        if actual != expected:
            raise ValueError(
                f"memory_11 cell {(row, column)} is {actual!r}, expected {expected!r}"
            )
        lines[row][column] = replacement
    candidate = "\n".join("".join(line) for line in lines) + "\n"

    digest = hashlib.sha256(candidate.encode()).hexdigest()
    if digest != CANDIDATE_SHA256:
        raise AssertionError(f"memory_12 SHA-256 drifted: {digest}")
    return candidate


def build_memory_hotpath(parent: str | None = None) -> str:
    """Build the candidate, loading the tracked parent when omitted."""

    if parent is None:
        repo = Path(__file__).resolve().parents[2]
        parent = (repo / "submissions/memory/memory_11.man").read_text()
    return apply_memory11_hotpath(parent)
