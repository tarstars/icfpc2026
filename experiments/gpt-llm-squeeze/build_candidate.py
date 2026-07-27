"""Build the GPT judge-safe row-squeeze successor to ``llm_codex_01``.

The 2,448 globally deletable rows are partitioned into 32 balanced contiguous
groups. Exact public judging retained groups 0..3, 5, and 8..31; groups 4, 6,
and 7 interact with runtime storage/timing and are not deleted.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "submissions/llm/llm_codex_01.man"
SELECTED_GROUPS = tuple(list(range(0, 4)) + [5] + list(range(8, 32)))
EXPECTED_BASE_SHA = "568d0b87937e9a41370d0b3434583d7109eb51ea9944b788e825e45c53e40ff6"
EXPECTED_SHA = "066c00b3f5aa34c0ec9d54c55d6f231bfd429522a9680d3f0cd9b45233d35ed9"


def balanced_groups(seq: list[int], count: int) -> list[list[int]]:
    q, r = divmod(len(seq), count)
    out = []
    pos = 0
    for index in range(count):
        size = q + (1 if index < r else 0)
        out.append(seq[pos : pos + size])
        pos += size
    assert pos == len(seq)
    return out


def build() -> str:
    base = BASE.read_text()
    assert hashlib.sha256(base.encode()).hexdigest() == EXPECTED_BASE_SHA
    raw = base.rstrip("\n").split("\n")
    width = max(map(len, raw))
    grid = [line.ljust(width) for line in raw]
    deletable = [row for row, line in enumerate(grid) if all(ch in " |" for ch in line)]
    assert len(deletable) == 2448
    groups = balanced_groups(deletable, 32)
    drop = {row for index in SELECTED_GROUPS for row in groups[index]}
    assert len(drop) == 2217
    candidate = "\n".join(
        line.rstrip() for row, line in enumerate(grid) if row not in drop
    ) + "\n"
    assert len(candidate.rstrip("\n").splitlines()) == 23580
    assert max(map(len, candidate.rstrip("\n").splitlines())) == 749
    assert hashlib.sha256(candidate.encode()).hexdigest() == EXPECTED_SHA
    return candidate


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: build_candidate.py OUTPUT.man")
    Path(sys.argv[1]).write_text(build())


if __name__ == "__main__":
    main()
