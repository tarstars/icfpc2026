"""Reproduce matmul_08.man from the checked-in matmul_07 parent.

Run from the ICFPC 2026 repository root:
    PYTHONPATH=src python /path/to/generate_matmul_08.py \
        submissions/matmul/matmul_07.man matmul_08.man
"""
from __future__ import annotations

import sys
from pathlib import Path

from littleman.alexey_piperoute import Router
from littleman.alexey_squeeze import squeeze
from littleman.matmul_components import _input_clearance_cells
from littleman.sim import Machine


def build(parent: str) -> str:
    squeezed, rows_dropped, cols_dropped = squeeze(
        parent, rows=False, cols=True
    )
    if (rows_dropped, cols_dropped) != (0, 16):
        raise ValueError(
            f"expected matmul_07 column squeeze (0, 16), got "
            f"{(rows_dropped, cols_dropped)}"
        )
    machine = Machine.parse(squeezed)
    controller = machine.rooms[0]
    old_a = next(
        pipe
        for pipe in machine.in_pipes[id(controller)]
        if len(pipe.cells) == 220
    )
    router = Router(
        squeezed,
        extra_blocked=_input_clearance_cells(machine),
    )
    router.erase(old_a.cells)
    path = router.route_safe(
        old_a.cells[0],
        old_a.cells[-1],
        into=(-1, 0),
        target=256,
        bounds=(router.h - 1, router.w - 1),
        out=(1, 0),
        attempts=500,
    )
    if len(path) != 256:
        raise ValueError(f"expected 256-cell A ring, got {len(path)}")
    return router.apply(path, into=(-1, 0))


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: generate_matmul_08.py PARENT.man OUTPUT.man")
    parent = Path(sys.argv[1]).read_text()
    Path(sys.argv[2]).write_text(build(parent))


if __name__ == "__main__":
    main()
