"""Judge-proven blank-line squeeze for the live ``lllm_03`` machine."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

PARENT_SHA256 = "2e2b99e00d03904731247e280c87c6f3b9c7a014126f03d1177fa2f0a88543e6"
CANDIDATE_SHA256 = "92c9ac64c2c1e7a2550a0e717e0e27e40dd10947eb2c2570a0958d512724f218"
DROPPED_ROWS = (310,)
DROPPED_COLUMNS = (74, 75, 76, 78)


def apply_lllm_squeeze(parent: str) -> str:
    """Delete the exact globally blank row and corridor columns."""

    digest = hashlib.sha256(parent.encode()).hexdigest()
    if digest != PARENT_SHA256:
        raise ValueError(f"unexpected lllm_03 parent SHA-256: {digest}")

    source = parent.rstrip("\n").splitlines()
    width = max(map(len, source))
    grid = [line.ljust(width) for line in source]
    for row in DROPPED_ROWS:
        if any(char not in " |" for char in grid[row]):
            raise AssertionError(f"LLLM row {row} is no longer mechanically blank")
    for column in DROPPED_COLUMNS:
        if any(line[column] not in " -" for line in grid):
            raise AssertionError(
                f"LLLM column {column} is no longer mechanically blank"
            )

    dropped_rows = set(DROPPED_ROWS)
    dropped_columns = set(DROPPED_COLUMNS)
    candidate = (
        "\n".join(
            "".join(
                char
                for column, char in enumerate(line)
                if column not in dropped_columns
            ).rstrip()
            for row, line in enumerate(grid)
            if row not in dropped_rows
        ).rstrip()
        + "\n"
    )
    digest = hashlib.sha256(candidate.encode()).hexdigest()
    if digest != CANDIDATE_SHA256:
        raise AssertionError(f"LLLM squeeze SHA-256 drifted: {digest}")
    return candidate


def build_lllm_squeeze(parent: str | None = None) -> str:
    if parent is None:
        repo = Path(__file__).resolve().parents[2]
        parent = (repo / "submissions/lllm/lllm_03.man").read_text()
    return apply_lllm_squeeze(parent)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        raise SystemExit("usage: python -m littleman.lllm_squeeze OUTPUT")
    Path(args[0]).write_text(build_lllm_squeeze())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
