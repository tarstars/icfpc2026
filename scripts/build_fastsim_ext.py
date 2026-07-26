#!/usr/bin/env python
"""Build the optional C accelerator for the littleman executor.

    uv run python scripts/build_fastsim_ext.py

Produces `src/littleman/_fastsim_ext*.so`.  Everything keeps working
without it -- `littleman.fastsim` falls back to its pure-Python loop, and
that in turn falls back to `littleman.sim` for anything it cannot compile.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import sysconfig

REPO = pathlib.Path(__file__).resolve().parent.parent
SRC = REPO / "src" / "littleman" / "_ext" / "fastsim_ext.c"
OUT = REPO / "src" / "littleman" / "_fastsim_ext.so"


def main() -> int:
    include = sysconfig.get_paths()["include"]
    cmd = [
        "cc", "-O3", "-fPIC", "-shared", "-fno-strict-aliasing",
        f"-I{include}", str(SRC), "-o", str(OUT),
    ]
    print(" ".join(cmd))
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        print("build failed; the pure-Python fast path stays in use")
        return proc.returncode
    sys.path.insert(0, str(REPO / "src"))
    from littleman import fastsim  # noqa: E402

    print(f"built {OUT.name}; HAVE_EXTENSION={fastsim.HAVE_EXTENSION}")
    return 0 if fastsim.HAVE_EXTENSION else 1


if __name__ == "__main__":
    raise SystemExit(main())
