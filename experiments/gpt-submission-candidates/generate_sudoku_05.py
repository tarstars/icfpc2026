"""Reproduce sudoku_05_single_ring.man.

Keep this script beside sudoku_single_generator.py, then run from the ICFPC
2026 repository root:

    PYTHONPATH=src python /path/to/generate_sudoku_05.py OUTPUT.man
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from littleman.alexey_squeeze import squeeze
from littleman.alexey_stairfold import fold_room


def _load_generator():
    path = Path(__file__).with_name("sudoku_single_generator.py")
    spec = importlib.util.spec_from_file_location("sudoku_single_generator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build() -> str:
    module = _load_generator()
    base = module.build_sudoku_single()
    folded, freed = fold_room(base, 0)
    if freed != 82:
        raise ValueError(f"expected 82 folded rows, got {freed}")
    candidate, rows_dropped, cols_dropped = squeeze(
        folded, rows=True, cols=True
    )
    if (rows_dropped, cols_dropped) != (100, 54):
        raise ValueError(
            f"expected Sudoku squeeze (100, 54), got "
            f"{(rows_dropped, cols_dropped)}"
        )
    return candidate


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: generate_sudoku_05.py OUTPUT.man")
    Path(sys.argv[1]).write_text(build())


if __name__ == "__main__":
    main()
