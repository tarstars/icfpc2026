#!/usr/bin/env python
"""Rebuild submissions/lllm/lllm_00.man from the current component sources.

STEP changes under us, so ALWAYS rebuild before judging; then:

    uv run python -m littleman submissions/lllm/lllm_00.man little-little-little-man
    uv run python scripts/preflight.py submissions/lllm/lllm_00.man little-little-little-man
    uv run python scripts/build_lllm.py --diagnose "first steps"
"""

from __future__ import annotations

import pathlib
import sys

from littleman import lllm_assemble as A

OUT = pathlib.Path("submissions/lllm/lllm_00.man")


def main(argv: list[str]) -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = A.build_machine()
    OUT.write_text(text)
    print(f"wrote {OUT}  ({len(text.encode())} bytes)")
    for line in A.audit_ports(text):
        print("  audit", line)
    from littleman.sim import Machine

    machine = Machine.parse(text)
    print(f"  rooms {len(machine.rooms)}  pipes {len(machine.pipes)}"
          f"  FETCH ring {A.ring_cells(machine, 'FETCH', 'FETCHRELAY')} cells")
    if "--sweep" in argv:
        for line in A.sweep(text):
            print(line)
    if "--diagnose" in argv:
        name = argv[argv.index("--diagnose") + 1]
        ticks = int(argv[-1]) if argv[-1].isdigit() else 400_000
        for line in A.diagnose_case(name, ticks):
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
